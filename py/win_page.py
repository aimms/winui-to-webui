# Process a WinUI page and convert it to a WebUI page, adding it to the WebUI structure.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import pathlib
import web_page
import win_object
import tools
import os
from aimmspy.project.project import Project, Model
from aimms_slug import aimms_slug
import converter_logging

def prescan_page(aimms_model: Model, gii_dict: dict, page_manager_xml_node:ET.Element, component_dict:dict) -> dict:
    """
    Pre-scan a WinUI page definition to collect its name and whether the page title is literal.
    in addition, check if the page has a tabbed widget.
    
    :param aimms_model: AIMMS model handle (not used directly but kept for signature consistency).
    :type aimms_model: Model
    :param gii_dict: Dictionary containing runtime library identifiers and handles.
    :type gii_dict: dict
    :param page_manager_xml_node: XML element for the page entry in `PageManager.xml`.
    :type page_manager_xml_node: ET.Element
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :return: Dictionary with page metadata such as the resolved page name and literal flag.
    :rtype: dict
    """

    # Get page name and slug
    page_name = page_manager_xml_node.attrib.get('Name','')
    # page_slug = aimms_slug(page_name)
    is_literal = 1 
    has_tabbed_widget = 0
    #print(f"prescan_page: {page_name} (slug: {page_slug})")

    # Parse the WinUI page XML, and process its PageObject children
    winui_page_filename = os.path.join( component_dict["Path"], "Pages", page_name + ".xml" )
    winui_page_filepath = pathlib.Path(winui_page_filename)

    if winui_page_filepath.exists():
        winui_page_tree = ET.parse(winui_page_filename)
        winui_page_root = winui_page_tree.getroot()
        for winui_page_child in winui_page_root:
            if winui_page_child.tag == 'Title':
                page_name = str(winui_page_child.text)
                if len(page_name) > 2 and page_name[0] == '"' and page_name[-1] == '"':
                    page_name = page_name[1:-1]
                    is_literal = 1
                else:
                    is_literal = 0  
            if winui_page_child.tag == 'PageObject':
                if 'Type' in winui_page_child.attrib:
                    if winui_page_child.attrib['Type'] == 'Tabbed Page Object':
                        has_tabbed_widget = 1
    else:
        page_name = winui_page_filename
        is_literal = 1
        has_tabbed_widget = 0

    prescan_info = {
        "page_name": page_name,
        "IsLiteral": is_literal,
        "has_tabbed_widget" : has_tabbed_widget
    }

    return prescan_info



def process_page(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, page_manager_xml_node:ET.Element, component_dict:dict, ancestor_info:dict) -> None:
    """
    Convert a WinUI page file into a WebUI page definition and process all page objects (including inherited templates).
    
    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used during widget conversion.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param page_manager_xml_node: XML element for the page entry in `PageManager.xml`.
    :type page_manager_xml_node: ET.Element
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Adds the converted page and its widgets to the WebUI data.
    :rtype: None
    """

    # Get page name and slug
    page_name = page_manager_xml_node.attrib.get('Name','')
    page_slug = aimms_slug(page_name)

    webui_page_dict = webui.add_page_to_pages_list(page_slug,ancestor_info)
    
    # Parse the WinUI page XML, and process its PageObject children
    winui_page_filename = os.path.join( component_dict["Path"], "Pages", page_name + ".xml" )

    winui_page_tree = ET.parse(winui_page_filename)
    winui_page_root = winui_page_tree.getroot()
    for winui_page_child in winui_page_root:
        win_object.winpage_object(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_manager_xml_node, winui_page_child, ancestor_info )

    # also need to visit the ancestors in the template tree.
    template_manager_file = os.path.join( component_dict["Path"], "TemplateManager.xml" )
    template_manager_path = pathlib.Path(template_manager_file)
    if template_manager_path.exists():
        template_manager_tree = ET.parse(template_manager_file)
        template_manager_root_winui = template_manager_tree.getroot()
        findstr = f".//*[@Name='{page_name}']"
        template_node_list = []
        template_node_list = template_manager_root_winui.findall(findstr)
        if len(template_node_list):
            if len(template_node_list) > 1:
                print(f"Warning page {winui_page_filename} is encountered multiple times in the template tree; only first one is processed.")
            template_node_leaf = template_node_list[0]
            template_node_parent_list = template_node_leaf.findall('..')
            template_node_parent = template_node_parent_list[0]
            while template_node_parent.tag != 'TemplateManager':
                if template_node_parent.tag != 'Template':
                    print("Internal error : non template page in template tree")

                # Visit the page objects in the template page.
                winui_template_page_name = template_node_parent.attrib.get('Name','')
                winui_template_page_filename = os.path.join( component_dict["Path"], "Templates", winui_template_page_name + ".xml" )
                winui_template_page_tree = ET.parse(winui_template_page_filename)
                winui_template_page_root = winui_template_page_tree.getroot()
                for winui_template_page_child in winui_template_page_root:
                    win_object.winpage_object(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_manager_xml_node, winui_template_page_child, ancestor_info )

                # go to the parent of this node.
                template_node_parent = template_node_parent.getparent()



    
