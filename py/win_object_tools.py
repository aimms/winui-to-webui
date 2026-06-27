from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
import lxml.etree as ET
import win_expression
import tools
from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import modeledit_aimmspy2
import identifier_element_text
import re

def determine_no_identifiers(winui_table_xml:ET.Element) -> int:
    """
    Determine how many identifier entries exist in a WinUI table XML element.
    
    :param winui_table_xml: XML element containing the WinUI table definition.
    :type winui_table_xml: ET.Element
    :return: Number of explicit identifier declarations found.
    :rtype: int
    """
    no_identifiers = 0
    for table_child in winui_table_xml:
        if table_child.tag == 'ExplicitIdentifier' or table_child.tag == 'Explicit_Identifier':
            no_identifiers += 1

    return no_identifiers

def find_identifiers(expr:str) -> list[str]:
    """
    Finds all valid identifiers in a given string expression.

    An identifier must:
    1. Start with a letter (a-z, A-Z) or underscore (_).
    2. Be followed by any combination of letters, digits (0-9), or underscores.
    3. Optionally contain a double colon (::) followed by more valid identifier characters.

    :param expr: the expression to be modified.
    :type expr: str
  
    :return: list of identifiers
    :rtype: list[str]
    """
    # The pattern explained:
    # r'...' makes it a raw string.
    # 1. [a-zA-Z_] : Start with a letter or an underscore.
    # 2. (?: [a-zA-Z0-9_] | :: )* : This is the main body, allowing zero or more 
    #    occurrences of:
    #    - a letter, digit, or underscore ( [a-zA-Z0-9_] ) 
    #    - OR a double colon ( :: )
    pattern = r"[a-zA-Z_](?:[a-zA-Z0-9_]|::)*"

    # re.findall returns a list of all non-overlapping matches
    return re.findall(pattern, expr)

def find_scoped_identifiers(expr):
    """
    Finds identifiers that consist of one or more name segments joined by '::'.

    Name segments start with [a-zA-Z_] and are followed by [a-zA-Z0-9_]*.

    :param expr: the expression to be modified.
    :type expr: str
  
    :return: list of identifiers
    :rtype: list[str]
    """
    
    # Pattern for a single name segment (e.g., "MyClass" or "_var1")
    name_segment = r"[a-zA-Z_][a-zA-Z0-9_]*"
    
    # Pattern for the full identifier: 
    # Matches one name_segment, optionally followed by (:: and another name_segment) zero or more times.
    pattern = rf"{name_segment}(?::{name_segment})*"

    # re.findall returns a list of all non-overlapping matches
    return re.findall(pattern, expr)


def remove_duplicates(input_list:list[str]) -> list[str]:
    """
    Removes duplicates from a list by converting it to a set and back to a list.

    :param input_list: a list of strings, potentially containing duplicates.
    :type input_list: list[str]
    
    :return: list of unique strings
    :rtype: list[str]
    """
    # 1. Convert the list to a set to remove duplicates
    unique_set = set(input_list)
    
    # 2. Convert the set back to a list
    unique_list = list(unique_set)
    
    return unique_list

def namespace_qualification(aimms_model: Model, expr:str, prefix:str)->str:
    """
    namespace_qualification - ensure identifiers have the correct prefix.
    
    Add prefix to those identifiers in expr that are declared inside namespace with prefix str, 
    but do not have that prefix in the expr.

    :param aimms_model: AIMMS model handle used to inspect identifiers and their domains.
    :type aimms_model: Model
    :param expr: the expression to be modified.
    :type expr: str
    :param prefix: the prefix to be used.
    :type prefix: str
    :return: adapted expr, where str is added when needed.
    :rtype: str
    """
    #inp_expr = expr
    #if expr.find('gui::gui::') >= 0:
    #    dummy = 1
    if prefix != '':
        ids = find_identifiers(expr)
        unique_ids = remove_duplicates(ids)
        for id in unique_ids:
            if id.find("::") <0:
                dim_main = modeledit_aimmspy2.getDim(aimms_model, id)
                dim_lib  = modeledit_aimmspy2.getDim(aimms_model, prefix + "::" + id)
                if ( dim_main < 0 ) and ( dim_lib >= 0 ):
                    expr = expr.replace(id,prefix + "::" + id)

    expr = expr.replace(prefix + "::" + prefix + "::", prefix + "::")

    return expr

