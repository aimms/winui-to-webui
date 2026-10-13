# This module is about replacing GUI expressions with defined parameters
# in each component's own GeneratedInterfaceIdentifiers module

from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import win_object_tools
import ams_file_editor as afe
import gii_module

def potentially_substitute_expression(aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, purpose: str, arg_expression:str, stable_id:str, item_index:int) -> str:
    """
    Replace WinUI inline expressions with generated AIMMS identifiers when required by WebUI.

    The function handles literal strings and expressions starting with `ELEMENT`, `STRING`, or `VALUE` by generating
    corresponding identifiers in the runtime library, compiling them, and returning a reference to the new identifier.

    :param aimms_model: AIMMS model handle used to create replacement identifiers.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary used for context during identifier creation.
    :type webui_page_dict: dict
    :param purpose: Short description of how the expression is used (for naming/logging).
    :type purpose: str
    :param arg_expression: AIMMS expression to potentially substitute.
    :type arg_expression: str
    :param stable_id: Stable identity of the widget the expression belongs to (see win_object_tools.compute_stable_id);
        already carries page context (page slug, or a pivot table's own ObjectUUID).
    :type stable_id: str
    :param item_index: Disambiguates multiple substitutions for the same widget/purpose (0 when not applicable).
    :type item_index: int
    :return: Original expression or the reference to the generated identifier replacing it.
    :rtype: str
    """
    identifier_reference = arg_expression
    expression = arg_expression
    if len(expression) > 2 and expression[0]=='"' and expression[-1]=='"':
        # Literal string, substitute.
        literal_text = expression[1:-1]
        candidate_name = f"sp_{purpose}_{stable_id}_{item_index}"
        if component_dict['Prefix'] != "":
            candidate_name = f"{component_dict['Prefix']}_{candidate_name}"
        lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""
        # Reuse an equivalent parameter already created this run (same literal text - see
        # gii_module.dedup_parameter) instead of minting a redundant new one. Filed into the
        # introducing page's own Section (see gii_module.ensure_page_section) - stable_id already
        # carries page context (see win_object_tools.compute_stable_id/page_slug_from_stable_id).
        expr_subst = gii_module.ensure_page_section(gii_dict, component_dict, win_object_tools.page_slug_from_stable_id(stable_id))
        usage = f"Used for {purpose} on {stable_id}"
        new_name, is_new, comment_command = gii_module.dedup_parameter(gii_dict, component_dict, "string parameter", "", None,
                                                                         f'"{literal_text}"', candidate_name, usage)
        identifier_reference = f'{lib_prefix}{gii_module.get_prefix(component_dict)}::{new_name}'
        if is_new:
            # Queue creation of the new (string) parameter - applied to the .ams file once AIMMS is done (see ams_file_editor.py).
            gii_dict["_edit_queue"].append(afe.AddIdentifier(name=new_name, type="string parameter", parent=expr_subst, file_hint=component_dict["AmsPath"]))
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=identifier_reference, attribute="Definition", value=f'"{literal_text}"'))
        gii_dict["_edit_queue"].append(comment_command)
    else:
        expression = expression.strip()
        for keyword in win_object_tools.EXPRESSION_KEYWORDS:
            if expression.startswith(keyword):
                # Found a matching keyword, perform substitution.
                rest_expression = expression[len(keyword):].strip()
                # Check for index domain in parentheses.
                index_domain = ""
                set_name = ""
                if rest_expression.startswith('('):
                    closing_paren_index = rest_expression.find(')')
                    if closing_paren_index != -1:
                        index_domain = rest_expression[0:closing_paren_index+1].strip()
                        rest_expression = rest_expression[closing_paren_index + 1:].strip()
                        # remove reverse index / element focus spec in UI index domain expressions.
                        to_ref_pos = index_domain.find('->')
                        while to_ref_pos >= 0:
                            komma_pos = index_domain[to_ref_pos:].find(',')
                            bracket_pos = index_domain[to_ref_pos:].find(']')
                            if bracket_pos == -1:
                                bracket_pos = index_domain[to_ref_pos:].find(')')
                            if komma_pos >=0 and komma_pos < bracket_pos:
                                end_reverse_pos = komma_pos + to_ref_pos
                            else:
                                end_reverse_pos = bracket_pos + to_ref_pos
                            index_domain = index_domain[:to_ref_pos] + index_domain[end_reverse_pos:]
                            to_ref_pos = index_domain.find('->')

                # For ELEMENT, check for '->' and set name.
                if keyword == 'ELEMENT':
                    if rest_expression.startswith('->'):
                        rest_expression = rest_expression[2:].strip()
                        # Extract set name.
                        set_name_end_index = rest_expression.find(':=')
                        if set_name_end_index != -1:
                            set_name = rest_expression[:set_name_end_index].strip()
                            rest_expression = rest_expression[set_name_end_index:].strip()
                # Now rest_expression should start with ':='
                if rest_expression.startswith(':='):
                    expr_body = rest_expression[2:].strip()
                    expr_body = win_object_tools.namespace_qualification(aimms_model, expr_body, component_dict['Prefix'])
                    id_type = "parameter"
                    # Construct a named identifier based on the keyword and set name.
                    if keyword == 'ELEMENT' and set_name:
                        start_name = "ep"
                        id_type = "element parameter"
                    elif keyword == 'STRING':
                        start_name = "sp"
                        id_type = "string parameter"
                    elif keyword == 'VALUE':
                        start_name = "p"
                        id_type = "parameter"
                    else:
                        start_name = "untyped_"
                        id_type = "parameter"
                    candidate_name = f"{start_name}_{purpose}_{stable_id}_{item_index}"
                    if component_dict['Prefix'] != "":
                        candidate_name = f"{component_dict['Prefix']}_{candidate_name}"

                    lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""
                    gii_prefix = gii_module.get_prefix(component_dict)

                    # Reuse an equivalent parameter already created this run (same type/range/
                    # index domain/definition - see gii_module.dedup_parameter) instead of
                    # minting a redundant new one. Filed into the introducing page's own Section
                    # (see gii_module.ensure_page_section) - stable_id already carries page
                    # context (see win_object_tools.compute_stable_id/page_slug_from_stable_id).
                    expr_subst = gii_module.ensure_page_section(gii_dict, component_dict, win_object_tools.page_slug_from_stable_id(stable_id))
                    usage = f"Used for {purpose} on {stable_id}"
                    new_name, is_new, comment_command = gii_module.dedup_parameter(gii_dict, component_dict, id_type, index_domain,
                                                                                     set_name if set_name != "" else None,
                                                                                     expr_body, candidate_name, usage)

                    # The expression to be returned is the new name, with the index domain appended if present.
                    # Return the substituted expression. index_domain (captured above, line ~72)
                    # already includes its own enclosing parens ("(ConfigFrom, ConfigTo)") - reusing
                    # it here without adding a second pair avoids "name(( ... ))", which downstream
                    # naive comma-splitting (tools.parse_aimms_string) mis-parses into args with
                    # stray leading/trailing parens on the first/last entry.
                    if index_domain != "":
                        identifier_reference = f"{lib_prefix}{gii_prefix}::{new_name}{index_domain}"
                    else:
                        identifier_reference = f"{lib_prefix}{gii_prefix}::{new_name}"

                    if is_new:
                        # The real work is queuing creation of the new parameter - applied to the
                        # .ams file once AIMMS is done (see ams_file_editor.py).
                        # print(f"substituting expression, new_name=\"{new_name}\"")
                        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=new_name, type=id_type, parent=expr_subst, file_hint=component_dict["AmsPath"]))
                        name_ref = f"{gii_prefix}::{new_name}"
                        if index_domain != "":
                            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=name_ref, attribute="IndexDomain", value=index_domain))
                        if set_name == "AllColors":
                            # WebUI can't use AIMMS's built-in AllColors system set as-is - defer to
                            # the same project-wide repointing as an existing AllColors-ranged
                            # identifier (see win_object_tools.investigate_contents and
                            # winui_to_webui.py's post-walk pass): register this new identifier so
                            # its Range is set to giim::s_AllColors once that set is known to exist.
                            gii_dict.setdefault("_all_colors_identifiers", {})[name_ref] = component_dict["AmsPath"]
                        elif set_name != "":
                            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=name_ref, attribute="Range", value=set_name))
                        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=name_ref, attribute="Definition", value=expr_body))
                        # print(f"name_ref={name_ref}, set_name={set_name}, index_domain={index_domain}, expr_body={expr_body}")
                    gii_dict["_edit_queue"].append(comment_command)
                    break

    return identifier_reference

