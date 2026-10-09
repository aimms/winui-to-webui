# Converts a WinUI Network Object to a WebUI Map widget (geographic coordinates) or Diagram
# widget (plain x/y coordinates).

from typing import Dict, List, Optional, Tuple
import re
import lxml.etree as ET

import converter_logging
import modeledit_aimmspy2
import tools
import web_page
import win_expression
import win_object_tools
from aimmspy.project.project import Model

LONGITUDE_TOKENS = {"lon", "lng", "long", "longitude"}
LATITUDE_TOKENS = {"lat", "latitude"}
# Used when the WinUI object has no <Location> to size the diagram's drawing space with -
# ranges found by hand to be reachable in a small diagram widget (examples/w2w0035/temp).
FALLBACK_DRAWING_WIDTH = 800.0
FALLBACK_DRAWING_HEIGHT = 360.0


def _strip_reverse_links(ref: str) -> str:
    """Drop WinUI's "index -> ElementParameter" focus links - UI-only, not part of the value."""
    return re.sub(r'\s*->\s*[A-Za-z_][\w:]*', '', ref)


def _name_tokens(ref: str) -> set:
    """Lower-case words of a reference's identifier name, split on '_' and camelCase, without
    any namespace prefix - so "nn::Longitude_center( reg )" gives {"longitude", "center"}."""
    name = tools.parse_aimms_string(ref)[0].split('::')[-1]
    words = re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).split('_')
    return {w.lower() for w in words if w}


def _has_gis_background(network_xml: ET.Element) -> bool:
    return any(isinstance(e.text, str) and 'GIS' in e.text for e in network_xml.iter('Background_Image_Source'))


def choose_widget(network_xml: ET.Element, mode: str) -> Tuple[str, str]:
    """
    Decide between "map" and "diagram" for one Network Object.

    :param mode: "map", "diagram" or "auto" (the --network command line option).
    :return: (widget kind, human-readable reason for the conversion log).
    """
    if mode in ("map", "diagram"):
        return mode, f"--network={mode}"
    if _has_gis_background(network_xml):
        return "map", "the WinUI object draws a GIS background"
    for node in network_xml.findall('Node'):
        x_ref, y_ref = node.findtext('XCoordinate') or '', node.findtext('YCoordinate') or ''
        if _name_tokens(x_ref) & LONGITUDE_TOKENS and _name_tokens(y_ref) & LATITUDE_TOKENS:
            return "map", f"node coordinates {x_ref.strip()} / {y_ref.strip()} are named as longitude/latitude"
    return "diagram", "no GIS background and no longitude/latitude coordinate names"


def _visible_area(aimms_model: Model, network_xml: ET.Element, prefix: str) -> Dict[str, object]:
    """Left/Right/Top/Bottom of the WinUI <VisibleArea>: a float, or - when WinUI computes it at
    run time (e.g. NetworkBound( 'Left' ), ContractVisibleAreaLeft) - the AIMMS expression as a
    string. WinUI omits a side that is 0."""
    area = network_xml.find('VisibleArea')
    sides: Dict[str, object] = {}
    for tag in ('Left', 'Right', 'Top', 'Bottom'):
        text = (area.findtext(tag) if area is not None else None) or '0'
        try:
            sides[tag] = float(text)
        except ValueError:
            sides[tag] = win_object_tools.namespace_qualification(aimms_model, text.strip(), prefix)
    return sides


def _num(value: float) -> str:
    return format(value, '.10g')


def _axis_transform(low, high, size: float) -> Tuple[str, str]:
    """(center, scale) as AIMMS expression text mapping [low, high] onto a drawing range of
    `size` centered on 0 - plain numbers when both sides are numeric, otherwise an expression
    over WinUI's own run-time bounds."""
    if isinstance(low, float) and isinstance(high, float):
        return _num((low + high) / 2), _num(size / (high - low) if high != low else 1.0)
    lo, hi = (_num(v) if isinstance(v, float) else v for v in (low, high))
    return f"( ( {lo} ) + ( {hi} ) ) / 2", f"{_num(size)} / ( ( {hi} ) - ( {lo} ) )"


