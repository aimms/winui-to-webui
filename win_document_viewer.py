# Converts a WinUI scalar object to a WebUI scalar widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
import win_expression
from aimmspy.project.project import Project, Model

def winpage_document_viewer(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_document_viewer_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI document viewer into a WebUI iframe widget and attach it to the target page.
    
    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle (not used directly but kept for signature consistency).
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary to which the widget will be added.
    :type webui_page_dict: dict
    :param page_name: Name of the page being processed.
    :type page_name: str
    :param winui_document_viewer_xml: XML element representing the WinUI document viewer definition.
    :type winui_document_viewer_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data when a document URL is available.
    :rtype: None
    """
    
    stable_id = win_object_tools.compute_stable_id(winui_document_viewer_xml, ancestor_info)

    info_dict: dict[str, Any] = {}
    for text_child in winui_document_viewer_xml:
        if text_child.tag == 'Contents':
            for text_grandchild in text_child:
                if text_grandchild.tag == 'Document_URL':
                    is_literal = 0
                    if 'LiteralFileName' in text_grandchild.attrib:
                        is_literal_txt = str(text_grandchild.attrib['LiteralFileName'])
                        if is_literal_txt == 'true' or is_literal_txt == '1':
                            is_literal = 1
                    literal_text = str(text_grandchild.text)
                    if len(literal_text) > 2 and literal_text[0] == '"' and literal_text[-1] == '"':
                        literal_text = literal_text[1:-1]
                    if ( is_literal == 0 ) and ( literal_text.find('(') >= 0 ):
                        literal_text = win_expression.make_webui_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "substitute_reference", literal_text, "", "string", "", stable_id, 0)
                    info_dict["LiteralText"] = literal_text
                    info_dict["IsLiteral"] = is_literal

    if info_dict != {}:
        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_document_viewer_xml, ancestor_info)
        webui.add_iframe_widget(webui_page_dict, info_dict, stable_id, area, title, visible_expr)