def investigate_contents(aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_data_xml:ET.Element, content_lists_expected:dict) -> dict:
    """
    Inspect WinUI data content and translate identifiers, slicing, and headers into WebUI-compatible structures.
    
    :param aimms_model: AIMMS model handle used to inspect identifiers and their domains.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary used for context during expression substitution.
    :type webui_page_dict: dict
    :param page_name: Name of the page being processed.
    :type page_name: str
    :param winui_data_xml: XML element representing the WinUI data definition.
    :type winui_data_xml: ET.Element
    :param content_lists_expected: Flags describing which content partitions should be constructed.
    :type content_lists_expected: dict
    :return: Dictionary describing contents, partitions, and optional focus information for WebUI widgets.
    :rtype: dict
    """

    store_focus_in = {} # to store info from reverse links in Pivot tables, and 'link to parameters' in contents of WinUI data objects.
    contents_xml = winui_data_xml
    if winui_data_xml.get('Type') == 'Pivot Table':
        for table_cat in winui_data_xml:
            if table_cat.tag == 'Contents':
                contents_xml = table_cat
        for content_child in winui_data_xml:
            if content_child.tag == 'Indices':
                # pivot tables also provide an alternative way for specifying reverse links, namely via the explicit indices.
                for content_grandchild in content_child:
                    if content_grandchild.tag == 'Explicit_Index':
                        index_elem_name = ''
                        index_elem_link_to_param = ''
                        for index_elem in content_grandchild:
                            if index_elem.tag == 'Index':
                                index_elem_name = str(index_elem.text)
                            if index_elem.tag == 'Link_to_Element_Parameter':
                                index_elem_link_to_param = str(index_elem.text)
                        if index_elem_name != '' and index_elem_link_to_param != '':
                            store_focus_in[index_elem_name] = index_elem_link_to_param

    # behavior differs for scalar/selectionbox versus indexed data.
    if content_lists_expected['objecttype'] == 'scalar' or content_lists_expected['objecttype'] == 'selectionbox-v2':
        is_scalar = 1
    else:
        is_scalar = 0

    no_identifiers = determine_no_identifiers(contents_xml)
    if no_identifiers == 0:
        print("Warning: no identifiers found in contents?")
        return_dict: dict[str, Any] = {}
        return return_dict

    identifier_text:str

    domain_identifier = ''
    domain_identifier_args: List[str] = []

    for table_child in contents_xml:
        if table_child.tag == 'Domain':
            for table_grandchild in table_child:
                if table_grandchild.tag == 'Identifier':
                    if type(table_grandchild.text) is str:
                        domain_identifier_text = table_grandchild.text
                        purpose = str(contents_xml.get('Type',"surprise") ).replace(' ','_') + "_domain"
                        domain_identifier_text = namespace_qualification( aimms_model, domain_identifier_text, component_dict['Prefix'] )
                        # if domain_identifier_text.find('gui::gui::') >= 0:
                        #     dummy = 1
                        domain_identifier_text = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, purpose, domain_identifier_text)
                        identifier_text_name, identifier_text_args = tools.parse_aimms_string(domain_identifier_text)
                        domain_identifier = identifier_text_name
                        domain_identifier_args = identifier_text_args

    first_column = -1
    if contents_xml.get('Type','') == 'Composite Table':
        first_column = 31
    return_dict = {}
    contents_list = []
    rowheader_list = []
    colheader_list = []
    aggregate_list = []
    header_list = []
    grouped_list = []
    stacked_list: list[str] = []
    overlay_list = []

    # For each explicit identifier idn, whereby decimals, readonly, (in)visible is specified, 
    # there will be an entry of the form: identifier_name : { "literal" : 0/1, "value" : number or name }
    decimals_dict = {} 
    visible_dict  = {}
    readonly_dict = {}
    for table_child in contents_xml:

        if table_child.tag == 'ExplicitIdentifier' or table_child.tag == 'Explicit_Identifier':

            no_decimals = 2
            literal_num_decimals = 0
            literal_name_decimals = 0
            ro_val = 0
            
            hid_seen = 0
            ro_seen = 0

            header_text = ""
            header_from_text_attrib = 0

            # Determine Identifier text, and some other attributes.
            for table_grandchild in table_child:

                if table_grandchild.tag == 'HeaderText' or table_grandchild.tag == 'TitleText':
                    if type(table_grandchild.text) is str:
                        header_text = table_grandchild.text
                    
                if table_grandchild.tag == 'IdentifierTextInTitle':
                    header_from_text_attrib = 1  

                if table_grandchild.tag == 'Identifier':
                    identifier_text = ""
                    if type(table_grandchild.text) is str:
                        identifier_text = table_grandchild.text
                     
                if table_grandchild.tag == 'NumberFormat':
                    if 'Decimals' in table_grandchild.attrib:
                        no_decimals = int( table_grandchild.attrib['Decimals'] )
                        literal_num_decimals = 1

                if table_grandchild.tag == 'NrDecimals':
                    if type(table_grandchild.text) is str:
                        name_decimals = str(table_grandchild.text)
                        literal_name_decimals = 1

                if table_grandchild.tag == 'Readonly':
                    if type(table_grandchild.text) is str:
                        ro_txt = str(table_grandchild.text)
                        ro_seen = 1
                        if ro_txt == '1' or ro_txt == '"Yes"':
                            ro_literal = 1
                            ro_val = 'true'
                        elif ro_txt == '0' or ro_txt == '"No"':
                            ro_literal = 1
                            ro_val = 'false'
                        else:
                            ro_literal = 0
                            ro_val = ro_txt

                if table_grandchild.tag == 'Hidden':
                    if type(table_grandchild.text) is str:
                        hid_txt = str(table_grandchild.text)
                        hid_seen = 1
                        if hid_txt == '1' or hid_txt == '"Yes"':
                            hid_literal = 1
                            hid_val = 1
                        elif hid_txt == '0' or hid_txt == '"No"':
                            hid_literal = 1
                            hid_val = 0
                        else:
                            hid_literal = 0
                            hid_val = hid_txt

                if table_grandchild.tag == 'FirstColumn':
                    if type(table_grandchild.text) is str:
                        first_column = int( table_grandchild.text )

            # decimals handling.
            if literal_name_decimals == 1:
                decimals_entry = {
                    "literal" : 0,
                    "value" : name_decimals
                }
            elif literal_num_decimals == 1:
                decimals_entry = {
                    "literal" : 1,
                    "value" : no_decimals
                }
            else:
                decimals_entry = {}

            # visibility handling
            if hid_seen:
                if hid_literal:
                    if hid_val == 1:
                        vis_val = 'Never Show'
                    else:
                        vis_val = 'Always Show'
                    visible_entry = {
                        "literal": 1,
                        "value": vis_val
                    }
                else:
                    hid_txt = hid_val
                    if hid_txt.startswith('VALUE'):
                        vis_expr = "1 - ( " + hid_txt[8:] + " )"
                    else:
                        vis_expr = f"1 - {hid_txt}"
                    vis_expr = namespace_qualification(aimms_model, vis_expr, component_dict['Prefix'])
                    vis_num_id  = win_expression.make_webui_scalar_reference(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, "visibility", vis_expr, "numeric", "")
                    # 'Never Show', 'Always Show'
                    vis_elem_id = win_expression.make_webui_scalar_reference(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, "visibility", f"if {vis_num_id} then 'Always Show' else 'Never Show' endif", "element", "gii::s_visibility_values")
                    visible_entry = {
                        "literal": 0,
                        "value": vis_elem_id
                    }
            else:
                visible_entry = {}

            # readonly handling
            if ro_seen:
                if ro_literal:
                    ro_entry = {
                        "literal": 1,
                        "value": ro_val
                    }
                else:
                    ro_txt = ro_val
                    if ro_txt.startswith('VALUE'):
                        ro_expr = namespace_qualification(aimms_model, vis_expr, component_dict['Prefix'])
                        ro_num_id  = win_expression.make_webui_scalar_reference(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, "readonly", ro_expr, "numeric")
                    else:
                        ro_num_id = ro_txt
                    ro_elem_id = win_expression.make_webui_scalar_reference(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, "readonly", f"if {ro_num_id} then 'True' else 'False' endif", "element", "s_readonly_values")
                    ro_entry = {
                        "literal": 0,
                        "value": ro_elem_id
                    }
            else:
                ro_entry = {}

            # Process Identifier text, and place in appropriate lists.
            if identifier_text != '' and identifier_text != '""':
                purpose = str(contents_xml.get('Type',"surprise") ).replace(' ','_') + "_content"
                #if identifier_text.find('Ps_GUI_UltimoEstadoSalvo') >=0:
                #    dummy = 1
                identifier_text = namespace_qualification( aimms_model, identifier_text,  component_dict['Prefix'])
                identifier_text = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict, page_name, purpose, identifier_text)
                identifier_text_name, identifier_text_args = tools.parse_aimms_string(identifier_text)
                suffix_list_start_pos = identifier_text_name.find('.[')
                if suffix_list_start_pos >= 0:

                    pure_name = identifier_text_name[:suffix_list_start_pos]
                    suffix_text = identifier_text_name[suffix_list_start_pos+2:]
                    komma_pos = suffix_text.find(',')
                    bracket_close_pos = suffix_text.find(']')

                    while komma_pos >= 0 and komma_pos < bracket_close_pos:

                        # Store
                        temp_text_name = pure_name + '.' + suffix_text[:komma_pos]
                        contents_list.append( temp_text_name )

                        # Shift Suffix text
                        suffix_text = suffix_text[komma_pos+1:]
                        komma_pos = suffix_text.find(',')

                    # Store last id.suffix
                    bracket_close_pos = suffix_text.find(']')
                    temp_text_name = pure_name + '.' + suffix_text[:bracket_close_pos]
                    contents_list.append( temp_text_name )

                    identifier_text_name = pure_name
                else:
                    contents_list.append( identifier_text_name )
                    dot_pos = identifier_text_name.find('.')
                    if dot_pos >=0:
                        identifier_text_name= identifier_text_name[:dot_pos]

                # Determine full identifier text name, including prefix.
                # if component_dict["Prefix"] == "":
                #     full_identifier_text_name = identifier_text_name 
                # else:
                #     full_identifier_text_name = component_dict["Prefix"] + "::" + identifier_text_name
                full_identifier_text_name = identifier_text_name

                # Determine header text, if it comes from the identifier declaration in the AIMMS model.
                if header_text == "":
                    if header_from_text_attrib:
                        header_text = modeledit_aimmspy2.getText(aimms_model, full_identifier_text_name)

                # Remove surrounding quotes from header text, if any.   
                if len(header_text) > 2 and header_text[0] == '"' and header_text[-1] == '"':
                    header_text = header_text[1:-1]

                if header_text != "":
                    identifier_element_text.add_element_safely( full_identifier_text_name, header_text)

                identifier_text_no_args = len( identifier_text_args )
                identifier_dim = modeledit_aimmspy2.getDim(aimms_model, identifier_text_name)
                if identifier_dim != identifier_text_no_args:
                    print(f"Warning: identifier '{identifier_text_name}' has dimension {identifier_dim} but {identifier_text_no_args} arguments in WinUI.")
                identifier_text_indices = [] 
                for indexPos in range(1, identifier_text_no_args + 1):
                    domain_index_name = modeledit_aimmspy2.getDomainIndex(aimms_model, identifier_text_name, indexPos)
                    identifier_text_indices.append( domain_index_name )

                only_free = 1
                slices = []
                arg_free_pos = 0
                for argpos in range(identifier_text_no_args):
                    arg = identifier_text_args[argpos]
                    domain_index_name = identifier_text_indices[argpos]

                    # extract "link index entry to" type of reverse links.
                    # syntax in the contents is a(i->ep)
                    p_revLinkarrow = arg.find('->')
                    if p_revLinkarrow >= 0:
                        store_focus_in[domain_index_name] = arg[p_revLinkarrow+2:]
                        arg = arg[0:p_revLinkarrow]

                    # Construct the slicing
                    is_scalar_element_parameter = modeledit_aimmspy2.isScalarElementParameter( aimms_model, arg )
                    if is_scalar_element_parameter == 0:
                        if arg == domain_index_name:
                            arg_type = "free"
                        else:
                            arg_type = "subset"
                            only_free = 0
                    else:
                        arg_type = "element-parameter"
                        only_free = 0
                    slicing_arg_dict = {
                        "index" : domain_index_name,
                        "type"  : arg_type,
                        "value" : arg
                    }
                    slices.append(slicing_arg_dict)

                    # Construct the partition.
                    if ( no_identifiers == 1 ) and ( first_column < 31 ):
                        if first_column >= 0:
                            if argpos < first_column:
                                rowheader_list.append( domain_index_name )
                            else:
                                colheader_list.append( domain_index_name )
                        else:
                            if content_lists_expected['header'] == 1:
                                header_list.append( domain_index_name )
                            else:
                                if identifier_text_no_args==1:
                                    rowheader_list.append( domain_index_name )
                                else:
                                    if argpos < identifier_text_no_args-1:
                                        rowheader_list.append( domain_index_name )
                                    else:
                                        colheader_list.append( domain_index_name )    
                    else:
                        # Multiple identifiers, place all args in header or rowheader.
                        if content_lists_expected['header'] == 1:
                            if not domain_index_name in header_list:
                                header_list.append( domain_index_name )
                        elif content_lists_expected['rowHeader'] == 1:
                            if not domain_index_name in rowheader_list:
                                rowheader_list.append( domain_index_name )
                    if not is_scalar_element_parameter:
                        arg_free_pos += 1

            if decimals_entry != {}:
                decimals_dict[identifier_text_name] = decimals_entry
            if visible_entry != {}:
                visible_dict[identifier_text_name] = visible_entry
            if ro_entry != {}:
                readonly_dict[identifier_text_name] = ro_entry

    # Place the identifier list in the appropriate partition list.
    if is_scalar == 0:
        if no_identifiers > 1:
            if content_lists_expected['colHeader'] == 1:
                colheader_list.append( "<IDENTIFIER-SET>" ) 
            elif content_lists_expected['overlays'] == 1:
                overlay_list.append( "<IDENTIFIER-SET>" )
            elif content_lists_expected['grouped'] == 1:
                grouped_list.append( "<IDENTIFIER-SET>" )
            else:
                print("Warning: multiple identifiers but no header, overlays, or grouped expected?")
        else:
            if identifier_text_no_args==1:
                colheader_list.append( "<IDENTIFIER-SET>" )
            else:
                aggregate_list.append( "<IDENTIFIER-SET>" )

    loc_contents_dict: dict[str, Any] = {}
    if only_free == 1:
        loc_contents_dict = {
            "contents": contents_list
        }
    else:
        slices_entry = {
            "identifier" : identifier_text_name,
            "slice": slices
        }
        slices_list = [slices_entry]
        loc_contents_dict = {
            "contents": contents_list,
            "prefix" : "aimms",
            "slices" : slices_list
        }

    # Insert domain spec if any.
    domain_literal_dict = {}
    if domain_identifier != '':
        for loc_id in contents_list:
            domain_literal_dict[loc_id] = domain_identifier
        domain_dict = {
            "literal": domain_literal_dict
        }

    return_dict = {
        "contents": {
            "aimms" : loc_contents_dict
        },
        "contents.partition": {
            "rowHeader": rowheader_list,
            "colHeader": colheader_list,
            "header": header_list,
            "aggregated": aggregate_list,
            "stacked": stacked_list,
            "overlays": overlay_list,
            "grouped": grouped_list
        }
    }
    if domain_literal_dict != {}:
        return_dict['contents.displaydomain'] = domain_dict
    if store_focus_in != {}:
        return_dict['store.focus.in'] = store_focus_in

    return_dict['decimals'] = decimals_dict
    return_dict['visible']  = visible_dict
    return_dict['readonly'] = readonly_dict

    return return_dict

def substitute_reference(imms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, reference: str) -> str:
    """
    substitute_reference : 
        in webui a reference is just a scalar parameter, 
        in winui it can also be an indexed parameter, whereby element parameters are used to point to the relevant element.
    
    :param imms_model: AIMMS model handle used to inspect identifiers and their domains.
    :type imms_model: Model
    :param gii_dict: DescRuntime library dictionary produced during conversion.ription
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: DescrWebUI page dictionary used for context during expression substitution.iption
    :type webui_page_dict: dict
    :param page_name: ame of the page being processed.
    :type page_name: str
    :param reference: scalar reference that may contain element parameters to point to the element of the string parameter
    :type reference: str

    :return: reference that is a scalar parameter.
    :rtype: str
    """