from typing import List, Dict, Tuple, Any, Union, Optional # Add Tuple and any other types you use
import lxml.etree as ET
import converter_logging
import pathlib
import win_page
import web_page
import os
from aimms_slug import aimms_slug
from aimmspy.project.project import Project, Model

process_page_number = 0
def get_next_process_page_number()-> int:
    """
    Return the next sequential page number used for logging during conversion.
    
    :return: Incremented page counter used in conversion logs.
    :rtype: int
    """
    global process_page_number

    process_page_number += 1
    return process_page_number

def process_page_xml_node(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, page_manager_webui_node:dict, page_manager_winui_node:ET.Element, component_dict:dict, ancestor_info:dict, current_page_slug: Optional[str] = None, ancestor_page_names: Optional[List[str]] = None) -> None:
    """
    Traverse a PageManager XML node and process each page entry, recursing through nested page structures.

    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used during widget conversion.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param page_manager_webui_node: Parent WebUI node where converted pages will be attached.
    :type page_manager_webui_node: dict
    :param page_manager_winui_node: PageManager XML element currently being processed.
    :type page_manager_winui_node: ET.Element
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :param current_page_slug: Slug of the page whose children are being iterated here (the
        immediate PageManager.xml parent of every child page processed in this call), or None at
        the top level (PageManager.xml's own root isn't itself a page). Recorded into
        gii_dict["_page_parent_slug"] for every child page discovered here, keyed by
        (id(component_dict), that child's own slug) - gii_module.ensure_page_section consults
        this registry so a page's generated identifiers are filed into a Section nested inside
        its own parent page's Section, mirroring PageManager.xml's page tree instead of dumping
        every page's Section flat under the module.
    :type current_page_slug: Optional[str]
    :param ancestor_page_names: WinUI Page Manager tree names of every ancestor of the pages
        processed in this call, outermost first (e.g. ["Main", "Application Input", "Unit Data"]
        for pages nested under Main > Application Input > Unit Data), or None/empty at the top
        level. Logged alongside each page's own conversion.md heading (see get_next_process_page_
        number's own call site below) as a "Main > ... > <this page>" breadcrumb, so navigating to
        a flagged page in the WinUI IDE's own Page Manager tree doesn't require hunting for it.
    :type ancestor_page_names: Optional[List[str]]
    :return: None. Adds pages to the WebUI structure and triggers page conversion.
    :rtype: None
    """
    ancestor_page_names = ancestor_page_names or []

    for page_manager_xml_child in page_manager_winui_node:

        # Get page name and slug
        page_manager_child_name = page_manager_xml_child.attrib.get('Name','')
        page_manager_child_slug = aimms_slug(page_manager_child_name)
        # print(f"Pagechild: {page_manager_child_name} (slug: {page_manager_child_slug})")

        # For now, only process Page tags.
        page_manager_xml_tag = page_manager_xml_child.tag
        if page_manager_xml_tag == 'Page':

            page_name = page_manager_xml_child.attrib.get('Name','')
            page_slug = page_slug = aimms_slug(page_name)
            winui_page_filename = os.path.join( component_dict["Path"], "Pages", page_name + ".xml" )
            winui_page_filepath = pathlib.Path(winui_page_filename)

            if winui_page_filepath.exists():

                loc_page_number = get_next_process_page_number()
                breadcrumb = " > ".join(ancestor_page_names + [page_name])
                if component_dict["Prefix"] == '':
                    converter_logging.lines([f"## {loc_page_number} Page '{breadcrumb}' with slug {page_slug}"])
                else:
                    converter_logging.lines([f"## {loc_page_number} From libary {component_dict["DisplayName"]} Page '{breadcrumb}' with slug {page_slug}"])

                prescan_info = win_page.prescan_page(aimms_model, gii_dict, page_manager_xml_child, component_dict)
                if "page_name" in prescan_info:
                    if "IsLiteral" in prescan_info:
                        is_literal = prescan_info["IsLiteral"]
                        if is_literal == 1:
                            page_manager_child_name = prescan_info["page_name"]
                        else:
                            pmcn = page_manager_child_name
                            if component_dict["Prefix"] != '':
                                pmcn = component_dict["Prefix"]+'::'+pmcn
                            converter_logging.exotic(["The WinUI title of a page is only converted to webui::PageName for literal titles.",
                                f"The title \"{prescan_info['page_name']}\" of {page_manager_child_name} (slug {page_manager_child_slug}) is an identifier.",
                                f"As an alternative, you may want to put {prescan_info['page_name']} in the status message."])
                gii_dict.setdefault("_page_parent_slug", {})[(id(component_dict), page_slug)] = current_page_slug
                has_tabbed_widget = prescan_info.get('has_tabbed_widget',0)
                page_tree_child_webui = webui.add_page_to_tree(page_manager_webui_node, page_manager_child_name, page_manager_child_slug)
                child_ancestor_info = ancestor_info.copy()
                if has_tabbed_widget == 1:
                    child_ancestor_info['has_tabbed_widget'] = has_tabbed_widget
                process_page_xml_node(webui, aimms_model, gii_dict, page_tree_child_webui, page_manager_xml_child, component_dict, child_ancestor_info, page_slug, ancestor_page_names + [page_name]) # recusive call
                # Adding the page to the pages list, and adding widgets will be done in:
                win_page.process_page(webui, aimms_model, gii_dict, page_manager_xml_child, component_dict, ancestor_info) 
            else:
                print(f"Warning: the Page \"{winui_page_filename}\" does not exist.")
        elif page_manager_xml_tag != 'Separator':
            print(f"Warning: skipping Page {page_manager_child_slug} with tag {page_manager_xml_tag}")


def process_page_manager_file(webui: web_page.WebUI, aimms_model: Model, gii_dict:dict, component_dict:dict) -> int:
    """ 
    Process `PageManager.xml` to convert WinUI pages into AIMMS WebUI structures for a component.

    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used during widget conversion.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :return: 1 when WebUI data is produced (even for default main model), otherwise 0.
    :rtype: int
    """ 
    page_manager_file = os.path.join( component_dict["Path"], "PageManager.xml" )
    page_manager_path = pathlib.Path(page_manager_file)
    if page_manager_path.exists():
        print(f"Processing Page Manager file: {page_manager_file}")

        try:
            page_manager_tree = ET.parse(page_manager_file)
            page_manager_root_winui = page_manager_tree.getroot()

            page_manager_root_webui = webui.get_root_page()

            ancestor_info = {}

            process_page_xml_node(webui, aimms_model, gii_dict, page_manager_root_webui, page_manager_root_winui, component_dict, ancestor_info)  
            return 1
        except ET.ParseError as e:
            print(f"Warning: could not parse {component_dict['Path']}/PageManager.xml: {e}")
            # if it is the Main Model, we still should create the default (empty) WebUI.
            if component_dict["Prefix"] == "":
                return 1
            else:
                return 0
    else:
        return 0

    
