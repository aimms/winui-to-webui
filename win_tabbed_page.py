# Converts a WinUI scalar object to a WebUI scalar widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET
from aimms_slug import aimms_slug
import modeledit_aimmspy
import converter_logging

import web_page
import win_object_tools
import win_expression
import ams_file_editor as afe
import gii_module
from aimmspy.project.project import Project, Model

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

   # Get page name
    page_name = page_manager_xml_node.attrib.get('Name','')
    stable_id = win_object_tools.compute_stable_id(winui_text_xml, ancestor_info)

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

        candidate_name = f"sp_tabbed_widget_{stable_id}"
        if component_dict['Prefix'] != "":
            candidate_name = f"{component_dict['Prefix']}_{candidate_name}"
        lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""
        index_domain = "(webui::indexNoOfTabs,webui::indexTabSpec)"

        # Reuse an equivalent tab-configuration parameter already created this run (same
        # definition - see gii_module.dedup_parameter) instead of minting a redundant new one.
        # Filed into this page's own Section (see gii_module.ensure_page_section).
        expr_subst = gii_module.ensure_page_section(gii_dict, component_dict, ancestor_info.get('page_slug', ''))
        usage = f"Used for tabbed page configuration on {stable_id}"
        new_name, is_new, comment_command = gii_module.dedup_parameter(gii_dict, component_dict, "string parameter", index_domain,
                                                                         None, def_body, candidate_name, usage)
        new_ref = f"{lib_prefix}{gii_module.get_prefix(component_dict)}::{new_name}"
        if is_new:
            # Queue creation of the new string parameter - applied to the .ams file once AIMMS is done (see ams_file_editor.py).
            gii_dict["_edit_queue"].append(afe.AddIdentifier(name=new_name, type="string parameter", parent=expr_subst, file_hint=component_dict["AmsPath"]))
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=new_ref, attribute="IndexDomain", value=index_domain))
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=new_ref, attribute="Definition", value=def_body))
        gii_dict["_edit_queue"].append(comment_command)

        info_dict = {
            "tabbed_configuration" : new_ref
        }

        area, title, visible_expr = win_object_tools.compute_layout_slot(aimms_model, gii_dict, component_dict, winui_text_xml, ancestor_info)
        webui.add_tabbed_widget(webui_page_dict, info_dict, ancestor_info, stable_id, area, title, visible_expr)
    else:
        converter_logging.exoticW([f"Conversion for the tabbed page on page {page_name} failed because it did not have child pages.",
            "https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Tabbed%20Page/index.html"],
            component_dict, "tabbed page object", page_name)
