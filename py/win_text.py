# Converts a WinUI scalar object to a WebUI scalar widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
import win_expression
from aimmspy.project.project import Project, Model

def winpage_text(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_text_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI text object into a WebUI text widget and attach it to the target page.
    
    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used for compatibility with other converters.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary to which the widget will be added.
    :type webui_page_dict: dict
    :param page_name: Name of the page being processed.
    :type page_name: str
    :param winui_text_xml: XML element representing the WinUI text definition.
    :type winui_text_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data based on literal text or string parameters.
    :rtype: None
    """
    
    info_dict: dict[str, Any] = {}
    for text_child in winui_text_xml:
        if text_child.tag == 'StaticText':
            literal_text = str(text_child.text)
            info_dict["LiteralText"] = literal_text
            info_dict["IsLiteral"] = 1
        elif text_child.tag == 'StringParameter':
            literal_text = str(text_child.text)
            # print(f"winpage_text, {literal_text}")
            if literal_text.startswith('STRING'):
                literal_text = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, "substitute_STRING_def", literal_text)
            elif literal_text.find('(') >= 0:
                literal_text = win_expression.make_webui_scalar_reference(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, "substitute_reference", literal_text,"string", "") 
            info_dict["LiteralText"] = literal_text
            info_dict["IsLiteral"] = 0
    if info_dict != {}:
        webui.add_text_widget(webui_page_dict, info_dict)
