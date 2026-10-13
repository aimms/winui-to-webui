"""Pure-Python, AIMMS-session-free editor for .ams model files.

Applies a queue of edit commands (add identifier, set attribute, set
annotation) directly to .ams file text. This is meant for use after an
AIMMS session has been closed: some model edits are not safe or even
possible to make while a session is live (e.g. ModelEditAimmsPython.ams's
pr_setAnnotation, which can never actually run because its guard variable
is never assigned).

Known limitations (matches the formatting this tool's own generated .ams
files, and every real .ams file inspected, already use): a declaration's
opening "{" must be the last brace on its line, and its closing "}" must be
alone on its own line - single-line block declarations aren't recognized.
Double-quoted strings are assumed not to span multiple lines.
"""

import re
import sys
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple


# Maps the lowercase AllIdentifierTypes strings used by modeledit_aimmspy2.create()
# calls throughout this codebase to their .ams textual keyword. The first 7 are
# confirmed against real generated .ams fixtures (examples/w2w0027, w2w0028); the
# rest follow the same AIMMS naming convention but are unconfirmed against a fixture.
AMS_TYPE_KEYWORDS: Dict[str, str] = {
    "section": "Section",                      # confirmed
    "declaration": "DeclarationSection",        # confirmed
    "set": "Set",                               # confirmed
    "procedure": "Procedure",                   # confirmed
    "string parameter": "StringParameter",      # confirmed
    "element parameter": "ElementParameter",    # confirmed
    "parameter": "Parameter",                   # confirmed
    "index": "Index",
    "variable": "Variable",
    "element variable": "ElementVariable",
    "string variable": "StringVariable",
    "function": "Function",
    "module": "Module",
}

# Declaration keywords the scanner recognizes when locating EXISTING identifiers
# across arbitrary .ams files - broader than AMS_TYPE_KEYWORDS, which only covers
# types this tool creates.
DECLARATION_KEYWORDS: List[str] = sorted(
    set(AMS_TYPE_KEYWORDS.values()) | {"LibraryModule", "Model", "Constraint", "MathProgram", "Quantity", "Unit"},
    key=len, reverse=True,
)

_DECL_RE = re.compile(
    r'^[ \t]*(' + '|'.join(DECLARATION_KEYWORDS) + r')\s+([A-Za-z_]\w*)\s*([{;])'
)


# An AIMMS identifier simple name: a letter or underscore followed by letters, underscores,
# and digits. An AIMMS identifier name is one or more simple names separated by '::', optionally
# prefixed by '::'.
_IDENTIFIER_NAME_RE = re.compile(r'^(::)?[A-Za-z_]\w*(::[A-Za-z_]\w*)*$')


def _check_identifier_name(name, what: str) -> None:
    """Warns (stderr, with a full traceback for context) but does not raise, when `name` isn't
    a valid AIMMS identifier name - a command built from a malformed name would otherwise fail
    obscurely, much later, once AmsProject tries to resolve it."""
    if isinstance(name, str) and _IDENTIFIER_NAME_RE.match(name):
        return
    try:
        raise ValueError(f'ams_file_editor: {what} {name!r} is not a valid AIMMS identifier name')
    except ValueError:
        traceback.print_exc(file=sys.stderr)


@dataclass
class AmsEditCommand:
    """Base class for all pending .ams edits; future ops (delete/rename/move) subclass this."""


@dataclass
class AddIdentifier(AmsEditCommand):
    name: str
    type: str
    parent: str
    # Disambiguates `parent` (and this new identifier's own registration) when the same bare
    # name is deliberately reused across multiple components/files - e.g. every component gets
    # its own "GeneratedInterfaceIdentifiers" module, so "parent" alone isn't unique project-wide.
    # Pass the target component's own .ams path (e.g. component_dict["AmsPath"]) whenever `parent`
    # might not be a genuinely globally-unique name.
    file_hint: Optional[str] = None

    def __post_init__(self) -> None:
        _check_identifier_name(self.name, "identifier name")
        _check_identifier_name(self.parent, "parent identifier")


@dataclass
class SetAttribute(AmsEditCommand):
    identifier: str
    attribute: str
    value: str
    file_hint: Optional[str] = None

    def __post_init__(self) -> None:
        _check_identifier_name(self.identifier, "identifier")
        _check_identifier_name(self.attribute, "attribute name")


