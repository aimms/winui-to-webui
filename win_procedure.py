# This module is about replacing action sequences by procedures
# in each component's own GeneratedInterfaceIdentifiers module

from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import lxml.etree as ET
import converter_logging
import aimms_slug
import win_object_tools
import ams_file_editor as afe
import gii_module

menu_command_ignores = 0

def work_action_sequence_into_procedure(aimms_model: Model,
        gii_dict: dict, component_dict:dict, webui_page_dict: dict,
        page_name: str, purpose: str, action_sequence :ET.Element, stable_id: str) -> dict:
    """
    Translate a WinUI action sequence into an AIMMS procedure (existing or generated) suitable for WebUI actions.

    :param aimms_model: AIMMS model handle used to create or reference procedures.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary used for context during logging.
    :type webui_page_dict: dict
    :param page_name: Name of the page containing the action sequence.
    :type page_name: str
    :param purpose: Short description of how the action sequence is used (for naming/logging).
    :type purpose: str
    :param action_sequence: WinUI XML element describing the action sequence to convert.
    :type action_sequence: ET.Element
    :param stable_id: Stable identity of the button the action sequence belongs to (see win_object_tools.compute_stable_id).
    :type stable_id: str
    :return: Dictionary with keys `name` (procedure identifier or string parameter) and `IsLiteral` (1 if literal procedure name, 0 if identifier reference).
    :rtype: dict
    """

    global menu_command_ignores

    return_dict = {
        'name' : '', # to be determined
        'IsLiteral' : 1  # For WinUI actions, the procedure name is always literal.
    }

    # First investigate if this action sequence can be replaced by an AIMMS procedure call.
    noActions = 0
    noProcCalls = 0
    procCall = ''
    noOtherTypeActions = 0
    for some_action in action_sequence:
        if str(some_action.tag) == 'Action':
            noActions += 1
            if some_action.attrib.get('Type','') == 'Run':
                for sub_action in some_action:
                    if sub_action.tag == 'RunWhat':
                        if str(sub_action.text) != 'SpecificProcecure':
                            noOtherTypeActions += 1
                    if sub_action.tag == 'Procedure':
                        noProcCalls += 1
                        procCall = str(sub_action.text)
            else:
                noOtherTypeActions += 1
        else:
            converter_logging.exoticW([f"unkown entry type {str(some_action.tag)} in action sequence"],
                    component_dict, purpose, page_name)

    if ( noActions == 1 ) and ( noProcCalls == 1 ) and ( noOtherTypeActions == 0 ):
        return_dict = { 
            'name' : procCall,  
            'IsLiteral' : 1 # For WinUI actions, the procedure name is always literal.
        }
    elif ( noActions == 0 ):
        return_dict = { 
            'name' : '',  
            'IsLiteral' : 1 # For WinUI actions, the procedure name is always literal.
        }
    else:
        # Create substittue proc.
        sp_lines: list[str] = []
        closePageActions = 0
        openingPageActions = 0
        for some_action in action_sequence:
            if some_action.tag == 'Action':
                action_type_name = str(some_action.attrib.get('Type',''))
                if   action_type_name == 'Run':
                    # the RunWhat subelement can be a SpecificProcecure or PageProcedure
                    # the procedure ran can have arguments (not for WebUI)
                    procedure_run_enabled = 1
                    for sub_action in some_action:
                        if sub_action.tag == 'RunWhat' and str(sub_action.text) != 'SpecificProcecure':
                            converter_logging.exoticW([f"unkown entry type {str(some_action.tag)} in action sequence"],
                                component_dict, purpose, page_name)
                            procedure_run_enabled = 0
                        if ( sub_action.tag == 'Procedure' ) and ( procedure_run_enabled == 1 ):
                            procName = str(sub_action.text);
                            if procName.find("(") == -1:
                                procName = procName + "()"
                            sp_lines.append(f"     {procName} ;\n")
                elif action_type_name == 'Assignment':
                    idName = ''
                    valStr = ''
                    for sub_action in some_action:
                        if str(sub_action.tag) == 'Identifier':
                            idName = str(sub_action.text)
                        elif str(sub_action.tag) == 'AssignedValue':
                            valStr = str(sub_action.text)
                            if valStr.find('VALUE :=') >= 0:
                                valStr = valStr[8:]
                        else:
                            converter_logging.exoticW([f"Invalid assignment in Action Sequence {str(sub_action.tag)} in action sequence"],
                                component_dict, purpose, page_name)
                    idName = win_object_tools.namespace_qualification(aimms_model, idName, component_dict['Prefix'])
                    valStr = win_object_tools.namespace_qualification(aimms_model, valStr, component_dict['Prefix'])
                    sp_lines.append(f"    {idName} := {valStr} ;\n")
                elif action_type_name == 'LinkedPage':
                    for sub_action in some_action:
                        if str(sub_action.tag) == 'Page':
                            pageName = sub_action.get('Name')
                            pageSlug = aimms_slug.aimms_slug(pageName)

                            sp_lines.append(f"    webui::OpenPage('{pageSlug}');\n")
                        else:
                            converter_logging.exoticW([f"Invalid sub action in LinkedPage action {str(sub_action.tag)} in action sequence"],
                                component_dict, purpose, page_name)
                elif action_type_name == 'ClosePage':
                    sp_lines.append(f"    ! closing page is implied.\n")
                elif action_type_name == 'MenuCommand':
                    for sub_action in some_action:
                        converter_logging.exoticW([f"The MenuCommand {sub_action.tag} is not converted with text {str(sub_action.text)} as part of an action sequence.",
                            "see also https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Button/Actions/index.html"],
                            component_dict, purpose, page_name)
                        menu_command_ignores += 1 
                        # if sub_action.tag == 'Command':
                        #     converter_logging.exoticW([f"Not converted is the menu action {str(sub_action.text)} as part of an action sequence.",
                        #         "see also https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Button/Actions/index.html"],
                        #         component_dict, purpose, page_name)
                        # else:
                        #     converter_logging.exoticW([f"Not converted is the menu action {str(sub_action.text)} as part of an action sequence.",
                        #         "see also https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Button/Actions/index.html"],
                        #         component_dict, purpose, page_name)
                elif  action_type_name in {
                            'DataPageSpecific',
                            'UpdateAllIdentifiers',
                            'SystemClose',
                            'AssertionCheck',
                            'PopupMenu',
                            'GotoNavigationPage',
                        }:
                    menu_command_ignores += 1 
                else:
                    converter_logging.exoticW([f"The action {action_type_name} in action sequence is not yet converted to a corresponding action for WebUI",
                        "see also https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Button/Actions/index.html"],
                        component_dict, purpose, page_name)


        # Create the substituting procedure - reusing an equivalent one already created this
        # run (same Body text - see gii_module.dedup_procedure) instead of minting a redundant
        # new one (e.g. many "close the page" buttons across many pages end up with an
        # identical generated body).
        gii_body_text = "".join(sp_lines)
        candidate_proc_name = f"pr_action_sequence_{purpose}_{stable_id}"
        lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""
        # Filed into the introducing page's own Section (see gii_module.ensure_page_section) -
        # stable_id already carries page context (see win_object_tools.compute_stable_id/
        # page_slug_from_stable_id).
        page_section = gii_module.ensure_page_section(gii_dict, component_dict, win_object_tools.page_slug_from_stable_id(stable_id))
        usage = f"Used by button action sequence {purpose} on page {page_name} ({stable_id})"
        gii_proc_name, is_new, comment_command = gii_module.dedup_procedure(gii_dict, component_dict, gii_body_text, candidate_proc_name, usage)
        procCall = f"{lib_prefix}{gii_module.get_prefix(component_dict)}::{gii_proc_name}"
        #print(f"gii_proc_name={gii_proc_name}, procCall={procCall}")
        if is_new:
            # Queue creation of the substituting procedure - applied to the .ams file once AIMMS is done (see ams_file_editor.py).
            gii_dict["_edit_queue"].append(afe.AddIdentifier(name=gii_proc_name, type="procedure", parent=page_section, file_hint=component_dict["AmsPath"]))
            gii_dict["_edit_queue"].append(afe.AppendToBody(identifier=procCall, attribute="Body", statement=gii_body_text))
        gii_dict["_edit_queue"].append(comment_command)
        # print(f"gii_proc_name={gii_proc_name}, gii_body_text={gii_body_text}")

        if openingPageActions > 1:
            converter_logging.exoticW(["More than one page open not supported by WebUI"],
                component_dict, purpose, page_name)

        if openingPageActions != closePageActions:
            converter_logging.exoticW(["Ignoring that number of opening page actions are not equeal to number of closing page actions"],
                component_dict, purpose, page_name)

        return_dict = {
            'name' : procCall,  
            'IsLiteral' : 1 # For WinUI actions, the procedure name is always literal.
        }

    return return_dict
