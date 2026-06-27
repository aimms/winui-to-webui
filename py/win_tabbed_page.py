# Converts a WinUI scalar object to a WebUI scalar widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET
from aimms_slug import aimms_slug
import modeledit_aimmspy
import modeledit_aimmspy2
import converter_logging

import web_page
import win_object_tools
import win_expression
from aimmspy.project.project import Project, Model

substitution_number = 0

def get_next_substitution_number() -> int:
    """
    Return the next substitution number and increment the global counter.
    
    :return: Incremented substitution counter for generated identifiers.
    :rtype: int
    """
    global substitution_number
    substitution_number += 1
    return substitution_number



def winpage_tabbed_page(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_manager_xml_node: ET.Element, winui_text_xml:ET.Element, ancestor_info:dict) -> None:
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
    :param page_manager_xml_node: XML element for the page entry in `PageManager.xml`.
    :type page_manager_xml_node: ET.Element
    :param winui_text_xml: XML element representing the WinUI text definition.
    :type winui_text_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Generates widget data based on literal text or string parameters.
    :rtype: None
    """

   # Get page name and slug
    page_name = page_manager_xml_node.attrib.get('Name','')
    page_slug = aimms_slug(page_name)

    def_lines: list[str] = ['{\n']
    tab_no = 1
    for child_page in page_manager_xml_node:
        child_page_name = child_page.attrib.get('Name','')
        child_page_slug = aimms_slug(child_page_name)
        if tab_no > 1:
            def_lines.append(",\n\n")
        def_lines.append(f"    ('{tab_no}', 'displayText' ) : \"{child_page_name}\",\n")
        def_lines.append(f"    ('{tab_no}', 'pageId'      ) : \"{child_page_slug}\",\n")
        def_lines.append(f"    ('{tab_no}', 'tooltip'     ) : \"\",\n")
        def_lines.append(f"    ('{tab_no}', 'icon'        ) : \"\",\n")
        def_lines.append(f"    ('{tab_no}', 'iconcolor'   ) : \"\",\n")
        def_lines.append(f"    ('{tab_no}', 'state'       ) : \"Active\"")
        tab_no += 1
    def_lines.append("\n}\n")

    if tab_no > 1:
        def_body = "".join(def_lines)

        sub_number = get_next_substitution_number()
        new_name = f"sp_{page_slug}_tabbed_widget_{sub_number}"
        if component_dict['Prefix'] != "":
            new_name = f"{component_dict['Prefix']}_{new_name}"   
        new_ref = f"{gii_dict['Prefix']}::{new_name}"
        # Create the new string parameter in the AIMMS model.   
        modeledit_aimmspy2.create(aimms_model, new_name, "string parameter", gii_dict["gui_expression_substitutions"], 0)
        modeledit_aimmspy2.setAttributeText(aimms_model, new_ref, "index domain", "(webui::indexNoOfTabs,webui::indexTabSpec)" )
        modeledit_aimmspy2.setAttributeText(aimms_model, new_ref, "definition", def_body )
        modeledit_aimmspy2.doCompile(aimms_model, new_ref)

        info_dict = {
            "tabbed_configuration" : new_ref
        }

        webui.add_tabbed_widget(webui_page_dict, info_dict, ancestor_info)
    else:
        converter_logging.exoticW([f"Conversion for the tabbed page on page {page_name} failed because it did not have child pages.",
            "https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Tabbed%20Page/index.html"],
            component_dict, "tabbed page object", page_name)
