import modeledit_aimmspy
import modeledit_aimmspy2
from aimmspy.project.project import Project, Model
from typing import Any

# Initialiseer de datastructuur
webui_identifier_title_mapping: dict[str, str] = {}

def add_element_safely(key_string: str, value_string: str) -> None:
    """
    Add a key-value mapping to the global title dictionary while warning on conflicting duplicates.
    
    :param key_string: Identifier or element name used as the dictionary key.
    :type key_string: str
    :param value_string: Display title associated with the identifier.
    :type value_string: str
    :return: None. Updates the global mapping in-place and prints a warning when a conflicting entry exists.
    :rtype: None
    """
    #print(f"identifier_element_text.add_element_safely({key_string},{value_string})")

    global webui_identifier_title_mapping

    if key_string in webui_identifier_title_mapping:
        # Key exists. Check if the value is different.
        if webui_identifier_title_mapping[key_string] != value_string:
            print(f"⚠️ Warning: Key '{key_string}' already exists with value '{webui_identifier_title_mapping[key_string]}', but you tried to set it to '{value_string}'. The original value remains unchanged.")
        # If the values are the same, do nothing (no warning, no change).
    else:
        # Key is new, add it.
        webui_identifier_title_mapping[key_string] = value_string
        #print(f"✅ Added: '{key_string}' with value '{value_string}' to the dictionary with {len(webui_identifier_title_mapping)} elements.")



def generate_pr_adaptNamesForPresentationInWebUI(aimms_model: Model, gii_dict: dict) -> None:
    """
    Create or update the AIMMS procedure `pr_adaptNamesForPresentationInWebUI` with the collected identifier title mappings.
    
    :param aimms_model: Handle to the AIMMS model used for writing the procedure body.
    :type aimms_model: Model
    :param gii_dict: Dictionary containing runtime library identifiers and handles.
    :type gii_dict: dict
    :return: None. Writes the generated procedure body back into the AIMMS model when mappings exist.
    :rtype: None
    """
    # item_key = ''
    # item_val = ''   
    # for item_key, item_val in webui_identifier_title_mapping.items():
    #     print(f"Mapping '{item_key}' to \"{item_val}\"")

    no_items = len(webui_identifier_title_mapping)
    if no_items == 0:
        return 

    sp_body_text = ''
    if no_items == 1:
        item_keys = list(webui_identifier_title_mapping.keys())
        item_vals = list(webui_identifier_title_mapping.values())
        item_key = item_keys[0]
        item_val = item_vals[0] 
        #item_key = str(webui_identifier_title_mapping.keys()[0])
        #item_val = str(webui_identifier_title_mapping.values()[0])
        sp_body_text = "webui::IdentifierElementText(IndexIdentifiers) :=$ data { '" + f"{item_key}" + "' : \"" + f"{item_val}" + "\" };"
    else:
        sp_body_text = "webui::IdentifierElementText(IndexIdentifiers) :=$ data {"
        for item_key, item_val in webui_identifier_title_mapping.items():
            sp_body_text += f"\n    '{item_key}' : '{item_val}'"
            if item_key != list(webui_identifier_title_mapping.keys())[-1]: 
                sp_body_text += ","
        sp_body_text += "};"

    #print("Generated procedure body:")
    #print(sp_body_text)
    modeledit_aimmspy2.setAttributeText(aimms_model, gii_dict["sp_pr_adaptNamesForPresentationInWebUI"], "body", sp_body_text)