def make_webui_reference(aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, purpose: str, winui_scalar_reference:str, index_domain:str, value_type:str, set_range:str, stable_id:str, item_index:int) -> str:
    """
    A WinUI reference can be of the form x( ep ), whereby ep is an element parameter and x an indexed parameter.
    The returned identifier reference is always a bare name (never carries index arguments): pass index_domain=""
    for callers (text, image, iframe widgets) that need a plain scalar, or a non-empty index_domain to instead
    create an indexed identifier - e.g. one meant to be read per-row through a 'webui::flagsIdentifier' annotation.

    :param aimms_model: AIMMS model handle used to create replacement identifiers.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary used for context during identifier creation.
    :type webui_page_dict: dict
    :param purpose: Short description of how the expression is used (for naming/logging).
    :type purpose: str
    :param arg_expression: AIMMS expression to potentially substitute.
    :type arg_expression: str
    :param value_type: One of: numeric, string, or element
    :type value_type: str
    :param set_range: if value_type == element, then the fully qualified set name.
    :type set_range: str
    :param stable_id: Stable identity of the widget the reference belongs to (see win_object_tools.compute_stable_id);
        already carries page context (page slug, or a pivot table's own ObjectUUID).
    :type stable_id: str
    :param item_index: Disambiguates multiple substitutions for the same widget/purpose (0 when not applicable).
    :type item_index: int
    :return: Original expression or the reference to the generated identifier replacing it.
    :rtype: str
    """
    # print(f"make_webui_reference(...,{winui_scalar_reference})")
    if value_type == "string":
        identifier_type = "string parameter"
        candidate_name = f"sp_{purpose}_{stable_id}_{item_index}"
    elif value_type == "element":
        identifier_type = "element parameter"
        candidate_name = f"ep_{purpose}_{stable_id}_{item_index}"
    else:
        identifier_type = "parameter"
        candidate_name = f"p_{purpose}_{stable_id}_{item_index}"
    if component_dict['Prefix'] != "":
        candidate_name = f"{component_dict['Prefix']}_{candidate_name}"
    lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""

    # Reuse an equivalent parameter already created this run (same type/range/index domain/
    # definition - see gii_module.dedup_parameter) instead of minting a redundant new one. Filed
    # into the introducing page's own Section (see gii_module.ensure_page_section) - stable_id
    # already carries page context (see win_object_tools.compute_stable_id/page_slug_from_stable_id).
    expr_subst = gii_module.ensure_page_section(gii_dict, component_dict, win_object_tools.page_slug_from_stable_id(stable_id))
    usage = f"Used for {purpose} on {stable_id}"
    new_name, is_new, comment_command = gii_module.dedup_parameter(gii_dict, component_dict, identifier_type, index_domain,
                                                                     set_range if value_type == "element" else None,
                                                                     winui_scalar_reference, candidate_name, usage)
    identifier_reference = f'{lib_prefix}{gii_module.get_prefix(component_dict)}::{new_name}'
    if is_new:
        # Queue creation of the new scalar parameter - applied to the .ams file once AIMMS is done (see ams_file_editor.py).
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=new_name, type=identifier_type, parent=expr_subst, file_hint=component_dict["AmsPath"]))
        if index_domain != "":
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=identifier_reference, attribute="IndexDomain", value=index_domain))
        if value_type == "element":
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=identifier_reference, attribute="Range", value=set_range))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=identifier_reference, attribute="Definition", value=winui_scalar_reference))
    gii_dict["_edit_queue"].append(comment_command)

    return identifier_reference
