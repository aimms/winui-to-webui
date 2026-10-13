# Process a WinUI page and convert it to a WebUI page, adding it to the WebUI structure.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import pathlib
import web_page
import win_object
import win_layout
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

    # Give every PageObject on this page (its own, and any inherited template ones below) a
    # stable identity to name from - the page's own slug, plus a per-page object counter.
    # See win_object_tools.compute_stable_id(). A fresh dict per page/call, so this never
    # leaks between pages (unlike ancestor_info, which callers may share/copy across siblings).
    page_ancestor_info = dict(ancestor_info)
    page_ancestor_info['page_slug'] = page_slug
    page_ancestor_info['object_counter'] = {'n': 0}

    # AIMMS's Data Pages framework auto-generates one page per editable identifier, named
    # "[Data Page] <identifier>" (see PageManager.xml), furnished with its own standard
    # Close/Undo/navigation buttons (WinUI Data Page chrome - see win_object.winpage_object and
    # win_layout.compute_page_layout) that have no WebUI equivalent and shouldn't reserve grid
    # space either.
    page_ancestor_info['is_data_page'] = page_name.startswith('[Data Page]')

    # Parse the WinUI page XML.
    winui_page_filename = os.path.join( component_dict["Path"], "Pages", page_name + ".xml" )
    winui_page_tree = ET.parse(winui_page_filename)
    winui_page_root = winui_page_tree.getroot()

    # Also locate (parse, but don't yet dispatch) any ancestors in the template tree - a page
    # inherits every PageObject placed on its template(s), so those need to be part of the
    # layout heuristic's input too, visually part of the same page.
    template_page_roots = []
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
                    print(f"Internal error: non-template page in template tree for page '{page_name}' - "
                          f"element <{template_node_parent.tag} Name=\"{template_node_parent.attrib.get('Name', '')}\">")

                winui_template_page_name = template_node_parent.attrib.get('Name','')
                winui_template_page_filename = os.path.join( component_dict["Path"], "Templates", winui_template_page_name + ".xml" )
                winui_template_page_path = pathlib.Path(winui_template_page_filename)
                if winui_template_page_path.exists():
                    winui_template_page_tree = ET.parse(winui_template_page_filename)
                    winui_template_page_root = winui_template_page_tree.getroot()
                    template_page_roots.append(winui_template_page_root)

                # go to the parent of this node.
                template_node_parent = template_node_parent.getparent()

    # Pre-pass: try to detect a CSS grid layout from the combined set of PageObjects (this
    # page's own, plus every inherited template's, in the same order the dispatch loops below
    # walk them) before any widget is converted. See win_layout.compute_page_layout().
    combined_page_objects = [c for c in winui_page_root if c.tag == 'PageObject']
    for template_page_root in template_page_roots:
        combined_page_objects.extend(c for c in template_page_root if c.tag == 'PageObject')
    if gii_dict.get("_network") == "ignore":
        # --network=ignore: no widget is made for a Network Object, so it must not reserve grid space.
        combined_page_objects = [c for c in combined_page_objects if c.get('Type') != 'Network Object']
    page_ancestor_info['layout_plan'] = win_layout.compute_page_layout(
        combined_page_objects, ignore_buttons=page_ancestor_info['is_data_page'])
    if page_ancestor_info['layout_plan'] is None and win_layout.page_has_layoutable_objects(
            combined_page_objects, page_ancestor_info['is_data_page']):
        # web_page.add_page_to_pages_list falls back to a generic Layout9/Layout10 grid whenever
        # there's no custom LayoutPlan to register - flag that here, once, so a real project's
        # conversion.md surfaces every page that got the generic fallback instead of a layout
        # actually fitted to its own WinUI object positions, for manual review/touch-up. Only
        # when the page actually had something to lay out in the first place
        # (page_has_layoutable_objects) - an empty page, or one that's just a Navigation Object
        # tree (e.g. a generic "All Data Pages" page), trivially has no better layout to find and
        # isn't worth a review item.
        converter_logging.exotic([
            f"Could not determine a good layout for page '{page_name}' (slug '{page_slug}') - falling back to a generic grid layout."
        ])

    webui_page_dict = webui.add_page_to_pages_list(page_slug, ancestor_info, page_ancestor_info['layout_plan'])

    # Dispatch pass - same order/loops as before, just over the already-parsed roots above
    # (element identity must stay stable between the pre-pass and here for the layout plan's
    # id()-keyed lookups to resolve). A PageObject the layout plan folded into another widget's
    # title (see LayoutPlan.is_absorbed) is skipped entirely - it must not become its own widget.
    for winui_page_child in winui_page_root:
        if page_ancestor_info['layout_plan'] is not None and page_ancestor_info['layout_plan'].is_absorbed(winui_page_child):
            continue
        win_object.winpage_object(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_manager_xml_node, winui_page_child, page_ancestor_info )

    for winui_template_page_root in template_page_roots:
        for winui_template_page_child in winui_template_page_root:
            if page_ancestor_info['layout_plan'] is not None and page_ancestor_info['layout_plan'].is_absorbed(winui_template_page_child):
                continue
            win_object.winpage_object(webui, aimms_model, gii_dict, component_dict, webui_page_dict, page_manager_xml_node, winui_template_page_child, page_ancestor_info )



    
