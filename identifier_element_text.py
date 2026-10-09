import modeledit_aimmspy
import modeledit_aimmspy2
from aimmspy.project.project import Project, Model
from typing import Any, Optional
import ams_file_editor as afe
import gii_module
import tools

# Initialiseer de datastructuur
webui_identifier_title_mapping: dict[str, str] = {}
# Every OTHER value add_element_safely saw for a key already registered under
# webui_identifier_title_mapping - "first registration wins" for the actual mapping (unchanged),
# but a rejected alternative is still worth surfacing to the modeler (see
# generate_pr_adaptNamesForPresentationInWebUI's own trailing "! Alternatives: ..." comment)
# rather than only ever being visible as a console warning easy to miss in a large project's
# conversion log. Deduplicated, insertion order preserved.
webui_identifier_title_alternatives: dict[str, list[str]] = {}


def ensure_lifecycle_procedures(gii_dict: dict, aimms_model: Model, main_model_component_dict: dict) -> None:
    """
    Ensures the main model has its own PostMainInitialization and PreMainTermination
    procedures - standard AIMMS App Framework lifecycle hooks. Older/customized projects
    don't always have the full standard app_start_stop scaffolding; generate_pr_adaptNames-
    ForPresentationInWebUI() below unconditionally appends a call into PostMainInitialization's
    body, which otherwise fails once AIMMS is done and the queued edit is applied (see
    ams_file_editor.py) - by then it's too late to add the missing procedure around it.

    Queues creating whichever of the two is missing as a top-level procedure (not nested in
    any pre-existing "app_start_stop"-style section, since that section itself may not exist
    either). PreMainTermination gets the standard "return 1;" default body; PostMainInitialization
    is left with an empty body - generate_pr_adaptNamesForPresentationInWebUI() fills it in
    when there's anything to put there.

    :param gii_dict: Dictionary holding the shared edit queue (see gii_module.get_prefix for the "giim"/"giil" prefix).
    :type gii_dict: dict
    :param aimms_model: Live AIMMS model handle, used to check whether each procedure already exists.
    :type aimms_model: Model
    :param main_model_component_dict: component_dict for the main model (the component whose own
        Prefix is empty), captured during the per-component loop.
    :type main_model_component_dict: dict
    :return: None. Queues AddIdentifier/AppendToBody commands for whichever procedure is missing.
    :rtype: None
    """
    main_ams_path = main_model_component_dict["AmsPath"]
    root_name = afe.find_root_identifier(main_ams_path)
    for proc_name in ("PostMainInitialization", "PreMainTermination"):
        # isIdentifier() isn't existence: per ModelEditAimmsPython.ams's pr_isIdentifier, an
        # undeclared-but-well-formed name deliberately reports as "is an identifier" too (it
        # answers "could this be used as one", not "does it already exist"). getType() is the
        # one that distinguishes a genuinely undeclared name (it returns the literal string
        # "undeclared identifier" rather than raising).
        if modeledit_aimmspy2.getType(aimms_model, proc_name) == "undeclared identifier":
            gii_dict["_edit_queue"].append(afe.AddIdentifier(name=proc_name, type="procedure", parent=root_name, file_hint=main_ams_path))
            if proc_name == "PreMainTermination":
                gii_dict["_edit_queue"].append(afe.AppendToBody(identifier=proc_name, attribute="Body", statement="return 1;", file_hint=main_ams_path))

def add_element_safely(aimms_model: Model, key_string: str, value_string: str) -> None:
    """
    Add a key-value mapping to the global title dictionary.

    "First registration wins" for the actual mapping - a later, different value for the same key
    is never applied - but it's remembered in webui_identifier_title_alternatives, so
    generate_pr_adaptNamesForPresentationInWebUI can remind the modeler what else was seen for
    this key (its own trailing "! Alternatives: ..." comment). No console warning: that comment
    is where the modeler looks, and the warnings only cluttered a large project's conversion log.

    :param key_string: Identifier or element name used as the dictionary key.
    :type key_string: str
    :param value_string: Display title associated with the identifier.
    :type value_string: str
    :return: None. Updates the global mapping in-place, recording any conflicting value as an alternative.
    :rtype: None
    """
    #print(f"identifier_element_text.add_element_safely({key_string},{value_string})")

    global webui_identifier_title_mapping

    if key_string != '':
        if modeledit_aimmspy2.isIdentifier(aimms_model, key_string):
            if key_string in webui_identifier_title_mapping:
                # Key exists. Check if the value is different.
                if ( webui_identifier_title_mapping[key_string] != value_string) and (key_string != value_string):
                    alternatives = webui_identifier_title_alternatives.setdefault(key_string, [])
                    if value_string not in alternatives:
                        alternatives.append(value_string)
                # If the values are the same, do nothing (no warning, no change).
            else:
                # Key is new, add it.
                webui_identifier_title_mapping[key_string] = value_string
                #print(f"✅ Added: '{key_string}' with value '{value_string}' to the dictionary with {len(webui_identifier_title_mapping)} elements.")



