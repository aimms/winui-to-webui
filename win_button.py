from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET
import win_procedure

import web_page
import win_object_tools
from aimmspy.project.project import Project, Model

def winpage_button(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_table_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a single WinUI button into a WebUI button widget and attach it to the target page.
    
    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used to construct supporting procedures.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary to which the widget will be added.
    :type webui_page_dict: dict
    :param page_name: Name of the page being processed.
    :type page_name: str
    :param winui_table_xml: XML element representing the WinUI button definition.
    :type winui_table_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data and supporting procedure when an action sequence is present.
    :rtype: None
    """
    stable_id = win_object_tools.compute_stable_id(winui_table_xml, ancestor_info)

    action_sequence: ET.Element = None
    info_dict = {
        'procedure' : '', # to be determined
        'title'     : '', # to be determined
        'IsLiteral' : -1  # to be determined as well 😉
    }

    for button_child_element in winui_table_xml:
        if button_child_element.tag == "Title":
            info_dict["title"] = str(button_child_element.text)
            # todo, determine if this title is a literal or a string parameter.
        elif button_child_element.tag == "ActionSequence":
            action_sequence = button_child_element

    if action_sequence != None:
        action_dict = win_procedure.work_action_sequence_into_procedure(aimms_model, gii_dict, component_dict, webui_page_dict,
                page_name, 'button_action_sequence', action_sequence, stable_id )
        info_dict['procedure'] = action_dict['name']
        info_dict['IsLiteral'] = action_dict['IsLiteral']

    area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_table_xml, ancestor_info)
    webui.add_button_widget(webui_page_dict, info_dict, stable_id, area, title, visible_expr)