@dataclass
class SetAnnotation(AmsEditCommand):
    identifier: str
    annotation: str
    value: str
    file_hint: Optional[str] = None

    def __post_init__(self) -> None:
        _check_identifier_name(self.identifier, "identifier")
        _check_identifier_name(self.annotation, "annotation name")


@dataclass
class AppendToBody(AmsEditCommand):
    """Appends a statement to an existing block-form attribute (e.g. Body: { ... }),
    preserving whatever statements are already there. Unlike SetAttribute, which
    always replaces a single-line value, this is for pre-existing multi-line
    statement blocks (an identifier declared before this run started) that must
    not be clobbered."""
    identifier: str
    attribute: str
    statement: str
    file_hint: Optional[str] = None

    def __post_init__(self) -> None:
        _check_identifier_name(self.identifier, "identifier")
        _check_identifier_name(self.attribute, "attribute name")


def _format_field_lines(field_name: str, value: str, indent: str) -> List[str]:
    """Formats a "Name: value;" field. A single-line value stays exactly that; a value that
    itself spans multiple lines (e.g. a tab-spec data literal) is instead wrapped in its own
    "{ }" block with no trailing ';' - matching AIMMS's own .ams serialization convention for
    multi-line attribute values (confirmed against real fixtures: a Comment/Definition/Body
    whose value is multi-line is always written as "Attr: { <value, reindented> }", never as
    "Attr: <value>;" spanning several lines)."""
    if '\n' not in value:
        return [f"{indent}{field_name}: {value};"]
    value_lines = value.rstrip('\n').split('\n')
    return [f"{indent}{field_name}: {{"] + [f"{indent}\t{line}" for line in value_lines] + [f"{indent}}}"]


def _sanitize_line(line: str) -> str:
    """Blank out double-quoted string contents and trailing '!' comments so
    brace/keyword scanning never trips over braces or keywords inside them."""
    out = []
    in_string = False
    n = len(line)
    i = 0
    while i < n:
        ch = line[i]
        if in_string:
            out.append('"' if ch == '"' else ' ')
            if ch == '"':
                in_string = False
        elif ch == '"':
            in_string = True
            out.append('"')
        elif ch == '!':
            out.append(' ' * (n - i))
            break
        else:
            out.append(ch)
        i += 1
    return ''.join(out)


_ROOT_DECL_RE = re.compile(r'^(Model|LibraryModule)\s+([A-Za-z_]\w*)\s*\{')


def find_root_identifier(path: Path) -> str:
    """Returns the name of a .ams file's own top-level (zero-indent) Model or
    LibraryModule declaration - used as the `parent` for a new top-level child
    (e.g. a per-component GeneratedInterfaceIdentifiers module) without needing
    a live AIMMS session to ask for it."""
    for raw_line in Path(path).read_text(encoding="utf-8").splitlines():
        m = _ROOT_DECL_RE.match(_sanitize_line(raw_line))
        if m:
            return m.group(2)
    raise RuntimeError(f'ams_file_editor: no top-level Model/LibraryModule declaration found in {path}')