def _alternatives_comment(alternatives: Optional[list[str]], indent: str) -> str:
    """
    A trailing "! Alternatives: ..." comment listing every OTHER value add_element_safely saw for
    a key (see webui_identifier_title_alternatives) - so the modeler can see, right next to the
    winning "first registration wins" value, what else was tried and reconsider if a different one
    would actually be the better display title - instead of that only ever having been a console
    warning, easy to miss across a large project's own conversion log.

    Wrapped across as many "!"-prefixed continuation lines as needed so a key with many rejected
    alternatives doesn't produce one unreadably long line - each alternative (itself possibly
    containing spaces, e.g. "Industrial Price: Option1") is kept whole, never split mid-value.

    :param alternatives: This key's own recorded alternatives, or None/empty if it has none.
    :type alternatives: Optional[list[str]]
    :param indent: Leading whitespace for every continuation line, sized by the caller to exactly
        the width of its own entry line (plus the one space before "!") - so a continuation
        line's own "!" lines up in the same text column as the first line's, not just starts
        somewhere indented under it. Every entry has a different length, so this is recomputed
        per call, never one fixed value for a whole data block.
    :type indent: str
    :return: The comment text (starting with "!", no leading/trailing newline), or "" when there
        are no alternatives to report.
    :rtype: str
    """
    if not alternatives:
        return ''
    quoted = [f'"{tools.string_to_model_text(alt)}"' for alt in alternatives]
    max_width = 100
    lines: list[str] = []
    current = "Alternatives:"
    for i, q in enumerate(quoted):
        piece = q + ("," if i < len(quoted) - 1 else "")
        candidate = f"{current} {piece}"
        if len(candidate) > max_width and current != "Alternatives:":
            lines.append(current)
            current = piece
        else:
            current = candidate
    lines.append(current)
    return f"! {lines[0]}" + "".join(f"\n{indent}! {line}" for line in lines[1:])


def generate_pr_adaptNamesForPresentationInWebUI(gii_dict: dict, main_model_component_dict: dict) -> None:
    """
    Queue creation of the AIMMS procedure `pr_adaptNamesForPresentationInWebUI`, with the collected
    identifier title mappings, inside the main model's own GeneratedInterfaceIdentifiers module -
    and queue a call to it from the main model's pre-existing PostMainInitialization body. Applied
    to the .ams files once AIMMS is done (see ams_file_editor.py).

    :param gii_dict: Dictionary holding the shared edit queue (see gii_module.get_prefix for the "giim"/"giil" prefix).
    :type gii_dict: dict
    :param main_model_component_dict: component_dict for the main model (the component whose own
        Prefix is empty), captured during the per-component loop.
    :type main_model_component_dict: dict
    :return: None. Queues the procedure's creation and its invocation when mappings exist.
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
        entry_text = "webui::IdentifierElementText(IndexIdentifiers) :=$ data { '" + f"{item_key}" + "' : \"" + tools.string_to_model_text(item_val) + "\" };"
        # Align any continuation line's own "!" under this line's "!" (one column past
        # entry_text's own end, where the space before "! Alternatives" goes) - see
        # _alternatives_comment.
        alt_comment = _alternatives_comment(webui_identifier_title_alternatives.get(item_key), indent=" " * (len(entry_text) + 1))
        sp_body_text = entry_text
        if alt_comment:
            sp_body_text += f" {alt_comment}"
    else:
        sp_body_text = "webui::IdentifierElementText(IndexIdentifiers) :=$ data {"
        last_line_has_comment = False
        for item_key, item_val in webui_identifier_title_mapping.items():
            entry_text = f"    '{item_key}' : \"{tools.string_to_model_text(item_val)}\""
            if item_key != list(webui_identifier_title_mapping.keys())[-1]:
                entry_text += ","
            sp_body_text += f"\n{entry_text}"
            # Align any continuation line's own "!" under THIS entry's own "!" - every entry
            # line has a different length, so this indent is recomputed per entry rather than
            # being one fixed column for the whole data block.
            alt_comment = _alternatives_comment(webui_identifier_title_alternatives.get(item_key), indent=" " * (len(entry_text) + 1))
            last_line_has_comment = bool(alt_comment)
            if alt_comment:
                sp_body_text += f" {alt_comment}"
        # The closing "};" must start its own line whenever the last entry's own line ends in a
        # "!" comment - that comment runs to end of line, so appending "};" straight after it on
        # the SAME line (as the no-comment case does, to keep today's compact style) would comment
        # the closing brace away too, breaking the whole statement.
        sp_body_text += "\n};" if last_line_has_comment else "};"

    #print("Generated procedure body:")
    #print(sp_body_text)
    proc_name = "pr_adaptNamesForPresentationInWebUI"
    main_ams_path = main_model_component_dict["AmsPath"]
    module_name = gii_module.ensure_module(gii_dict, main_model_component_dict)
    gii_dict["_edit_queue"].append(afe.AddIdentifier(name=proc_name, type="procedure", parent=module_name, file_hint=main_ams_path))
    gii_dict["_edit_queue"].append(afe.AppendToBody(identifier=proc_name, attribute="Body", statement=sp_body_text, file_hint=main_ams_path))
    gii_dict["_edit_queue"].append(afe.AppendToBody(identifier="PostMainInitialization", attribute="Body",
                                                     statement=f"{gii_module.get_prefix(main_model_component_dict)}::{proc_name}();", file_hint=main_ams_path))
