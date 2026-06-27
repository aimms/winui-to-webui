# This module is about replacing action sequences by procedures
# in runtime library GeneratedInterfaceIdentifiersLibrary

from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import modeledit_aimmspy2
import lxml.etree as ET
import converter_logging
import aimms_slug
import win_object_tools

substitution_number = 0

def get_next_substitution_number() -> int:
    """
    Return the next substitution number and increment the global counter.
    
    :return: Incremented substitution counter.
    :rtype: int
    """
    global substitution_number
    substitution_number += 1
    return substitution_number

def work_action_sequence_into_procedure(aimms_model: Model, 
        gii_dict: dict, component_dict:dict, webui_page_dict: dict, 
        page_name: str, purpose: str, action_sequence :ET.Element) -> dict:
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
    :return: Dictionary with keys `name` (procedure identifier or string parameter) and `IsLiteral` (1 if literal procedure name, 0 if identifier reference).
    :rtype: dict
    """

    page_slug = aimms_slug.aimms_slug(page_name)
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
        proc_no = get_next_substitution_number()
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
                        if sub_action.tag == 'Command':
                            converter_logging.exoticW([f"The menu action {str(sub_action.text)} in an action sequence is not yet converted to a corresponding action for WebUI, or a conversion may not be available.",
                                "see also https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Button/Actions/index.html"],
                                component_dict, purpose, page_name)
                else:
                    converter_logging.exoticW([f"The action {action_type_name} in action sequence is not yet converted to a corresponding action for WebUI",
                        "see also https://documentation.aimms.com/user-guide/aimms-ide/Aimms/Page%20Manager/Page%20Objects/Button/Actions/index.html"],
                        component_dict, purpose, page_name)

                # elif action_type_name == 'ClosePage':
                # elif action_type_name == 'MenuCommand':
                # elif action_type_name == 'DataPageSpecific':
                # elif action_type_name == 'UpdateAllIdentifiers':
                # elif action_type_name == 'SystemClose':
                # elif action_type_name == 'AssertionCheck':
                # elif action_type_name == 'PopupMenu':
                # elif action_type_name == 'GotoNavigationPage':

        # Create the substituting procedure.
        gii_body_text = "".join(sp_lines)
        gii_proc_name = f"pr_action_sequence_{page_slug}_{purpose}_{proc_no}"
        procCall = "gii::" + gii_proc_name
        #print(f"gii_proc_name={gii_proc_name}, procCall={procCall}")
        modeledit_aimmspy2.create(aimms_model, gii_proc_name, 'procedure', gii_dict["sp_public_section"], 0)
        modeledit_aimmspy2.setAttributeText(aimms_model, procCall, 'body', gii_body_text)
        # print(f"gii_proc_name={gii_proc_name}, gii_body_text={gii_body_text}")
        modeledit_aimmspy2.doCompile(aimms_model, procCall)

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
