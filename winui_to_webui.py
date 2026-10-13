from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
import copy
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
from aimms_slug import aimms_slug
import tools
import identifier_element_text
import manipulate_main_model
import converter_logging
import win_object
import win_pivot_state
import win_color
import win_color_scan
import gii_module
import ams_file_editor as afe

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modeledit_aimmspy import Model

def process_aimms_app(project_folder:str, project_name:str, page_name: str = None, new_color_set: bool = False, colors: bool = False, network: str = "auto", diagram_spread: float = 2.5, share_layouts: bool = False) -> None:
    """
    Convert all WinUI pages of an AIMMS project into WebUI format for the specified project folder and name.

    :param project_folder: Folder path where the AIMMS project resides.
    :type project_folder: str
    :param project_name: Name of the AIMMS project (without extension).
    :type project_name: str
    :param page_name: When given, restricts conversion to the single WinUI page with this
        PageManager.xml "Name" attribute; every other page already present in an existing
        WebUI/webui.json is left untouched. Components (main model or a library) that don't
        already have a webui.json but do have a non-empty Pages folder still get a fresh base
        webui.json created (no pages converted into it) so the overall WebUI stays coherent.
        When None (default), the whole project is converted and any existing webui.json is
        rebuilt from scratch, as before.
    :type page_name: str | None
    :param new_color_set: When True, every ElementParameter anywhere in the project whose Range
        is (case-insensitively) AIMMS's built-in AllColors system set is repointed to the main
        model's own giim::s_AllColors instead - not just the ones a converted widget actually
        references (see ams_file_editor.AmsProject.find_all_colors_element_parameters). Off by
        default since it touches identifiers outside anything the current conversion run itself
        needs.
    :type new_color_set: bool
    :param colors: When True (--colors), convert WinUI data coloring (Colors/Background_Color,
        chart Color) into webui::AnnotationsIdentifier + w2w-color.css, and create the
        giim::s_AllColors color registry. Off by default: the generated CSS still colors widgets
        that don't use coloring, so it stays opt-in until the CSS is understood.
    :type colors: bool
    :param network: How a WinUI Network Object is converted (--network): "map" (WebUI Map widget),
        "diagram" (WebUI Diagram widget), or "auto" - per object, map for a GIS background or
        longitude/latitude coordinate names, else diagram (see win_network.choose_widget) - or
        "ignore" (no widget, no grid space).
    :type network: str
    :param diagram_spread: Factor by which a converted diagram's drawing space exceeds the WinUI
        object's own pixel size (--diagram-spread), with the initial zoom set to its inverse:
        WebUI draws each node as a labelled box, much larger than WinUI's dot, so nodes need
        more room between them.
    :type diagram_spread: float
    :param share_layouts: When True (--share-layouts), pages with the same custom grid shape share
        one custom layout. Off by default: every page gets its own custom layout, so editing one
        page's layout never changes another page. A WebUI standard layout is used either way.
    :type share_layouts: bool
    :return: None. Generates WebUI output, supporting runtime libraries, and writes conversion logs.
    :rtype: None
    """

    # Ensure the project folder exists
    project_folder_path = pathlib.Path(project_folder)
    if not project_folder_path.exists():
        raise FileNotFoundError(f"Project folder'{project_folder}' does not exist.")

    print(f"Processing AIMMS project '{project_name}' in folder '{project_folder}'")

    # Copy the ModelEditAimmsPython library into the project at hand (used for live, read-side
    # queries during phase 1 - GeneratedInterfaceIdentifiers modules are written directly into
    # each component's own .ams file in phase 2, so no separate library needs copying in for that).
    shutil.copytree('ModelEditAimmsPython',  os.path.join(project_folder, 'ModelEditAimmsPython'), dirs_exist_ok=True)

    # Read the w2w-color.css template now, while the cwd is still the tool's own directory
    # (where the bundled template lives) - expanding it against the merged color registry, and
    # writing it into the main model's own WebUI/resources/css/ folder, happens later, once that
    # registry is known (see win_color.expand_css/write_color_css, called after the per-component
    # loop below).
    color_css_template = win_color.read_template()

    # what is the current working directory?
    cwd = os.getcwd()

    # Change working directory to the project folder.
    os.chdir(project_folder)

    # tools.optdel("MainProject\\WebUI\\webui.json")
    # tools.optdel("sampleLib\\WebUI\\webui.json")

    project_file = f"{project_name}.aimms"
    print(f"folder {project_folder}, name {project_name}, file {project_file}")
    if not os.path.exists(project_file):
        raise FileNotFoundError(f"Project file '{project_file}' not found.")
    
    # Open conversion log
    converter_logging.open_log(project_name)

    manipulate_main_model.ensureSystemLibrary(project_file,"AimmsPro" )
    webui_dict = {
        "UUID"    : "69378F70-E906-486F-8F2C-1D606AEB9669",
        "Name"    : "WebUI",
        "Version" : "26.12.5.5"
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


    # gii_dict no longer points at a live, pre-built central library - each component gets its own
    # nested GeneratedInterfaceIdentifiers module, created lazily on first need (see gii_module.py;
    # gii_module.get_prefix(component_dict) gives the "giim"/"giil" prefix for a given component -
    # there's no single project-wide prefix anymore) and applied to the .ams files as text once
    # this whole per-component loop is done (phase 2, see ams_file_editor.py) - some of these
    # edits aren't safe to make on the live session.
    gii_dict = {
        "_edit_queue": [],
        "_color_css_template": color_css_template,
        "_colors": colors,
        "_network": network,
        "_diagram_spread": diagram_spread,
    }
    main_model_component_dict = None

    # Pre-pass: discover every component's own Prefix/AmsPath UPFRONT, before any page is
    # converted below, so a page in one component that references an identifier declared in
    # ANOTHER component not yet reached by the main loop - e.g. the main model's own page
    # forward-referencing a library identifier, since the main model is always processed first -
    # can still resolve which component that identifier actually belongs to (see
    # win_object_tools.resolve_identifier_owner_component). Builds the very same component_dict
    # object the main loop below goes on to reuse (looked up there, never reconstructed) so any
    # "_gii_module_ready"-style flag later set on it stays consistent for the rest of the run -
    # two different dict objects for the same component would each think a module/section/etc.
    # still needs creating, queuing duplicate AddIdentifier commands for it.
    for project_component_xml in project_file_xml_tree_root:
        component_path_attr = project_component_xml.get("Path")
        component_path_attribute = str(component_path_attr) if component_path_attr is not None else ""
        if component_path_attribute == "":
            continue
        component_project_xml_file_name = os.path.join(component_path_attribute, "Project.xml")
        component_project_xml_file_path = pathlib.Path(component_project_xml_file_name)
        if not component_project_xml_file_path.exists():
            continue
        component_project_xml_tree = ET.parse(component_project_xml_file_name)
        component_project_xml_root = component_project_xml_tree.getroot()
        component_prefix = ''
        component_display_name = ''
        component_model_file_name = ''
        for component_project_xml_child in component_project_xml_root:
            if component_project_xml_child.tag == "Prefix":
                component_prefix = str(component_project_xml_child.text)
            if component_project_xml_child.tag == "DisplayName":
                component_display_name = str(component_project_xml_child.text)
            if component_project_xml_child.tag == "ModelFileName":
                component_model_file_name = str(component_project_xml_child.text)
        component_display_slug = "" if (component_prefix == "" or component_display_name == "") else \
            aimms_slug(component_prefix) + "::" + aimms_slug(component_display_name)
        gii_dict.setdefault("_component_dict_by_prefix", {})[component_prefix] = {
            "Path"        : component_path_attribute,
            "Prefix"      : component_prefix,
            "DisplayName" : component_display_name,
            "DisplaySlug" : component_display_slug,
            "AmsPath"     : os.path.join(component_path_attribute, component_model_file_name),
        }

    # The .aimms file is an xml file that lists the components of the project,
    # starting with the model, and then the libraries.
    # Note the system and repository libraries do not have a path (sub folder inside the project folder)
    # The next loop will visit each component (main model, or library) that has a path inside the project folder.
    page_found_anywhere = False
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

                if page_name is None:
                    # Full conversion: any existing webui.json is rebuilt from scratch.
                    tools.optdel_webui(component_path_attribute)
                # In single-page mode, keep the existing webui.json so it can be loaded below
                # and only the requested page's contribution to it gets replaced.

                # This component's own Prefix (the rest of Project.xml - DisplayName, ModelFileName -
                # was already extracted by the pre-pass above, which built and registered this
                # component's own component_dict, looked up below).
                component_project_xml_tree = ET.parse(component_project_xml_file_name)
                component_project_xml_root = component_project_xml_tree.getroot()
                component_prefix = ''
                for component_project_xml_child in component_project_xml_root:
                    if component_project_xml_child.tag == "Prefix":
                        component_prefix = str(component_project_xml_child.text)

                sp_runtimeSection= ''

                # The pre-pass above already built this component's own component_dict (and
                # registered it in gii_dict["_component_dict_by_prefix"]) - reuse that same
                # object rather than constructing a new one here, so any "_gii_module_ready"-style
                # flag a cross-component reference may already have set on it (see
                # win_object_tools.resolve_identifier_owner_component) stays in effect.
                component_dict = gii_dict["_component_dict_by_prefix"][component_prefix]

                if component_prefix == '':
                    main_model_component_dict = component_dict
                    # The main model is always the first component in the .aimms project's own
                    # listing (see the comment above this loop) - so this is already set by the
                    # time any library's Picture-widget conversion might need it, to create
                    # giim::fcn_filenameFromPath from wherever it's needed (see
                    # gii_module.ensure_image_reference_parameter/ensure_filename_from_path_function).
                    gii_dict["_main_model_component_dict"] = component_dict

                # Resolve every Pivot Table's real row/column/outer index arrangement from
                # .DeveloperState in one pass (see win_pivot_state.py) - this arrangement is set
                # interactively in the WinUI IDE and is never written to the WinUI XML itself.
                pivot_table_uuids = win_pivot_state.collect_pivot_table_uuids(component_dict)
                component_dict["PivotState"] = win_pivot_state.scan_pivot_tables(component_dict, pivot_table_uuids)

                # Collect this component's own widget-styling colors (any *Color* element in its
                # Pages/*.xml) and every color declared in its own Settings/UserColors.xml, so
                # they can be merged project-wide into gii_module.ensure_all_colors_values()'s
                # giim::s_AllColors/p_Red/p_Green/p_Blue below, once the whole per-component loop is
                # done and it's clear whether anything color-related was found at all.
                if colors:
                    discovered_user_colors = gii_dict.setdefault("_discovered_user_colors", {})
                    for color_name, rgb in win_color_scan.scan_user_colors(component_path_attribute).items():
                        discovered_user_colors.setdefault(color_name, rgb)
                    discovered_literal_colors = gii_dict.setdefault("_discovered_literal_colors", {})
                    for color_name, rgb in win_color_scan.scan_page_colors(component_path_attribute).items():
                        discovered_literal_colors.setdefault(color_name, rgb)

                # Initialize the WebUI object, loading existing webui.json if it exists.
                webui_filename = os.path.join( component_path_attribute, 'WebUI', 'webui.json')
                webui_already_existed = os.path.exists(webui_filename)
                webui = web_page.WebUI(webui_filename, component_dict)
                webui.share_layouts = share_layouts
                webui_dict = webui.get_data()

                # In single-page mode, remember what was on disk (or the freshly-built default
                # skeleton, if nothing was on disk) before this run, so pages other than the
                # requested one can be restored untouched after the walk below.
                webui_snapshot = copy.deepcopy(webui_dict) if page_name is not None else None

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
                # This always walks every page in the component (even in single-page mode) because
                # this component's own GeneratedInterfaceIdentifiers module is rebuilt from scratch
                # every run and must stay complete for every page that remains referenced in
                # webui.json. That's safe now that
                # widget/identifier names are stable-identity-based (see win_object_tools.compute_stable_id):
                # regenerating a page's identifiers reproduces the same names, so it doesn't disturb
                # pages restrict_to_page() is about to leave untouched.
                comp_done = win_pagemanager.process_page_manager_file(webui, aimms_model, gii_dict, component_dict)

                if page_name is not None:
                    page_found_in_component = webui.restrict_to_page(webui_snapshot, page_name, component_dict)
                    page_found_anywhere = page_found_anywhere or page_found_in_component

                    if page_found_in_component:
                        write_this_component = True
                    elif not webui_already_existed:
                        # No webui.json existed for this component before this run. Still give it a
                        # fresh base (no pages converted into it) if it actually has pages to manage,
                        # so the overall WebUI stays coherent even though we're only converting one
                        # page elsewhere. restrict_to_page() already reset self.data to that base
                        # skeleton (the snapshot captured right after WebUI() built it).
                        pages_dir = pathlib.Path(component_path_attribute) / "Pages"
                        write_this_component = pages_dir.is_dir() and any(pages_dir.glob("*.xml"))
                    else:
                        # Already had a webui.json, and the requested page isn't here - leave it alone.
                        write_this_component = False

                    comp_done = comp_done and write_this_component

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

    # Phase 2's AmsProject (see below) is constructed here rather than at its usual, later spot
    # so that --newcolorset can use it to scan the .ams text for pre-existing identifiers before
    # the block below decides whether any AllColors-repointing work is needed at all - it's still
    # only applied/saved later, once every edit (from here and the per-component loop above) has
    # been queued.
    main_ams_path = main_model_component_dict["AmsPath"] if main_model_component_dict is not None else None
    # Every known component's own directory - not just the main model's - so a library reached
    # only via a ".." Library Path that steps outside the current directory entirely (a "family
    # of models" layout, e.g. "<main model dir>/../../ngas") still has its own .ams file(s) found;
    # see AmsProject's own docstring for why project_root alone isn't enough for that layout.
    component_dirs = [pathlib.Path(cd["Path"]) for cd in gii_dict.get("_component_dict_by_prefix", {}).values()]
    ams_project = afe.AmsProject(pathlib.Path("."), main_ams_path=main_ams_path, extra_roots=component_dirs)

    if main_model_component_dict is not None:
        # Some (older/customized) projects don't have the full standard App Framework
        # scaffolding - ensure the two lifecycle procedures generated content below depends on
        # actually exist before anything tries to append into them.
        identifier_element_text.ensure_lifecycle_procedures(gii_dict, aimms_model, main_model_component_dict)

        identifier_element_text.generate_pr_adaptNamesForPresentationInWebUI(gii_dict, main_model_component_dict)

        if new_color_set:
            # --newcolorset: repoint EVERY ElementParameter in the project whose Range is
            # (case-insensitively) AllColors, not just the ones a converted widget actually
            # referenced (see win_object_tools.investigate_contents/win_expression.py, which only
            # populate _all_colors_identifiers for identifiers a WinUI page actually used). Merging
            # into the same dict the widget walk already populates means the block below (which
            # creates giim::s_AllColors and does the actual repointing) needs no changes at all.
            for path, name in ams_project.find_all_colors_element_parameters():
                gii_dict.setdefault("_all_colors_identifiers", {})[name] = str(path)

        # Any identifier ranged over AIMMS's built-in AllColors system set that got used for
        # data coloring (see win_object_tools.investigate_contents) needs repointing to the main
        # model's own s_AllColors instead - collected during the walk above so it's created (and
        # each identifier's Range changed) only once, here. giim::s_AllColors is unambiguous from
        # anywhere in the project (main model or any library) since "giim" is never reused by a
        # library's own GeneratedInterfaceIdentifiers module - see gii_module.py.
        #
        # s_AllColors/p_Red/p_Green/p_Blue only get created at all if there's actually something
        # color-related in the project (data coloring, discovered widget-styling colors, or a
        # non-empty Settings/UserColors.xml anywhere) - once that's true, the set is always the
        # full merge: the 147 standard w3c/CSS names, plus every discovered project color,
        # priority w3c > Settings/UserColors > other (win_color_scan.py) on a name clash.
        if (gii_dict.get("_all_colors_identifiers") or gii_dict.get("_discovered_user_colors")
                or gii_dict.get("_discovered_literal_colors") or gii_dict.get("_color_literal_names")):
            merged_colors = {}
            merged_colors.update(gii_dict.get("_discovered_literal_colors", {}))
            merged_colors.update(gii_dict.get("_discovered_user_colors", {}))
            merged_colors.update(win_color.COLOR_RGB)
            gii_module.ensure_all_colors_values(gii_dict, main_model_component_dict, merged_colors)
            # Every literal color a table/chart's Colors/Color element itself referenced (see
            # win_object_tools.investigate_contents) needs its own ElementParameter, so it can be
            # used with formatString(...%e...) - a bare quoted element literal doesn't type-check.
            gii_module.ensure_color_literal_elements(gii_dict, main_model_component_dict)
            all_colors_ref = f"{gii_module.MAIN_PREFIX}::{gii_module.ALL_COLORS_SET_NAME}"
            for color_identifier_name, file_hint in sorted(gii_dict.get("_all_colors_identifiers", {}).items()):
                gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=color_identifier_name, attribute="Range", value=all_colors_ref, file_hint=file_hint))

            # w2w-color.css needs one rule block per giim::s_AllColors member, not just the 147
            # standard names the template is written in terms of - only written at all if some
            # widget actually used AIMMS data coloring (win_object_tools.py sets this flag), since
            # a UserColors.xml/page-styling-only project has nothing that references these classes.
            if gii_dict.get("_color_css_needed"):
                css_content = win_color.expand_css(gii_dict["_color_css_template"], merged_colors)
                win_color.write_color_css(main_model_component_dict, css_content)

        if not colors:
            # A w2w-color.css left behind by an earlier --colors run would keep coloring widgets.
            win_color.remove_color_css(main_model_component_dict)

    # Phase 2: AIMMS is done producing information for this run - apply the queued GII edits
    # directly to each component's own .ams file as text (see ams_file_editor.py). Some of these
    # edits (a new nested Module, a statement appended into a pre-existing procedure body) aren't
    # safe to make on the live, compiled session. (ams_project itself was already constructed
    # above, before the AllColors-repointing block, so --newcolorset could use it to scan.)
    ams_project.apply(gii_dict["_edit_queue"])
    # A page's own generated Section (see gii_module.ensure_page_section) can end up with nothing
    # in it - every widget on that page turned out not to need a single generated identifier, or
    # it only ever existed to hold a child page's own (now-pruned) Section - so sweep those away
    # before writing anything to disk. Scoped to PAGE_SECTION_NAME_PREFIX: only ever removes
    # Sections this tool itself generated, never a user's own pre-existing one.
    ams_project.prune_empty_sections(name_prefix=gii_module.PAGE_SECTION_NAME_PREFIX,
                                      within_module_names=(gii_module.MAIN_MODULE_NAME, gii_module.LIBRARY_MODULE_NAME))
    ams_project.save()

    manipulate_main_model.removeLibrary(project_file, "ModelEditAimmsPython")

    shutil.rmtree('ModelEditAimmsPython')

    win_object.report_ignored_lines_rectangles()

    # Restore the original working directory.
    os.chdir(cwd)

    if page_name is not None and not page_found_anywhere:
        raise ValueError(f"Page '{page_name}' not found in any component of the project.")
