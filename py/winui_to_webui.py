from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
import shutil
import os
#from lxml import etree as ET
import lxml.etree as ET

import pathlib  
import win_pagemanager
import web_page
import json
from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import modeledit_aimmspy2
from aimms_slug import aimms_slug
import tools
import identifier_element_text
import manipulate_main_model
import converter_logging
import win_object

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modeledit_aimmspy import Model

def process_aimms_app(project_folder:str, project_name:str) -> None:
    """
    Convert all WinUI pages of an AIMMS project into WebUI format for the specified project folder and name.
    
    :param project_folder: Folder path where the AIMMS project resides.
    :type project_folder: str
    :param project_name: Name of the AIMMS project (without extension).
    :type project_name: str
    :return: None. Generates WebUI output, supporting runtime libraries, and writes conversion logs.
    :rtype: None
    """

    # Ensure the project folder exists
    project_folder_path = pathlib.Path(project_folder)
    if not project_folder_path.exists():
        raise FileNotFoundError(f"Project folder'{project_folder}' does not exist.")

    print(f"Processing AIMMS project '{project_name}' in folder '{project_folder}'")

    # First copy two AIMMS libraries into the project at hand.
    shutil.copytree('GeneratedInterfaceIdentifiersLibrary', os.path.join(project_folder, 'GeneratedInterfaceIdentifiersLibrary'), dirs_exist_ok=True)
    shutil.copytree('ModelEditAimmsPython',  os.path.join(project_folder, 'ModelEditAimmsPython'), dirs_exist_ok=True)

    # what is the current working directory?    
    cwd = os.getcwd()

    # Change working directory to the project folder.
    os.chdir(project_folder)

    # tools.optdel("MainProject\\WebUI\\webui.json")
    # tools.optdel("sampleLib\\WebUI\\webui.json")

    project_file = f"{project_name}.aimms"
    if not os.path.exists(project_file):
        raise FileNotFoundError(f"Project file '{project_file}' not found.")
    
    # Open conversion log
    converter_logging.open_log(project_name)

    # wipe any existing GeneratedInterfaceIdentifiersLibrary from the project file, as we're going to re-create it.
    manipulate_main_model.removeLibrary(project_file, "GeneratedInterfaceIdentifiersLibrary" )

    manipulate_main_model.ensureSystemLibrary(project_file,"AimmsPro" )
    webui_dict = {
        "UUID"    : "69378F70-E906-486F-8F2C-1D606AEB9669",
        "Name"    : "WebUI",
        "Version" : "25.9.1.0"
    }
    manipulate_main_model.ensureRepositoryLibrary(project_file, "WebUI", webui_dict)
    manipulate_main_model.ensureExistingLibrary(project_file, "ModelEditAimmsPython" )

    project_file_xml_tree = ET.parse(project_file)
    project_file_xml_tree_root = project_file_xml_tree.getroot()

    # Initialize the aimmspy model.
    aimms_model : Model 
    aimms_model = modeledit_aimmspy.initialize_aimms_model(project_name)
    # aimmspy will generate an include python file (extension .pyi)
    # we need to append a signature for the function that initializes the AIMMS model
    # for type checking purposes.
    python_script_dir = pathlib.Path(__file__).parent
    python_include_filename = "modeledit_aimmspy.pyi"
    python_include_absolute_filepath = python_script_dir / python_include_filename
    with open(python_include_absolute_filepath, "a") as f:
        f.write("def initialize_aimms_model( am_pn:str) -> Model: ...\n")

    # # And test it.
    # id = "p_cc"
    # d = modeledit_aimmspy2.getDim(aimms_model,id)
    # print(f"process_aimms_app() Dimension of {id} is {d}")

    # Create the runtime library that will contain the generated procedure.
    gii_dict = {}

    gii_dict["sp_runtimeLib"] = modeledit_aimmspy2.createLibrary(aimms_model, "GeneratedInterfaceIdentifiersLibrary", "gii")
    gii_dict["Prefix"] = "gii"  
    gii_dict["sp_public_section"] = modeledit_aimmspy2.create(aimms_model, "Public_Section", 'Section', gii_dict["sp_runtimeLib"], 0)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["sp_runtimeLib"], 'interface', "Public_Section")
    gii_dict["gui_expression_substitutions"] = modeledit_aimmspy2.create(aimms_model, "gui_expression_substitutions", 'declaration', gii_dict["sp_public_section"], 0)
    gii_dict["s_readonly_values"] = modeledit_aimmspy2.create(aimms_model, "s_readonly_values", 'set', gii_dict["gui_expression_substitutions"], 0)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["s_readonly_values"], 'definition',"data { False, True }")
    gii_dict["s_visibility_values"] = modeledit_aimmspy2.create(aimms_model, "s_visibility_values", 'set', gii_dict["gui_expression_substitutions"], 0)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["s_visibility_values"], 'definition',"data { Default, 'Never Show', 'Always Show' }")
    gii_dict["sp_pr_adaptNamesForPresentationInWebUI"]  = modeledit_aimmspy2.create(aimms_model, "pr_adaptNamesForPresentationInWebUI", 'Procedure', gii_dict["sp_public_section"], 0)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["sp_runtimeLib"], 'property',"nosave")
    gii_dict["sp_private_section"]  = modeledit_aimmspy2.create(aimms_model, "Private_Section", 'Section', gii_dict["sp_runtimeLib"], 0)
    gii_dict["sp_lib_start_stop_section"]  = modeledit_aimmspy2.create(aimms_model, "lib_start_stop_section", 'Section', gii_dict["sp_private_section"], 0)
    gii_dict["sp_pr_lib_init"]  = modeledit_aimmspy2.create(aimms_model, "LibraryInitialization", 'Procedure', gii_dict["sp_lib_start_stop_section"], 0)
    gii_dict["sp_pr_post_lib_init"]  = modeledit_aimmspy2.create(aimms_model, "PostLibraryInitialization", 'Procedure', gii_dict["sp_lib_start_stop_section"], 0)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["sp_pr_post_lib_init"], 'body', "pr_adaptNamesForPresentationInWebUI();")
    gii_dict["sp_pr_pre_lib_stop"]  = modeledit_aimmspy2.create(aimms_model, "PreLibraryTermination", 'Procedure', gii_dict["sp_lib_start_stop_section"], 0)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["sp_pr_pre_lib_stop"], 'body', "return 1;")
    gii_dict["sp_pr_lib_stop"]  = modeledit_aimmspy2.create(aimms_model, "LibraryTermination", 'Procedure', gii_dict["sp_lib_start_stop_section"], 0)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["sp_pr_lib_stop"], 'body', "return 1;")
    modeledit_aimmspy2.doCompile(aimms_model, gii_dict["sp_runtimeLib"])
    
    # The .aimms file is an xml file that lists the components of the project, 
    # starting with the model, and then the libraries.
    # Note the system and repository libraries do not have a path (sub folder inside the project folder)
    # The next loop will visit each component (main model, or library) that has a path inside the project folder.
    for project_component_xml in  project_file_xml_tree_root:

        component_path_attr = project_component_xml.get("Path")
        if component_path_attr == None:
            component_path_attribute = ""
        else:
            component_path_attribute = str(component_path_attr)
        # Path attribute is empty for system libraries and for repository libraries.
        if component_path_attribute != "":


            component_project_xml_file_name = os.path.join(component_path_attribute, "Project.xml")
            component_project_xml_file_path = pathlib.Path(component_project_xml_file_name)
            if component_project_xml_file_path.exists():

                tools.optdel_webui(component_path_attribute)

                # Extract essential info from the Project.xml file for this component.
                component_project_xml_tree = ET.parse(component_project_xml_file_name)
                component_project_xml_root = component_project_xml_tree.getroot()
                component_prefix = ''
                component_display_name = ''
                component_display_slug = ''
                for component_project_xml_child in component_project_xml_root:
                    if component_project_xml_child.tag == "Prefix":
                        component_prefix = str(component_project_xml_child.text)
                    if component_project_xml_child.tag == "DisplayName":
                        component_display_name =str(component_project_xml_child.text)

                if component_prefix == "" or component_display_name == "": 
                    component_display_slug = ""
                else:
                    component_display_slug = aimms_slug(component_prefix) + "::" + aimms_slug(component_display_name)
            
                sp_runtimeSection= ''

                # Construct the dictionary that contains the distinctive information per component.
                component_dict = {
                    "Path"        : component_path_attribute,   # Path to the component, relative to the project folder.
                    "Prefix"      : component_prefix,           # Prefix used by the component, empty for the main model.
                    "DisplayName" : component_display_name,     # Display name of the component.
                    "DisplaySlug" : component_display_slug      # Slug for the component.
                }

                # Initialize the WebUI object, loading existing webui.json if it exists.
                webui_filename = os.path.join( component_path_attribute, 'WebUI', 'webui.json')
                webui = web_page.WebUI(webui_filename, component_dict)
                webui_dict = webui.get_data()

                if component_prefix == '':
                    experimental_features_text_lines = [
                        "# WebUI Labs is a testing ground for experimental features that are not ready for production.",
                        "compact-scalar 1",
                        "ignore-inline-asr 0",
                        "highlight-annotations 0",
                        "webui-state-support 0",
                        "ignore-grid-layout 0",
                        "workflow_panel_v2 1",
                        "table-v2 1",
                        "ignore-font-update 0",
                        "new-global-limited-option-editor 0",
                        "supports-pages-in-library 1",
                        "" ]
                    experimental_features_text = "\n".join(experimental_features_text_lines)

                    experimental_features_filename = os.path.join( component_path_attribute, 'WebUI', 'experimental-features.conf')
                    with open(experimental_features_filename,"w") as experimental_features_file:
                        experimental_features_file.write(experimental_features_text)

                # Process each page according to the <comp>/PageManager.xml file.
                comp_done = win_pagemanager.process_page_manager_file(webui, aimms_model, gii_dict, component_dict)

                # Writing the output to the webui.json file.
                if comp_done:
                    webui_folder_name = os.path.join( component_path_attribute, 'WebUI' )
                    webui_folder_path = pathlib.Path(webui_folder_name)
                    if not webui_folder_path.exists():
                       webui_folder_path.mkdir()
                    webui_filename = os.path.join( component_path_attribute, 'WebUI', 'webui.json')
                    webui_dict = webui.get_data()
                    webui_pretty = json.dumps(webui_dict,indent=2)
                    webui_path = pathlib.Path(webui_filename)
                    with webui_path.open("w") as webui_file:
                        webui_file.write(webui_pretty)
                    print(f"Wrote WebUI file to {webui_filename}")

    identifier_element_text.generate_pr_adaptNamesForPresentationInWebUI(aimms_model, gii_dict)

    modeledit_aimmspy2.exportNode(aimms_model, gii_dict["sp_runtimeLib"], os.path.join("GeneratedInterfaceIdentifiersLibrary","GeneratedInterfaceIdentifiers.ams"))
    manipulate_main_model.ensureExistingLibrary(project_file, "GeneratedInterfaceIdentifiersLibrary" )
    manipulate_main_model.removeLibrary(project_file, "ModelEditAimmsPython")

    shutil.rmtree('ModelEditAimmsPython')

    win_object.report_ignored_lines_rectangles()

    # Restore the original working directory.
    os.chdir(cwd)   
