# Converts a WinUI 2D Chart object to a WebUI combination chart widget (see win_linechart.py/
# win_barchart.py for the flat-<ExplicitIdentifier> Curve/Bar Chart counterparts this mirrors).

from typing import List, Dict, Tuple, Any, Union, Optional # Add Tuple and any other types you use
import lxml.etree as ET

import web_page
import win_object_tools
from aimmspy.project.project import Project, Model

def _resolve_chart_type_text(chart_type_el: Optional[ET.Element]) -> Optional[str]:
    """The stripped, unquoted text of a <Chart_type> element (e.g. "Area" from '"Area"'), or
    None when the element is absent/empty - WinUI omits it entirely for the default chart type
    (a plain line)."""
    if chart_type_el is None or not isinstance(chart_type_el.text, str):
        return None
    text = chart_type_el.text.strip()
    if len(text) > 1 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    return text or None


def _map_chart_type(chart_type_text: Optional[str]) -> str:
    """WinUI's own <Chart_type> text to WebUI's Combination Chart "chart.type" - only "Area" maps
    to "area"; anything else (absent, "Line", or an unrecognized value) is a plain line."""
    return "area" if chart_type_text == "Area" else "line"

def winpage_2dchart(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_table_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI 2D Chart object into a WebUI Combination Chart widget and attach it to the
    target page.

    A 2D Chart's own content is nested under a single <Y_Axis> (confirmed against a real
    production project - never more than one per 2D Chart):
      - <Y_Axis><Chart_type> is a quoted WinUI string (e.g. "Area") - the widget's own default
        chart type, absent entirely when the WinUI default (a plain line chart) applies, the same
        "presence means non-default" convention as win_linechart.py's own <FillArea>. Each
        <Identifier> can override it with its own nested <Chart_type> (confirmed with the user -
        a Combination Chart itself supports an "area" series type per content item, not just one
        shared type for the whole widget) - see chart_series_type_by_item below.
      - Each <Y_Axis><Identifier><Value> is one series' own content reference - a bare identifier
        or a computed expression (e.g. "STRING(...):=..."), either way handled identically to any
        other content reference by synthesizing it into the standard <ExplicitIdentifier>
        <Identifier> shape win_object_tools.investigate_contents already expects everywhere else
        (the same trick win_floatingindex.py uses for its own differently-shaped content) -
        investigate_contents' existing per-argument substitution handles the expression case with
        no extra code needed here.
      - <Identifier><Value_label> (a computed per-series display label) and <Identifier>
        <Appearance> (a per-series color) are deliberately not converted (out of scope for now).
        <X_Axis><Domain> needs no separate handling either - it's redundant with the domain
        argument each <Value> already carries directly.

    content_lists_expected["chart_series_type_by_item"] carries each series' own resolved chart
    type, keyed by its POSITION in the synthesized <ExplicitIdentifier> list (0-based) rather
    than its eventual content name - an expression-based <Value> (e.g. "STRING(...):=...") only
    gets its real, generated parameter name once investigate_contents has already substituted it,
    so a name-keyed dict couldn't be built ahead of that call. web_page.add_data_widget's own
    per-item loop walks contents_list in this exact same order, so the position lines up; see its
    own "chart.type" handling.

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
    :param winui_table_xml: XML element representing the WinUI 2D Chart definition.
    :type winui_table_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data when content can be translated.
    :rtype: None
    """
    y_axis = winui_table_xml.find('Y_Axis')
    if y_axis is None:
        return

    axis_chart_type_text = _resolve_chart_type_text(y_axis.find('Chart_type'))

    chart_series_type_by_item: Dict[int, str] = {}
    item_no = 0
    for series_identifier in y_axis.findall('Identifier'):
        value_el = series_identifier.find('Value')
        if value_el is None or not isinstance(value_el.text, str):
            continue
        explicit_identifier = ET.SubElement(winui_table_xml, 'ExplicitIdentifier')
        ET.SubElement(explicit_identifier, 'Identifier').text = value_el.text
        own_chart_type_text = _resolve_chart_type_text(series_identifier.find('Chart_type'))
        chart_series_type_by_item[item_no] = _map_chart_type(
            own_chart_type_text if own_chart_type_text is not None else axis_chart_type_text)
        item_no += 1

    stable_id = win_object_tools.compute_stable_id(winui_table_xml, ancestor_info)
    content_lists_expected = {
        "objecttype" : "combinationchart",
        "rowHeader"  : 0,
        "colHeader"  : 0,
        "header"     : 1,
        "aggregated" : 1,
        "stacked"    : 1,
        "overlays"   : 0,
        "grouped"    : 1,
        "chart_series_type": _map_chart_type(axis_chart_type_text),
        "chart_series_type_by_item": chart_series_type_by_item }
    info_dict = win_object_tools.investigate_contents(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_table_xml, content_lists_expected, stable_id)
    if info_dict != {}:
        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_table_xml, ancestor_info)
        webui.add_data_widget(aimms_model, gii_dict, webui_page_dict, info_dict, content_lists_expected, ancestor_info, stable_id, area, title, visible_expr)
