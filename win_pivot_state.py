# Reads a WinUI Pivot Table's row/column/outer index arrangement directly out of the AIMMS
# IDE's .DeveloperState / .UserState files, keyed by the object's own <ObjectUUID>.
#
# This arrangement is set interactively in the WinUI IDE and is never written to the WinUI
# XML, so it can only be recovered from these binary state files. The on-disk format is
# undocumented; this module implements it from the real AIMMS engine source
# (C:\u\s\work\aimms\engine\aimms\ui\PivotGrid\src\SavedPivotState.cpp/.h, Serializable.cpp/.h,
# InterpreterGroup.h; C:\u\s\work\aimms\engine\aimms\ui\gui\{include,src}\GuiBinaryIOBuffers.*,
# GuiDBStateFile.*) and was cross-checked against 8 independently hand-verified real pivot
# tables (all 8 matched). See documentation/pivot state.md for the format writeup.
#
# The file is a "gdbi" key-value store: every distinct object ever saved gets an auto-assigned
# RootFolder number (starting at 10), looked up by a UTF-8-encoded string key. Within a
# RootFolder, named Folders (SavedPivotState_Impl: RowTree=10, ColumnTree=20, Interpreters=30,
# SymbolInfo=40, GridOptions=50, SortCriterions=60) each hold a sequence of buffers. We only
# need the Interpreters folder: one zlib-compressed SerializableInterpreter record per
# identifier the IDE has ever touched for that table, each directly carrying an
# InterpreterGroupType enum - the row/column/outer assignment itself, no further inference
# needed.

from typing import Dict, List, Optional, Set, Tuple
import os
import pathlib
import struct
import zlib

import lxml.etree as ET
import converter_logging

INTERPRETERS_FOLDER = 30
NEW_HEADER_VERSION_ID = -310

GROUP_NONE = 0
GROUP_OUTER = 1
GROUP_ROW_COMMON = 2
GROUP_COLUMN_COMMON = 3
GROUP_REMAINING = 4

DOMAIN_INDEX_ID_FIRST = 1  # id.first for a real domain-index interpreter (2/3/5 = generic Symbols/Cases/Suffices axes)
SYMBOLS_ID_FIRST = 2  # id.first for the pseudo-axis listing a multi-identifier table's own explicit identifiers


def _read_int(buf: bytes, pos: int) -> Tuple[int, int]:
    return struct.unpack_from("<i", buf, pos)[0], pos + 4


def _read_short(buf: bytes, pos: int) -> Tuple[int, int]:
    return struct.unpack_from("<h", buf, pos)[0], pos + 2


def _read_bool(buf: bytes, pos: int) -> Tuple[bool, int]:
    return buf[pos] != 0, pos + 1


def _read_string(buf: bytes, pos: int) -> Tuple[str, int]:
    """Length-prefixed string per GuiBinaryIOBuffers.cpp: positive length = ASCII bytes,
    negative length = -length UTF-16LE chars, zero = empty string."""
    length, pos = _read_int(buf, pos)
    if length == 0:
        return "", pos
    if length > 0:
        return buf[pos:pos + length].decode("ascii", errors="replace"), pos + length
    n = -length
    return buf[pos:pos + n * 2].decode("utf-16-le", errors="replace"), pos + n * 2


def _developer_state_path(component_dict: dict) -> Optional[pathlib.Path]:
    filename = "Main.DeveloperState" if component_dict.get("Prefix", "") == "" else "Library.DeveloperState"
    path = pathlib.Path(os.path.join(component_dict["Path"], filename))
    return path if path.exists() else None


def _find_root_folder(data: bytes, uuid: str) -> Optional[int]:
    """Look up an ObjectUUID's RootFolder number, per DBStateFile::FetchRootFolderViaUTF8's
    key encoding: [int(-1)][int length][UTF-8 string], value = [int RootFolder number]."""
    name = uuid.upper().encode("utf-8")
    key = struct.pack("<ii", -1, len(name)) + name
    idx = data.find(key)
    if idx < 0:
        return None
    value_at = idx + len(key)
    if value_at + 4 > len(data):
        return None
    return struct.unpack_from("<i", data, value_at)[0]


def _read_folder_last_written(data: bytes, root: int, folder: int) -> int:
    """Read the [root,folder,0] header buffer and return lastWritten, per
    DBStateFolder::ReadFromHeader's two formats (old style: a single positive int; new style:
    NEW_HEADER_VERSION_ID, then lastWritten, then a bool isZipped). Unlike every other buffer,
    the header is written via DBStateRootFolder::WriteFolderBuffer directly - bypassing
    DBStateFolder::WriteNthBuffer's zip-wrapping - so it is always stored raw/unzipped."""
    key = struct.pack("<iii", root, folder, 0)
    idx = data.find(key)
    if idx < 0:
        return 0
    raw = data[idx + len(key):idx + len(key) + 16]
    if len(raw) < 4:
        return 0
    first, pos = _read_int(raw, 0)
    if first > 0:
        return first
    if first == NEW_HEADER_VERSION_ID:
        last_written, pos = _read_int(raw, pos)
        return last_written if last_written > 0 else 0
    return 0


