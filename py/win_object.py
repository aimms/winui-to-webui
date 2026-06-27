# Converts a WinUI page object to a WebUI widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
from aimms_slug import aimms_slug
import converter_logging
import lxml.etree as ET
import web_page
import win_barchart
import win_button
import win_classic_table
import win_composite_table
import win_elemselec
import win_pivot_table
import win_linechart
import win_scalar
import win_tabbed_page
import win_text
import win_document_viewer
import win_picture
from aimmspy.project.project import Project, Model

no_object_type_rectangle = 0
no_object_type_line = 0

def report_ignored_lines_rectangles() -> None:
    """
    Report the number of ignored line and rectangle objects to the conversion log.
    
    :return: None. Appends a summary line to the converter log file.
    :rtype: None
    """
    global no_object_type_rectangle
    global no_object_type_line
    converter_logging.lines([f"During the conversion {no_object_type_rectangle} lines and {no_object_type_line} rectangles were ignored."])

def winpage_object(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_manager_xml_node: ET.Element, winui_page_xml: ET.Element, ancestor_info:dict) -> None:
    """
    Convert a single WinUI page object into the corresponding WebUI widget and attach it to the page definition.
    
    :param webui: WebUI helper used to build and persist the widget definitions.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used to inspect identifiers during conversion.
    :type aimms_model: Model
    :param gii_dict: Dictionary containing runtime library nodes and helpers.
    :type gii_dict: dict
    :param component_dict: Component metadata for the current project element.
    :type component_dict: dict
    :param webui_page_dict: Page dictionary representing the target WebUI page.
    :type webui_page_dict: dict
    :param page_name: Name of the page being converted.
    :type page_name: str
    :param winui_page_xml: XML element describing the WinUI page object to convert.
    :type winui_page_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Adds the converted widget to the WebUI data structures or logs unsupported types.
    :rtype: None
    """

    # Get page name and slug
    page_name = page_manager_xml_node.attrib.get('Name','')
    page_slug = aimms_slug(page_name)

    if winui_page_xml.tag == 'PageObject':
        type_attrib = 'Type'
        if type_attrib in winui_page_xml.attrib:
            # print(f" and type = {winui_page_xml.attrib[type_attrib]}")
            object_type_attrib = winui_page_xml.attrib[type_attrib]
            if  object_type_attrib == 'Table':
                win_classic_table.winpage_classic_table(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Composite Table':
                win_composite_table.winpage_composite_table(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Pivot Table':
                win_pivot_table.winpage_pivot_table(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Curve':
                win_linechart.winpage_linechart(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Bar Chart':
                win_barchart.winpage_barchart(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Button':
                win_button.winpage_button(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Scalar':
                win_scalar.winpage_scalar(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Selection Object':
                win_elemselec.winpage_selectionbox(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Text':
                win_text.winpage_text(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Document Viewer':
                win_document_viewer.winpage_document_viewer(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Picture':
                win_picture.winpage_picture(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_name, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Tabbed Page Object':
                win_tabbed_page.winpage_tabbed_page(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_manager_xml_node, winui_page_xml, ancestor_info)
            elif object_type_attrib == 'Line':
                global no_object_type_line
                no_object_type_line += 1
            elif object_type_attrib == 'Rectangle':
                global no_object_type_rectangle
                no_object_type_rectangle += 1
            else:
                converter_logging.exoticW([f"Conversion for the page object type {object_type_attrib} on page {page_name} is not yet implemented, or maybe not possible",
                    "see also https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/index.html"],
                    component_dict, "page object type", page_name)
                
    elif winui_page_xml.tag == 'Action':
        for action_child in winui_page_xml:
            if action_child.tag == 'EntryProcedure':
                webui.set_procedure_onload(webui_page_dict, str(action_child.text))
            elif action_child.tag == 'ExitProcedure':
                webui.set_procedure_uponleave(webui_page_dict, str(action_child.text))
            else:
                print(f"Warning unknown type of page action: {action_child.tag} on page {page_name} with slug {page_slug}")