class _FileState:
    def __init__(self, path: Path):
        self.path = path
        text = path.read_text(encoding="utf-8")
        self.newline = "\r\n" if "\r\n" in text else "\n"
        self.lines: List[str] = text.splitlines()
        # name -> [start_line, end_line] (0-based, inclusive); end == start for a bodiless "Type name;" declaration
        self.ranges: Dict[str, List[int]] = {}
        # name -> declaration keyword (e.g. "ElementParameter") - lets callers find every
        # existing identifier of a given type (see find_all_colors_element_parameters)
        # without re-deriving it from ranges/lines themselves.
        self.types: Dict[str, str] = {}
        self.dirty = False
        self._scan()

    def _scan(self) -> None:
        self.ranges.clear()
        self.types.clear()
        stack: List[Tuple[str, int, int, str]] = []  # (name, start_line, depth_before, keyword)
        depth = 0
        for idx, raw_line in enumerate(self.lines):
            sanitized = _sanitize_line(raw_line)
            m = _DECL_RE.match(sanitized)
            opens_here = sanitized.count('{') > sanitized.count('}')
            if m and m.group(3) == '{' and opens_here:
                stack.append((m.group(2), idx, depth, m.group(1)))
            elif m and m.group(3) == ';':
                self.ranges[m.group(2)] = [idx, idx]
                self.types[m.group(2)] = m.group(1)

            depth += sanitized.count('{') - sanitized.count('}')

            while stack and depth <= stack[-1][2]:
                name, start_line, _, keyword = stack.pop()
                self.ranges[name] = [start_line, idx]
                self.types[name] = keyword

    def get_single_line_field(self, start: int, end: int, field_name: str) -> Optional[str]:
        """Returns the trimmed value text of a single-line "field_name: value;" field found
        within lines (start, end] (the body of the declaration spanning [start, end]), or None
        if not present - used to inspect an existing attribute's value (e.g. Range) without
        changing it, unlike _set_field's write path."""
        field_re = re.compile(r'^[ \t]*' + re.escape(field_name) + r'\s*:\s*(.*);\s*$')
        for idx in range(start + 1, end):
            m = field_re.match(_sanitize_line(self.lines[idx]))
            if m:
                return m.group(1).strip()
        return None

    def find_block_end(self, open_line_idx: int) -> int:
        """Given a line containing an unmatched opening '{', returns the index of
        the line containing its matching closing '}' (brace-depth matching, not
        tied to the declaration scanner - used for arbitrary block-form attribute
        values like Body: { ... })."""
        depth = 0
        for idx in range(open_line_idx, len(self.lines)):
            sanitized = _sanitize_line(self.lines[idx])
            depth += sanitized.count('{') - sanitized.count('}')
            if depth <= 0:
                return idx
        raise RuntimeError(f'ams_file_editor: unbalanced braces in {self.path} starting at line {open_line_idx + 1}')

    def indent_of(self, line_idx: int) -> str:
        line = self.lines[line_idx]
        return line[:len(line) - len(line.lstrip(' \t'))]

    def insert_lines(self, pos: int, new_lines: List[str]) -> None:
        n = len(new_lines)
        self.lines[pos:pos] = new_lines
        for rng in self.ranges.values():
            if rng[0] >= pos:
                rng[0] += n
            if rng[1] >= pos:
                rng[1] += n
        self.dirty = True

    def replace_line(self, line_idx: int, new_text: str) -> None:
        self.lines[line_idx] = new_text
        self.dirty = True

    def replace_lines(self, start_idx: int, end_idx: int, new_lines: List[str]) -> None:
        """Replaces lines [start_idx, end_idx) with new_lines, which may be a different count."""
        delta = len(new_lines) - (end_idx - start_idx)
        self.lines[start_idx:end_idx] = new_lines
        if delta != 0:
            for rng in self.ranges.values():
                if rng[0] >= end_idx:
                    rng[0] += delta
                if rng[1] >= end_idx:
                    rng[1] += delta
        self.dirty = True

    def save(self) -> None:
        if not self.dirty:
            return
        text = self.newline.join(self.lines)
        if self.lines:
            text += self.newline
        self.path.write_text(text, encoding="utf-8")
        self.dirty = False


