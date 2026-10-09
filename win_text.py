# Converts a WinUI scalar object to a WebUI scalar widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
import win_expression
import win_layout
from aimmspy.project.project import Project, Model

def winpage_text(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, 
                 page_name: str, winui_text_xml:ET.Element, ancestor_info:dict) -> None:
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
    
    stable_id = win_object_tools.compute_stable_id(winui_text_xml, ancestor_info)

    if win_layout.is_empty_text_object(winui_text_xml):
        # No actual text content (an empty/self-closing <StaticText/>, or none at all) - treat
        # as if this object didn't exist, rather than emit a widget with a bogus/blank literal.
        return

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
                literal_text = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict, 
                                                                                "substitute_STRING_def", literal_text, stable_id, 0)
            elif literal_text.find('(') >= 0:
                index_domain = ""
                literal_text = win_expression.make_webui_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "substitute_reference",
                                                                        literal_text, index_domain, "string", "", stable_id, 0)
            info_dict["LiteralText"] = literal_text
            info_dict["IsLiteral"] = 0
    if winui_text_xml.findtext('SourceType') == 'File':
        # The text is the contents of a file: <FileName LiteralFileName="true">"name.txt"</FileName>
        # (a quoted literal, relative to the project folder), or with LiteralFileName="false" a
        # string expression yielding the name. Read at run time via a generated string parameter
        # defined as FileRead(...), so a changed file shows changed text - same as WinUI.
        file_name_el = winui_text_xml.find('FileName')
        file_name = (file_name_el.text or '').strip()
        if file_name_el.get('LiteralFileName', 'true') != 'true':
            file_name = win_object_tools.namespace_qualification(aimms_model, file_name, component_dict['Prefix'])
        info_dict["LiteralText"] = win_expression.make_webui_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "file_text",
                                                                      f"FileRead( {file_name} )", "", "string", "", stable_id, 0)
        info_dict["IsLiteral"] = 0
    if info_dict != {}:
        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_text_xml, ancestor_info)
        webui.add_text_widget(webui_page_dict, info_dict, stable_id, area, title, visible_expr)
