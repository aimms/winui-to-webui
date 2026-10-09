# Converts a WinUI pivot table object to a WebUI table widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
from aimmspy.project.project import Project, Model

def winpage_pivot_table(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict,  webui_page_dict: dict, page_name: str, winui_table_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI pivot table into a WebUI table widget and attach it to the target page.
    
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
    :param winui_table_xml: XML element representing the WinUI pivot table definition.
    :type winui_table_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data when content can be translated.
    :rtype: None
    """


    stable_id = win_object_tools.compute_stable_id(winui_table_xml, ancestor_info)
    content_lists_expected = {
        "objecttype" : "table",
        "rowHeader"  : 1,
        "colHeader"  : 1,
        "header"     : 0,
        "aggregated" : 1,
        "stacked"    : 0,
        "overlays"   : 0,
        "grouped"    : 0 }
    table_info_dict = win_object_tools.investigate_contents(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_table_xml, content_lists_expected, stable_id)
    if table_info_dict != {}:
        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_table_xml, ancestor_info)
        # Fall back to the Pivot Table's own Symbols-axis Header_Title (see
        # win_object_tools.investigate_contents) when nothing else - a caption Text object,
        # win_layout.py - already supplied a title.
        if not title:
            title = table_info_dict.get('header_title')
        if not title:
            title = win_object_tools.resolve_sole_identifier_title(aimms_model, component_dict, winui_table_xml)
        webui.add_data_widget(aimms_model, gii_dict, webui_page_dict, table_info_dict, content_lists_expected, ancestor_info, stable_id, area, title, visible_expr)
