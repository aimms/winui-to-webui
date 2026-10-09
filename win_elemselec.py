# Converts a WinUI element select object to a WebUI selectionbox widget - or, when the object is
# bound to a genuine scalar Parameter/ElementParameter rather than a Set, to a compact scalar
# widget instead (see _resolve_scalar_parameter_identifier) - or, when it's bound to a Set
# (WinUI's own way of showing set-membership selection, e.g. a subset picked from a ListBox), to
# a "multiselect" widget instead (see _resolve_set_selection_identifier).

from typing import List, Dict, Tuple, Any, Union, Optional # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
import modeledit_aimmspy2
import tools
from aimmspy.project.project import Project, Model

def _resolve_scalar_parameter_identifier(aimms_model: Model, component_dict: dict, winui_table_xml: ET.Element) -> Optional[str]:
    """
    The (namespace-qualified) bound identifier when a Selection Object is bound to a genuine
    0-dimensional AIMMS Parameter (e.g. a boolean toggle like FlowAccuracyIsRelative, shown via
    CheckBoxes) or ElementParameter (e.g. ep_b, shown via a DropDownList/ListBox picking one
    element rather than a subset) rather than a Set (e.g. a subset like MeasuredFlows picked from
    a ListBox), else None. The former two belong on a WebUI "scalar" widget - selectionbox-v2 is
    for actual set-membership selection, and misrepresents a plain scalar toggle/element pick.

    :param aimms_model: AIMMS model handle used to inspect the identifier's dimension and type.
    :type aimms_model: Model
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param winui_table_xml: XML element representing the WinUI selection object definition.
    :type winui_table_xml: ET.Element
    :return: The bound identifier's name if it's a scalar Parameter/ElementParameter, else None.
    :rtype: Optional[str]
    """
    explicit_identifier = winui_table_xml.find('ExplicitIdentifier')
    if explicit_identifier is None:
        return None
    identifier_el = explicit_identifier.find('Identifier')
    if identifier_el is None or not isinstance(identifier_el.text, str):
        return None
    identifier_text = win_object_tools.namespace_qualification(aimms_model, identifier_el.text, component_dict['Prefix'])
    identifier_name, _ = tools.parse_aimms_string(identifier_text)
    if modeledit_aimmspy2.getDim(aimms_model, identifier_name) != 0:
        return None
    if modeledit_aimmspy2.getType(aimms_model, identifier_name) not in ('parameter', 'element parameter'):
        return None
    return identifier_name


def _resolve_set_selection_identifier(aimms_model: Model, component_dict: dict, winui_table_xml: ET.Element) -> Optional[str]:
    """
    True (returning the bound Set's own name) when a Selection Object is bound to a plain
    (non-indexed) Set - either its own membership against a named domain set
    ("SubsetName( DomainSet )", e.g. a subset like MeasuredFlows picked from a ListBox) or, with
    no argument at all, against itself. WebUI has no widget that can bind to a raw Set, only to
    an ordinary Parameter - see win_object_tools._substitute_set_indicator_reference, which
    investigate_contents() calls to rewrite the actual content reference into one for an
    auto-generated binary indicator Parameter; this function only decides that the resulting
    widget should be a "multiselect" rather than "selectionbox-v2".

    modeledit_aimmspy2.getDim() reports 1 even for a plain, unindexed Set (not 0 as might be
    expected), so it can't distinguish "SetName" from an indexed set family's own single-index
    reference ("SetFamily(i)", selecting one member set by its family index i - out of scope,
    since i is an Index, not a Set) - checking the argument's own type instead sidesteps that
    ambiguity (mirrors win_object_tools._substitute_set_indicator_reference's own check). An
    indexed set family reference with more than one argument is also out of scope, same as
    _resolve_scalar_parameter_identifier's equally narrow scope for the scalar case. Either case
    returns None.

    :param aimms_model: AIMMS model handle used to inspect the identifier's type.
    :type aimms_model: Model
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param winui_table_xml: XML element representing the WinUI selection object definition.
    :type winui_table_xml: ET.Element
    :return: The bound Set's own name if it's a plain Set, else None.
    :rtype: Optional[str]
    """
    explicit_identifier = winui_table_xml.find('ExplicitIdentifier')
    if explicit_identifier is None:
        return None
    identifier_el = explicit_identifier.find('Identifier')
    if identifier_el is None or not isinstance(identifier_el.text, str):
        return None
    identifier_text = win_object_tools.namespace_qualification(aimms_model, identifier_el.text, component_dict['Prefix'])
    identifier_name, identifier_args = tools.parse_aimms_string(identifier_text)
    if len(identifier_args) > 1:
        return None
    if modeledit_aimmspy2.getType(aimms_model, identifier_name) != 'set':
        return None
    domain_set = identifier_args[0] if identifier_args else identifier_name
    if modeledit_aimmspy2.getType(aimms_model, domain_set) != 'set':
        return None
    return identifier_name


