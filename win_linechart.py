# Converts a WinUI curve object to a WebUI combination chart widget (one "line" series per
# curve - see win_barchart.py for the "column" counterpart).

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
import win_layout
from aimmspy.project.project import Project, Model

def winpage_linechart(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_table_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI curve object into a WebUI Combination Chart widget (each curve becomes its
    own "line" series - content_lists_expected["chart_series_type"] tells
    web_page.add_data_widget which per-series chart.type to emit; see win_barchart.py for the
    identical structure with "column" instead) and attach it to the target page.

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
    :param winui_table_xml: XML element representing the WinUI curve definition.
    :type winui_table_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data when content can be translated.
    :rtype: None
    """
    stable_id = win_object_tools.compute_stable_id(winui_table_xml, ancestor_info)

    if win_layout.is_empty_data_object(winui_table_xml):
        # No ExplicitIdentifier with a real identifier/expression reference - treat as if this
        # object didn't exist, rather than emit a widget with empty contents.
        return

    # <FillArea>true</FillArea> is a widget-level WinUI flag (a sibling of <DrawLines>, not
    # per-ExplicitIdentifier) - shades the area under every curve in this widget, matching
    # WebUI's own "area" chart type (confirmed against a hand-built reference widget - see
    # examples/w2w0034/temp). Every series in the widget shares the same chart_series_type, same
    # as the plain-line case.
    fill_area_elem = winui_table_xml.find('FillArea')
    chart_series_type = "area" if (fill_area_elem is not None and fill_area_elem.text == 'true') else "line"
    # A curve whose identifier keeps two free/subset indices: the first goes to the X-axis
    # ("header"), the second to "grouped" - or the other way round with <SwappedAxes>true.
    swapped_axes_elem = winui_table_xml.find('SwappedAxes')
    content_lists_expected = {
        "chart_index_split": True,
        "chart_swapped_axes": swapped_axes_elem is not None and swapped_axes_elem.text == 'true',
        "objecttype" : "combinationchart",
        "rowHeader"  : 0,
        "colHeader"  : 0,
        "header"     : 1,
        "aggregated" : 1,
        "stacked"    : 1,
        "overlays"   : 0,
        "grouped"    : 1,
        "chart_series_type": chart_series_type }
    info_dict = win_object_tools.investigate_contents(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_table_xml, content_lists_expected, stable_id)
    if info_dict != {}:
        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_table_xml, ancestor_info)
        webui.add_data_widget(aimms_model, gii_dict, webui_page_dict, info_dict,  content_lists_expected, ancestor_info, stable_id, area, title, visible_expr)