def _node_index(aimms_model: Model, node_identifier: str) -> str:
    """The index a <Node> runs over: its <Identifier> is normally an index, but may be a set."""
    if modeledit_aimmspy2.getType(aimms_model, node_identifier) == 'index':
        return node_identifier
    index_attr = modeledit_aimmspy2.getAttribute(aimms_model, node_identifier, "index")
    if index_attr not in ("", "<Error>"):
        index_name = index_attr.split(',')[0].strip()
        prefix = node_identifier.rsplit('::', 1)[0] + '::' if '::' in node_identifier else ''
        return prefix + index_name if '::' not in index_name else index_name
    return node_identifier


def _identifier_slice(aimms_model: Model, ref: str) -> dict:
    """{"identifier": name, "slice": [...]} for a reference like "FlowsAnnual( ModelYear, h, h1 )"
    - same free / subset / element-parameter classification as win_object_tools.investigate_contents."""
    name, args = tools.parse_aimms_string(_strip_reverse_links(ref))
    prefix = name.rsplit('::', 1)[0] + '::' if '::' in name else ''
    slices = []
    for pos, arg in enumerate(args):
        domain_index = modeledit_aimmspy2.getDomainIndex(aimms_model, name, pos + 1)
        if prefix and '::' not in domain_index:
            domain_index = prefix + domain_index
        if modeledit_aimmspy2.isScalarElementParameter(aimms_model, arg):
            arg_type = "element-parameter"
        elif arg == domain_index:
            arg_type = "free"
        else:
            arg_type = "subset"
        slices.append({"index": domain_index, "type": arg_type, "value": arg})
    return {"identifier": name, "slice": slices}


def _coordinate_reference(aimms_model, gii_dict, component_dict, webui_page_dict, purpose: str, ref: str,
                          node_index: str, stable_id: str, item_index: int, transform: Optional[Tuple[str, str]] = None) -> dict:
    """A node coordinate as {"identifier", "slice"}. Used directly when it is a plain
    "parameter( node_index )"; otherwise - an element slice like NodeCoordinate( n, 'x' ), or a
    diagram coordinate that needs rescaling ((value - center) * scale) - via a generated
    parameter indexed over the node index."""
    ref = _strip_reverse_links(ref)
    name, args = tools.parse_aimms_string(ref)
    if transform is None and args == [node_index]:
        return _identifier_slice(aimms_model, ref)
    expr = ref if transform is None else f"( {ref} - {transform[0]} ) * {transform[1]}"
    generated = win_expression.make_webui_reference(aimms_model, gii_dict, component_dict, webui_page_dict, purpose,
                                                    expr, node_index, "numeric", "", stable_id, item_index)
    return {"identifier": generated, "slice": [{"index": node_index, "type": "free", "value": node_index}]}