class AmsProject:
    """Loads every .ams file under a project root and applies a queued list of
    AmsEditCommand objects to them as plain text - for use once the AIMMS
    session that produced the model has been closed."""

    def __init__(self, project_root: Path, main_ams_path: Optional[Path] = None,
                 extra_roots: Optional[List[Path]] = None):
        self.project_root = Path(project_root)
        # The main model's own .ams file (component Prefix == "" in the .aimms project file) -
        # an unqualified reference (no "prefix::" in the original identifier text) that's still
        # ambiguous after file_hint filtering falls back to whichever candidate is this file,
        # since an identifier written without a "::" qualifier can only mean the main model (every
        # library requires its own prefix to be referenced at all) - see _resolve().
        self.main_ams_path = Path(main_ams_path).resolve() if main_ams_path else None
        self._files: Dict[Path, _FileState] = {}
        # A bare name can legitimately be declared in more than one file - e.g. every component
        # gets its own "GeneratedInterfaceIdentifiers" module - so this maps name -> every file
        # that declares it; _resolve() disambiguates using a file_hint when there's more than one.
        self._index: Dict[str, List[Path]] = {}
        # `project_root` alone only reaches a component whose own folder is NESTED inside it - a
        # library referenced via a ".." Library Path that steps OUTSIDE project_root entirely
        # (e.g. "<main model dir>/../../ngas", a sibling of a sibling, not a descendant at all -
        # a "family of models" project layout, several components sharing one common ancestor a
        # couple levels up, rather than every library living inside the main model's own tree) is
        # never found by project_root.rglob() alone. `extra_roots` - every known component's own
        # directory (winui_to_webui.py passes every component_dict["Path"] here) - is scanned the
        # same way in addition, so every component's .ams file(s) are found regardless of where
        # its own folder actually sits relative to project_root. Already-seen files (resolved to
        # an absolute path, so the same file reached twice under two different-looking relative
        # spellings is only loaded once) are skipped - most components ARE nested normally under
        # project_root, so their own entry in extra_roots is typically redundant with the
        # project_root scan, not wrong.
        seen: Set[Path] = set()
        for root in [self.project_root] + [Path(r) for r in (extra_roots or [])]:
            if not root.is_dir():
                continue
            for ams_path in sorted(root.rglob("*.ams")):
                resolved = ams_path.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                state = _FileState(ams_path)
                self._files[ams_path] = state
                for name in state.ranges:
                    self._index.setdefault(name, []).append(ams_path)

    def apply(self, commands: List[AmsEditCommand]) -> None:
        for command in commands:
            try:
                if isinstance(command, AddIdentifier):
                    self._add_identifier(command)
                elif isinstance(command, SetAttribute):
                    self._set_field(command.identifier, command.attribute, command.value, command.file_hint)
                elif isinstance(command, SetAnnotation):
                    self._set_field(command.identifier, command.annotation, command.value, command.file_hint)
                elif isinstance(command, AppendToBody):
                    self._append_to_body(command)
                else:
                    raise TypeError(f"Unsupported AmsEditCommand: {command!r}")
            except Exception as e:
                # One bad edit (e.g. an ambiguous or missing identifier) shouldn't take down
                # every other queued edit - report it and keep going.
                print(f"ams_file_editor: error applying {command!r}: {e}", file=sys.stderr)

    def save(self) -> None:
        for state in self._files.values():
            try:
                state.save()
            except Exception as e:
                print(f"ams_file_editor: error saving {state.path}: {e}", file=sys.stderr)

    def prune_empty_sections(self, name_prefix: str = "", within_module_names: Tuple[str, ...] = ()) -> None:
        """Removes every Section left with nothing declared inside it - no nested Section,
        Procedure, or other identifier - once every queued edit has been applied. Call after
        apply() and before save().

        Two independent scopes, both must pass, so this only ever removes a Section a caller's
        own generated-identifier scaffolding created (see gii_module.ensure_page_section) - never
        a user's own pre-existing Section elsewhere in the model, even one that happens to already
        be empty:
        - `name_prefix` (e.g. gii_module.PAGE_SECTION_NAME_PREFIX) - a plain name-prefix check;
          an empty `name_prefix` (the default) doesn't filter by name at all.
        - `within_module_names` - the Section must be nested (at any depth) inside a Module
          declared under one of these names (e.g. gii_module.MAIN_MODULE_NAME/LIBRARY_MODULE_NAME)
          - a STRUCTURAL check, independent of naming, so a name-prefix collision alone (a user's
          own Section that happens to start the same way, elsewhere in the model) still can't be
          touched. An empty tuple (the default) doesn't filter by structure at all.

        A page's own generated Section can end up empty when every widget on that page turned out
        not to need a single generated identifier after all, or when it was created purely to
        hold a now-pruned child page's own Section (see ensure_page_section's ancestor-chain
        nesting). Runs repeatedly per file until a full pass removes nothing, since removing an
        empty Section can leave its own now-childless parent Section empty too - this converges
        regardless of scan/iteration order, so it doesn't depend on any particular nesting-depth
        ordering of `_FileState.types`.

        Also catches a Section already written in AIMMS's own bodiless shorthand ("Section Foo;",
        no "{ }" at all) - a Section this tool always creates braced (see AddIdentifier's own
        keyword/name/"{"/"}" line pair), so a bodiless one seen here is AIMMS's own doing, from an
        earlier run: AIMMS collapses an empty "{ }" block to this form the next time it loads and
        re-saves the project. A bodiless declaration can't contain anything by construction (no
        body to put it in), so it's unconditionally treated as empty - the same "nothing declared
        inside" case as an empty braced block, just spelled differently.
        """
        for state in self._files.values():
            while True:
                removed_any = False
                for name in list(state.types.keys()):
                    if state.types.get(name) != "Section" or not name.startswith(name_prefix):
                        continue
                    start, end = state.ranges[name]
                    if within_module_names and not self._is_nested_in(state, start, end, within_module_names):
                        continue  # not nested inside any of the named modules - leave it alone.
                    if start != end and any(other_start > start and other_end < end
                                             for other_name, (other_start, other_end) in state.ranges.items()
                                             if other_name != name):
                        continue  # something (direct or nested) is still declared inside it.
                    state.replace_lines(start, end + 1, [])
                    del state.ranges[name]
                    del state.types[name]
                    paths = self._index.get(name)
                    if paths and state.path in paths:
                        paths.remove(state.path)
                        if not paths:
                            del self._index[name]
                    removed_any = True
                if not removed_any:
                    break

    @staticmethod
    def _is_nested_in(state: "_FileState", start: int, end: int, module_names: Tuple[str, ...]) -> bool:
        """True when the declaration spanning [start, end] sits (at any depth) inside a Module
        declared under one of `module_names`, in this same file."""
        for mname in module_names:
            mrange = state.ranges.get(mname)
            if mrange is None or state.types.get(mname) != "Module":
                continue
            mstart, mend = mrange
            if mstart < start and end < mend:
                return True
        return False

    def find_all_colors_element_parameters(self) -> List[Tuple[Path, str]]:
        """Returns (file path, bare name) for every ElementParameter declared anywhere in the
        project whose Range is (case-insensitively) "AllColors" - AIMMS's own built-in system set
        of color names, not directly usable by WebUI (see gii_module.ensure_all_colors_values).
        A bodiless "ElementParameter Foo;" declaration has no body to hold a Range at all, so it
        never matches."""
        results: List[Tuple[Path, str]] = []
        for path, state in sorted(self._files.items()):
            for name, (start, end) in state.ranges.items():
                if state.types.get(name) != "ElementParameter" or start == end:
                    continue
                range_value = state.get_single_line_field(start, end, "Range")
                if range_value is not None and range_value.strip().lower() == "allcolors":
                    results.append((path, name))
        return results

    def _resolve(self, name: str, file_hint: Optional[str] = None) -> Tuple[_FileState, str, List[int]]:
        """Returns (file state, resolved bare name, [start, end]). The resolved name is the
        actual key under which the declaration is indexed in state.ranges - never the possibly
        "prefix::"-qualified `name` argument - so callers that later mutate state.ranges (e.g.
        after promoting a bodiless declaration to a braced block) update the same entry they
        just read, instead of stashing a second, stale copy under the qualified key."""
        hint_path = Path(file_hint).resolve() if file_hint else None
        was_qualified = '::' in name
        candidates = self._index.get(name, [])
        if not candidates and was_qualified:
            # Callers often pass a fully-qualified "prefix::name" reference (as used
            # in expression text) even though declarations are indexed by their bare
            # name - retry with the part after the last '::'.
            name = name.rsplit('::', 1)[-1]
            candidates = self._index.get(name, [])
        if hint_path is not None:
            hinted = [p for p in candidates if p.resolve() == hint_path]
            if hinted:
                state = self._files[hinted[0]]
                return state, name, state.ranges[name]
        if len(candidates) == 1:
            state = self._files[candidates[0]]
            return state, name, state.ranges[name]
        if len(candidates) > 1:
            if not was_qualified and self.main_ams_path is not None:
                # The caller's identifier carried no "::" qualifier at all, so it can only have
                # meant the main model - every library needs its own prefix to be referenced -
                # and file_hint (often just a guess at the referencing page's own component, not
                # necessarily where the identifier is declared) failed to narrow it down above.
                main_matches = [p for p in candidates if p.resolve() == self.main_ams_path]
                if main_matches:
                    state = self._files[main_matches[0]]
                    return state, name, state.ranges[name]
            raise RuntimeError(f'ams_file_editor: identifier "{name}" is declared in {len(candidates)} files - pass file_hint to disambiguate')
        raise RuntimeError(f'ams_file_editor: identifier "{name}" not found in any .ams file under {self.project_root}')

    def _add_identifier(self, command: AddIdentifier) -> None:
        keyword = AMS_TYPE_KEYWORDS.get(command.type)
        if keyword is None:
            raise RuntimeError(f'ams_file_editor: unknown identifier type "{command.type}"')
        state, _, parent_range = self._resolve(command.parent, command.file_hint)
        if command.name in state.ranges:
            raise RuntimeError(f'ams_file_editor: identifier "{command.name}" already exists in {state.path}')
        parent_start, parent_end = parent_range
        if parent_start == parent_end:
            raise RuntimeError(f'ams_file_editor: parent "{command.parent}" has no body to insert into')
        indent = state.indent_of(parent_start) + "\t"
        insert_pos = parent_end
        state.insert_lines(insert_pos, [f"{indent}{keyword} {command.name} {{", f"{indent}}}"])
        state.ranges[command.name] = [insert_pos, insert_pos + 1]
        # _scan() (run once, at AmsProject.__init__, over each file's pre-existing on-disk text)
        # already populates state.types for every identifier that existed before this run - this
        # is the same bookkeeping for one freshly created in-memory, so anything keying off
        # state.types (e.g. prune_empty_sections' own "is this a Section" check) sees a fresh
        # identifier exactly the same way it would if the file were re-scanned from disk.
        state.types[command.name] = keyword
        self._index.setdefault(command.name, []).append(state.path)

    def _set_field(self, identifier: str, field_name: str, value: str, file_hint: Optional[str] = None) -> None:
        state, resolved_name, (start, end) = self._resolve(identifier, file_hint)
        if start == end:
            # A bodiless "Type name;" declaration (AIMMS allows omitting the {} block when an
            # identifier has no attributes, e.g. "Parameter FlowAccuracyIsRelative;") has nowhere
            # to put a field yet - promote it to an (initially empty) braced block first, the
            # same shape _add_identifier() leaves a freshly created identifier in, then fall
            # through to the normal field-insertion path below.
            sanitized = _sanitize_line(state.lines[start])
            m = _DECL_RE.match(sanitized)
            if not m or m.group(3) != ';':
                raise RuntimeError(f'ams_file_editor: identifier "{identifier}" has no body to set "{field_name}" on')
            indent = state.indent_of(start)
            state.replace_lines(start, start + 1, [f"{indent}{m.group(1)} {m.group(2)} {{", f"{indent}}}"])
            end = start + 1
            # Update under `resolved_name` (the bare name state.ranges is actually indexed by) -
            # not the possibly "prefix::"-qualified `identifier` argument, which would otherwise
            # stash a second, stale [start, start] entry that every later SetAttribute on this
            # same identifier keeps re-resolving to, "has no body" and all.
            state.ranges[resolved_name] = [start, end]
        field_re = re.compile(r'^([ \t]*)' + re.escape(field_name) + r'\s*:')
        for idx in range(start + 1, end):
            sanitized = _sanitize_line(state.lines[idx])
            m = field_re.match(sanitized)
            if m:
                field_indent = m.group(1)
                if sanitized.rstrip().endswith('{'):
                    # An existing multi-line "Field: {" block (see _format_field_lines) - its own
                    # closing "}" is written at this SAME indent (never deeper - every content
                    # line is indented one tab further), so the first line matching that exactly
                    # is unambiguously it, not a content line. Replace the whole block, not just
                    # its opening line, or the old content/closing "}" would be left behind as
                    # orphaned, stale lines.
                    close_idx = idx + 1
                    while close_idx < end and _sanitize_line(state.lines[close_idx]).rstrip() != field_indent + "}":
                        close_idx += 1
                    if close_idx >= end:
                        raise RuntimeError(f'ams_file_editor: identifier "{identifier}" has an unterminated "{field_name}" block')
                    state.replace_lines(idx, close_idx + 1, _format_field_lines(field_name, value, field_indent))
                else:
                    state.replace_lines(idx, idx + 1, _format_field_lines(field_name, value, field_indent))
                return
        indent = state.indent_of(start) + "\t"
        state.insert_lines(end, _format_field_lines(field_name, value, indent))

    def _append_to_body(self, command: AppendToBody) -> None:
        state, _, (start, end) = self._resolve(command.identifier, command.file_hint)
        if start == end:
            raise RuntimeError(f'ams_file_editor: identifier "{command.identifier}" has no body to append "{command.attribute}" to')
        # A statement may itself be multi-line (e.g. several ';'-terminated lines built up by a
        # caller) - split it so each line stays its own entry in the in-memory buffer, keeping
        # later line-index-based operations (insert/scan) accurate.
        statement_lines = command.statement.rstrip('\n').split('\n') or [""]
        block_re = re.compile(r'^([ \t]*)' + re.escape(command.attribute) + r'\s*:\s*\{')
        for idx in range(start + 1, end):
            m = block_re.match(_sanitize_line(state.lines[idx]))
            if m:
                block_end = state.find_block_end(idx)
                indent = m.group(1) + "\t"
                state.insert_lines(block_end, [f"{indent}{line}" for line in statement_lines])
                return
        indent = state.indent_of(start) + "\t"
        state.insert_lines(end, [f"{indent}{command.attribute}: {{"] + [f"{indent}\t{line}" for line in statement_lines] + [f"{indent}}}"])
