# This module is about replacing GUI expressions with defined parameters 
# in runtime library GeneratedInterfaceIdentifiersLibrary

from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import modeledit_aimmspy2
import aimms_slug
import win_object_tools

substitution_number = 0

def get_next_substitution_number() -> int:
    """
    Return the next substitution number and increment the global counter.
    
    :return: Incremented substitution counter for generated identifiers.
    :rtype: int
    """
    global substitution_number
    substitution_number += 1
    return substitution_number


def potentially_substitute_expression(aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, purpose: str, arg_expression:str) -> str:
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
    :param page_name: Name of the page containing the expression.
    :type page_name: str
    :param purpose: Short description of how the expression is used (for naming/logging).
    :type purpose: str
    :param arg_expression: AIMMS expression to potentially substitute.
    :type arg_expression: str
    :return: Original expression or the reference to the generated identifier replacing it.
    :rtype: str
    """
    identifier_reference = arg_expression
    expression = arg_expression
    if len(expression) > 2 and expression[0]=='"' and expression[-1]=='"':
        # Literal string, substitute.
        literal_text = expression[1:-1]
        sub_number = get_next_substitution_number()
        page_slug = aimms_slug.aimms_slug(page_name)
        new_name = f"sp_{page_slug}_{purpose}_{sub_number}"
        if component_dict['Prefix'] != "":
            new_name = f"{component_dict['Prefix']}_{new_name}"     
        identifier_reference = f'{gii_dict["Prefix"]}::{new_name}'
        # Create the new (string) parameter in the AIMMS model.   
        modeledit_aimmspy2.create(aimms_model, new_name, "string parameter", gii_dict["gui_expression_substitutions"], 0)
        modeledit_aimmspy2.setAttributeText(aimms_model, identifier_reference, "definition", f'"{literal_text}"' )
        modeledit_aimmspy2.doCompile(aimms_model, identifier_reference)
    else:
        keywords = ['ELEMENT', 'STRING', 'VALUE']
        expression = expression.strip() 
        for keyword in keywords:
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
                    sub_number = get_next_substitution_number()
                    page_slug = aimms_slug.aimms_slug(page_name)
                    new_name = f"{start_name}_{page_slug}_{purpose}_{sub_number}"
                    if component_dict['Prefix'] != "":
                        new_name = f"{component_dict['Prefix']}_{new_name}"
                    
                    # The expression to be returned is the new name, with the index domain appended if present.
                    # Return the substituted expression.
                    if index_domain != "":
                        identifier_reference = f"{gii_dict["Prefix"]}::{new_name}({index_domain})"
                    else:
                        identifier_reference = f"{gii_dict["Prefix"]}::{new_name}"

                    # The real work is the creation of the new parameter in the AIMMS model.
                    # This is done here, by adding a new parameter with the appropriate attributes.
                    # print(f"substituting expression, new_name=\"{new_name}\"")
                    modeledit_aimmspy2.create(aimms_model, new_name, id_type, gii_dict["gui_expression_substitutions"], 0)
                    name_ref = f"{gii_dict["Prefix"]}::{new_name}"
                    if index_domain != "":
                        modeledit_aimmspy2.setAttributeText(aimms_model, name_ref, "index domain", index_domain)
                    if set_name != "":
                        modeledit_aimmspy2.setAttributeText(aimms_model, name_ref, "range", set_name)
                    modeledit_aimmspy2.setAttributeText(aimms_model, name_ref, "definition", expr_body)
                    # print(f"name_ref={name_ref}, set_name={set_name}, index_domain={index_domain}, expr_body={expr_body}")
                    modeledit_aimmspy2.doCompile(aimms_model, name_ref)
                    break

    return identifier_reference

def make_webui_scalar_reference(aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, purpose: str, winui_scalar_reference:str,value_type:str, set_range:str) -> str:
    """
    A WinUI scalar reference can be of the form x( ep ), whereby ep is an element parameter and x an indexed parameter.
    A WebUI scalar reference can only be a scalar.  So we need a definition d = x(ep), and use d in text, image, and iframe widgets.
   
    :param aimms_model: AIMMS model handle used to create replacement identifiers.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary used for context during identifier creation.
    :type webui_page_dict: dict
    :param page_name: Name of the page containing the expression.
    :type page_name: str
    :param purpose: Short description of how the expression is used (for naming/logging).
    :type purpose: str
    :param arg_expression: AIMMS expression to potentially substitute.
    :type arg_expression: str
    :param value_type: One of: numeric, string, or element
    :type value_type: str 
    :param set_range: if value_type == element, then the fully qualified set name.
    :type set_range: str  
    :return: Original expression or the reference to the generated identifier replacing it.
    :rtype: str
    """
    # print(f"make_webui_scalar_reference(...,{winui_scalar_reference})")
    sub_number = get_next_substitution_number()
    page_slug = aimms_slug.aimms_slug(page_name)
    new_name = f"sp_{page_slug}_{purpose}_{sub_number}"
    if value_type == "string":
        identifier_type = "string parameter"
        new_name = f"sp_{page_slug}_{purpose}_{sub_number}"
    elif value_type == "element":
        identifier_type = "element parameter"
        new_name = f"ep_{page_slug}_{purpose}_{sub_number}"
    else:
        identifier_type = "parameter"
        new_name = f"p_{page_slug}_{purpose}_{sub_number}"
    if component_dict['Prefix'] != "":
        new_name = f"{component_dict['Prefix']}_{new_name}"     
    identifier_reference = f'{gii_dict["Prefix"]}::{new_name}'
    # Create the new scalar parameter in the AIMMS model.   
    
    modeledit_aimmspy2.create(aimms_model, new_name, identifier_type, gii_dict["gui_expression_substitutions"], 0)
    if value_type == "element":
        modeledit_aimmspy2.setAttributeText(aimms_model, identifier_reference, "range", set_range )
    modeledit_aimmspy2.setAttributeText(aimms_model, identifier_reference, "definition", winui_scalar_reference )
    modeledit_aimmspy2.doCompile(aimms_model, identifier_reference)

    return identifier_reference