def winpage_network(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict: dict, webui_page_dict: dict,
                    page_name: str, network_xml: ET.Element, ancestor_info: dict) -> None:
    """
    Convert a WinUI Network Object into a WebUI Map widget (map-v2) or Diagram widget - see
    choose_widget for which - and attach it to the page. Nodes keep their own index and
    coordinates; arcs keep their identifier. A Diagram takes one arc set only (a current WebUI
    limitation): further arc sets are left out and reported in the conversion log. Diagram
    coordinates are rescaled from the WinUI <VisibleArea> to a drawing space the size of the WinUI
    object, with Y flipped (WinUI's Y points up, the diagram's down). Node/arc styling (sizes,
    shapes, colors) and GIS background layers are not converted.
    """
    prefix = component_dict['Prefix']
    kind, reason = choose_widget(network_xml, gii_dict.get("_network", "auto"))
    stable_id = win_object_tools.compute_stable_id(network_xml, ancestor_info)
    messages = [f"Network object converted to a WebUI {kind} widget ({reason})."]

    sides = _visible_area(aimms_model, network_xml, prefix)
    transform_x = transform_y = None
    if kind == "diagram":
        loc = network_xml.find('Location')
        width = float(loc.get('right')) - float(loc.get('left')) if loc is not None else FALLBACK_DRAWING_WIDTH
        height = float(loc.get('bottom')) - float(loc.get('top')) if loc is not None else FALLBACK_DRAWING_HEIGHT
        # WebUI draws a node as a labelled box, far larger than WinUI's dot: spread the drawing
        # (--diagram-spread) and start zoomed out by the same factor, so the network keeps its
        # on-screen size but gains room between the boxes.
        spread = gii_dict.get("_diagram_spread", 2.5)
        width, height = width * spread, height * spread
        transform_x = _axis_transform(sides['Left'], sides['Right'], width)
        # Y flips: WinUI's Top (the larger value) must land at the diagram's negative (upper) side.
        transform_y = _axis_transform(sides['Top'], sides['Bottom'], height)

    details: Dict[str, dict] = {}
    node_keys: List[str] = []
    for n, node in enumerate(network_xml.findall('Node')):
        node_identifier = win_object_tools.namespace_qualification(aimms_model, (node.findtext('Identifier') or '').strip(), prefix)
        if node_identifier == '':
            continue
        node_index = _node_index(aimms_model, node_identifier)
        x_ref = win_object_tools.namespace_qualification(aimms_model, node.findtext('XCoordinate') or '', prefix)
        y_ref = win_object_tools.namespace_qualification(aimms_model, node.findtext('YCoordinate') or '', prefix)
        key = f"nodes.{len(node_keys)}"
        node_keys.append(key)
        details[f"{key}.index"] = {"literal": {"identifier": node_index}}
        if kind == "map":
            lon = _coordinate_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "longitude", x_ref, node_index, stable_id, n)
            lat = _coordinate_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "latitude", y_ref, node_index, stable_id, n)
            details[key] = {"aimms": {"contents": [lon["identifier"], lat["identifier"]], "slices": [lon, lat]}}
            details[f"{key}.longitude"] = {"literal": lon}
            details[f"{key}.latitude"] = {"literal": lat}
        else:
            x = _coordinate_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "diagram_x", x_ref, node_index, stable_id, n, transform_x)
            y = _coordinate_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "diagram_y", y_ref, node_index, stable_id, n, transform_y)
            details[f"{key}.coordinate.x"] = {"literal": x}
            details[f"{key}.coordinate.y"] = {"literal": y}
    if not node_keys:
        return
    details["nodes.__display_order__"] = {"literal": node_keys}

    arcs = [a for a in network_xml.findall('Arc') if (a.findtext('Identifier') or '').strip()]
    if kind == "diagram" and len(arcs) > 1:
        dropped = ", ".join(a.findtext('Identifier').strip() for a in arcs[1:])
        messages.append(f"A WebUI diagram supports one arc set only - not converted: {dropped}.")
        arcs = arcs[:1]
    arc_keys: List[str] = []
    for arc in arcs:
        arc_ref = win_object_tools.namespace_qualification(aimms_model, arc.findtext('Identifier').strip(), prefix)
        arc_slice = _identifier_slice(aimms_model, arc_ref)
        key = f"arcs.{len(arc_keys)}"
        arc_keys.append(key)
        if kind == "map":
            details[key] = {"aimms": {"contents": [arc_slice["identifier"]], "slices": [arc_slice]}}
            details[f"{key}.value"] = {"literal": arc_slice}
            details[f"{key}.line.straight"] = {"literal": (arc.findtext('Shape') or 'Straight') == 'Straight'}
            if arc.find('TextShowWhat') is None:
                details[f"{key}.label.hide"] = {"literal": True}
        else:
            details[f"{key}.identifier"] = {"literal": arc_slice}
    if arc_keys:
        details["arcs.__display_order__"] = {"literal": arc_keys}

    if kind == "map":
        if all(isinstance(v, float) for v in sides.values()):
            left, right, top, bottom = sides['Left'], sides['Right'], sides['Top'], sides['Bottom']
            details["mapbounds.nw.latitude"] = {"literal": top}
            details["mapbounds.nw.longitude"] = {"literal": left}
            details["mapbounds.se.latitude"] = {"literal": bottom}
            details["mapbounds.se.longitude"] = {"literal": right}
            details["center.latitude"] = {"literal": (top + bottom) / 2}
            details["center.longitude"] = {"literal": (left + right) / 2}
        else:
            messages.append("The WinUI visible area is computed at run time; set the map's bounds by hand.")
        if _has_gis_background(network_xml):
            layers = [e.text.strip().strip('"') for e in network_xml.iter('Shape_File') if isinstance(e.text, str)]
            messages.append(f"GIS background layers are not converted: {', '.join(layers) or 'unnamed'}.")
    else:
        details["center.x"] = {"literal": 0}
        details["center.y"] = {"literal": 0}
        details["zoom"] = {"literal": 1 / gii_dict.get("_diagram_spread", 2.5)}

    converter_logging.exoticW(messages, component_dict, "network object", page_name)
    area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, network_xml, ancestor_info)
    webui.add_network_widget(webui_page_dict, kind, details, stable_id, area, title, visible_expr)