def winpage_selectionbox(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_table_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI element selection object into a WebUI selection box widget (or, for a scalar
    Parameter/ElementParameter selection, a compact scalar widget - see
    _resolve_scalar_parameter_identifier; or, for a Set selection, a "multiselect" widget - see
    _resolve_set_selection_identifier) and attach it to the target page. A scalar Parameter
    selection (not ElementParameter - see the call site below) also gets its identifier's Range
    backfilled to "binary" if it doesn't have one yet (see win_object_tools.ensure_binary_range) -
    a checkbox implies a 0/1 value regardless of whether the parameter happens to also drive some
    other widget's visibility.

    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used to inspect identifier contents.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary to which the widget will be added.
    :type webui_page_dict: dict
    :param page_name: Name of the page being processed.
    :type page_name: str
    :param winui_table_xml: XML element representing the WinUI selection object definition.
    :type winui_table_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data when content can be translated.
    :rtype: None
    """
    stable_id = win_object_tools.compute_stable_id(winui_table_xml, ancestor_info)
    scalar_identifier = _resolve_scalar_parameter_identifier(aimms_model, component_dict, winui_table_xml)
    set_identifier = None if scalar_identifier is not None else _resolve_set_selection_identifier(aimms_model, component_dict, winui_table_xml)
    if scalar_identifier is not None:
        objecttype = "scalar"
    elif set_identifier is not None:
        objecttype = "multiselect"
    else:
        objecttype = "selectionbox-v2"
    content_lists_expected = {
        "objecttype" : objecttype,
        "rowHeader"  : 0,
        "colHeader"  : 0,
        "header"     : 0,
        "aggregated" : 0,
        "stacked"    : 0,
        "overlays"   : 0,
        "grouped"    : 0 }
    if scalar_identifier is not None:
        # A checkbox implies a 0/1 value - backfill Range: binary if it's not already set. Only
        # meaningful for a genuine boolean Parameter; an ElementParameter's Range is its (already
        # mandatory) domain Set, never binary.
        if modeledit_aimmspy2.getType(aimms_model, scalar_identifier) == 'parameter':
            win_object_tools.ensure_binary_range(aimms_model, gii_dict, component_dict, scalar_identifier)
        # _resolve_scalar_parameter_identifier only looks at the first <ExplicitIdentifier> -
        # a CheckBoxes Selection Object can carry several siblings (one independent boolean
        # Parameter per row, e.g. OPTION_DispatchTransactions, OPTION_EnergyConstraints, ...),
        # each still becoming a "scalar" widget's content row via investigate_contents below.
        # Compact display only suits the genuine single-toggle case (e.g. FlowAccuracyIsRelative)
        # - a multi-row checkbox list must keep its normal (non-compact) display.
        if len(winui_table_xml.findall('ExplicitIdentifier')) == 1:
            content_lists_expected["compact"] = 1
    info_dict = win_object_tools.investigate_contents(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_table_xml, content_lists_expected, stable_id)
    if info_dict != {}:
        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_table_xml, ancestor_info)
        webui.add_data_widget(aimms_model, gii_dict, webui_page_dict, info_dict, content_lists_expected, ancestor_info, stable_id, area, title, visible_expr)
