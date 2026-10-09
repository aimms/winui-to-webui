# Converts a WinUI scalar object to a WebUI scalar widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
import win_layout
from aimmspy.project.project import Project, Model

def winpage_scalar(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_table_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI scalar object into a WebUI scalar widget and attach it to the target page.
    
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
    :param winui_table_xml: XML element representing the WinUI scalar definition.
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

    content_lists_expected = {
        "objecttype" : "scalar",
        "rowHeader"  : 0,
        "colHeader"  : 0,
        "header"     : 0,
        "aggregated" : 0,
        "stacked"    : 0,
        "overlays"   : 0,
        "grouped"    : 0 }
    info_dict = win_object_tools.investigate_contents(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_table_xml, content_lists_expected, stable_id)
    if info_dict != {}:
        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_table_xml, ancestor_info)
        webui.add_data_widget(aimms_model, gii_dict, webui_page_dict, info_dict, content_lists_expected, ancestor_info, stable_id, area, title, visible_expr)