def _read_zipped_buffer_at(data: bytes, raw_at: int) -> Optional[bytes]:
    """Decompress a ZippedBinaryOutputBuffer value starting at raw_at: [int originalSize],
    then raw zlib/deflate compressed bytes (GuiBinaryIOBuffers.cpp)."""
    if raw_at + 4 > len(data):
        return None
    comp_start = raw_at + 4
    d = zlib.decompressobj()
    try:
        out = d.decompress(data[comp_start:comp_start + 1_000_000])
        out += d.flush()
    except zlib.error:
        return None
    return out if out else None


def _read_zipped_buffer(data: bytes, root: int, folder: int, n: int) -> Optional[bytes]:
    key = struct.pack("<iii", root, folder, n)
    idx = data.find(key)
    if idx < 0:
        return None
    return _read_zipped_buffer_at(data, idx + len(key))


def _decode_interpreter_group(raw: bytes) -> Optional[Tuple[int, str, int]]:
    """Read just id.first, id.second, m_GroupType from a SerializableInterpreter::Write()
    record (Serializable.cpp:247) - no need to parse the rest, each record lives in its own
    independently-keyed buffer."""
    try:
        id_first, pos = _read_int(raw, 0)
        id_second, pos = _read_string(raw, pos)
        has_aggr, pos = _read_bool(raw, pos)
        if has_aggr:
            return None  # aggrInfo format not needed/decoded - not a plain domain index record
        group_type, pos = _read_int(raw, pos)
        return id_first, id_second, group_type
    except (struct.error, IndexError):
        return None


def _classify_table(data: bytes, uuid: str) -> Optional[Dict[str, object]]:
    root = _find_root_folder(data, uuid)
    if root is None:
        return None

    last_written = _read_folder_last_written(data, root, INTERPRETERS_FOLDER)
    if last_written <= 0:
        return None

    outer_names: List[str] = []
    row_names: List[str] = []
    col_names: List[str] = []
    remaining_names: List[str] = []
    folded: List[Tuple[str, str]] = []
    symbols_group_type: Optional[int] = None
    # How many distinct row/column COMMON indices were recorded before the last Symbols record -
    # the identifier list's own nesting position on its axis (no RowTree/ColumnTree data seen).
    symbols_row_pos = 0
    symbols_col_pos = 0

    for n in range(1, last_written + 1):
        raw = _read_zipped_buffer(data, root, INTERPRETERS_FOLDER, n)
        if raw is None:
            continue
        decoded = _decode_interpreter_group(raw)
        if decoded is None:
            continue
        id_first, name, group_type = decoded
        if id_first == SYMBOLS_ID_FIRST:
            # A multi-identifier table (composite/pivot) folds all its explicit identifiers onto
            # one shared "Symbols" pseudo-axis in the IDE. The same table can record it more than
            # once (e.g. OUTER, then later COLUMN after re-pivoting): the LAST record is the
            # current placement - confirmed against a real WinUI screenshot (50NGMM, LNG Exports).
            symbols_group_type = group_type
            symbols_row_pos = len(row_names)
            symbols_col_pos = len(col_names)
            continue
        if id_first != DOMAIN_INDEX_ID_FIRST:
            continue  # generic Cases/Suffices axis, not a real domain index

        if group_type == GROUP_OUTER:
            if name not in outer_names:
                outer_names.append(name)
                folded.append((name, "OUTER"))
        elif group_type == GROUP_ROW_COMMON:
            if name not in row_names:
                row_names.append(name)
        elif group_type == GROUP_COLUMN_COMMON:
            if name not in col_names:
                col_names.append(name)
        elif group_type == GROUP_REMAINING:
            # REMAINING doesn't record which tree (row or column) it belongs to in this
            # folder alone (would need the separate RowTree/ColumnTree folders, empty in
            # every real test case seen) - resolved below, once symbols_placement is known.
            if name not in remaining_names:
                remaining_names.append(name)

    if not (outer_names or row_names or col_names or remaining_names or symbols_group_type is not None):
        return None

    # symbols_pos: index within the returned "row"/"col" list in front of which the identifier
    # list nests. OUTER (a WinUI filter/selector, no WebUI equivalent) stays outermost on rows;
    # REMAINING goes after the row's own common indices.
    symbols_pos: Optional[int] = None
    if symbols_group_type == GROUP_OUTER:
        symbols_placement = "row"
        symbols_pos = 0
    elif symbols_group_type == GROUP_ROW_COMMON:
        symbols_placement = "row"
        symbols_pos = len(outer_names) + symbols_row_pos
    elif symbols_group_type == GROUP_REMAINING:
        symbols_placement = "row"
        symbols_pos = len(outer_names) + len(row_names)
    elif symbols_group_type == GROUP_COLUMN_COMMON:
        symbols_placement = "col"
        symbols_pos = symbols_col_pos
    else:
        symbols_placement = None

    # The AIMMS engine's own IndividualInterpreterGroup (InterpreterGroup.h) - what
    # GROUP_REMAINING actually maps to - is documented there as holding indices that
    # "appear below the identifier node", i.e. nested alongside wherever the table's own
    # multi-identifier "Symbols" pseudo-axis (SYMBOLS_ID_FIRST) sits, rather than always on
    # the row axis: a real customer pivot table (RSC, Area MW CC) had a REMAINING index
    # (IndexCurrentCaseSelection) placed in the WinUI IDE on the SAME axis as Symbols -
    # column - and converting it to row (the previous, single-verified-set default) put it
    # on the wrong axis entirely. Follow symbols_placement when the table has one; a
    # single-identifier table has no Symbols axis to follow, so keep the row default (the
    # only case the earlier hand-verified real tables actually covered).
    remaining_axis = symbols_placement or "row"
    folded.extend((name, "REMAINING") for name in remaining_names)

    return {
        "row": outer_names + row_names + (remaining_names if remaining_axis == "row" else []),
        "col": col_names + (remaining_names if remaining_axis == "col" else []),
        "folded": folded,
        # Row/column placement of the multi-identifier "Symbols" pseudo-axis itself (see
        # SYMBOLS_ID_FIRST above) - "row", "col", or None when this table never recorded one
        # (e.g. a single-identifier table, which has no such axis at all).
        "symbols": symbols_placement,
        "symbols_pos": symbols_pos,
    }


def collect_pivot_table_uuids(component_dict: dict) -> Set[str]:
    """Scan this component's PageManager.xml-reachable Pages and Templates for every Pivot
    Table's <ObjectUUID>, so scan_pivot_tables() only ever looks up UUIDs actually in use."""
    uuids: Set[str] = set()
    base = pathlib.Path(component_dict["Path"])
    for folder_name in ("Pages", "Templates"):
        folder = base / folder_name
        if not folder.is_dir():
            continue
        for xml_path in folder.glob("*.xml"):
            try:
                tree = ET.parse(str(xml_path))
            except ET.XMLSyntaxError:
                continue
            for pobj in tree.getroot().findall(".//PageObject[@Type='Pivot Table']"):
                uuid_text = pobj.findtext("ObjectUUID")
                if uuid_text:
                    uuids.add(uuid_text.strip().upper())
    return uuids


def scan_pivot_tables(component_dict: dict, uuids: Set[str]) -> Dict[str, Dict[str, object]]:
    """
    Read this component's .DeveloperState once and resolve the row/column/outer arrangement
    for each requested Pivot Table ObjectUUID.

    :param component_dict: Component metadata (must carry 'Path' and 'Prefix').
    :type component_dict: dict
    :param uuids: ObjectUUIDs (as found in the WinUI XML) to look up.
    :type uuids: Set[str]
    :return: {uuid: {"row": [domain index names, outer-then-row-then-remaining order],
        "col": [domain index names], "folded": [(name, "OUTER"|"REMAINING"), ...],
        "symbols": "row"|"col"|None}} - a UUID with nothing usefully cached is simply absent;
        callers must treat that as "unknown", not a hard failure.
    :rtype: Dict[str, Dict[str, object]]
    """
    if not uuids:
        return {}

    path = _developer_state_path(component_dict)
    if path is None:
        return {}

    data = path.read_bytes()

    result: Dict[str, Dict[str, object]] = {}
    for uuid in uuids:
        classified = _classify_table(data, uuid)
        if classified is not None:
            result[uuid] = classified

    return result


def log_folded_indices(component_dict: dict, page_name: str, table_label: str, folded: List[Tuple[str, str]]) -> None:
    """Record OUTER/REMAINING indices whose row/column axis was inferred rather than read
    directly off an explicit row/column classification, so real-project conversions can be
    manually spot-checked (see _classify_table's own row/col placement for where each one
    actually landed)."""
    if not folded:
        return
    lines = [f"Pivot table '{table_label}' on page {page_name}: the following indices' row/column axis was inferred:"]
    for name, reason in folded:
        lines.append(f"  - {name} (WinUI classification: {reason})")
    converter_logging.lines(lines)
