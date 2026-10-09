import re
import os
import pathlib
import sys
import traceback
from typing import Tuple, List

def parse_aimms_string(expression: str) -> Tuple[str, List[str]]:
    """
    Parse AIMMS-like strings such as `a`, `b(i)`, or `c(j,k)` into a base name and list of arguments.
    
    :param expression: Raw AIMMS expression to dissect.
    :type expression: str
    :return: Tuple containing the identifier name and a list of parsed arguments (empty when none).
    :rtype: Tuple[str, List[str]]
    """
    # Pattern explanation:
    # 1. (^.+?) : Group 1 (Name). Matches one or more characters from the start (non-greedily).
    # 2. (\((.*)\))? : Group 2 (Optional Arguments). Matches zero or one of the following:
    #    - \( : Literal open parenthesis.
    #    - (.*) : Group 3 (Arguments). Captures all content inside the parentheses.
    #    - \) : Literal close parenthesis.
    pattern = r"^(.*?)(?:\((.*)\))?$"

    # Newlines and tabs are treated exactly like spaces (a caller may pass raw, multi-line,
    # indented WinUI source text, e.g. a multi-line "VALUE := ..." expression) - the pattern's
    # '.' doesn't otherwise cross a '\n' without re.DOTALL.
    single_line_expression = re.sub(r"[\n\t]", " ", expression.strip())

    match = re.match(pattern, single_line_expression)

    if not match:
        # Warn with a traceback so the offending call site is immediately traceable, but don't
        # raise - callers aren't expecting this to fail.
        try:
            raise ValueError(f"Unable to parse expression as an AIMMS identifier reference: {expression!r}")
        except ValueError:
            traceback.print_exc(file=sys.stderr)
        return expression, []

    # Group 1 is always the name
    name = match.group(1).strip()

    # Group 3 contains the raw comma-separated arguments (or None if no parentheses)
    raw_args = match.group(2)

    if raw_args:
        # Split by comma, strip leading/trailing spaces from each argument
        args = [arg.strip() for arg in raw_args.split(',')]
    else:
        args = []

    return name, args


def string_to_model_text(text: str) -> str:
    """
    Converts a plain Python string into AIMMS's own "string in model text" form - the escaped
    representation to embed between double quotes in an AIMMS .ams source file, so any character
    in `text` that would otherwise corrupt or truncate the resulting string literal round-trips
    correctly instead (e.g. an identifier's own declared Text: attribute, or a WinUI Title/
    Description, embedded verbatim in a generated `data { 'key' : "value" }` literal - see
    identifier_element_text.generate_pr_adaptNamesForPresentationInWebUI):
    - '\\' -> '\\\\'
    - '"'  -> '\\"'
    - "'"  -> "\\'"
    - a newline -> '\\n'
    - a tab -> '\\t'
    - anything else (ASCII or not) is passed through unchanged - the .ams file is UTF-8, so a
      non-ASCII character (e.g. 'é') is written as itself, not escaped.

    Processes `text` one source character at a time rather than a sequence of global replaces, so
    there's no risk of one rule's own escaped output (e.g. the '\\' a '"' rule just introduced)
    being mistaken for input and escaped a second time by a rule applied afterwards.

    :param text: Plain, unescaped text.
    :type text: str
    :return: text, escaped for direct embedding inside an AIMMS double-quoted string literal.
    :rtype: str
    """
    out = []
    for ch in text:
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif ch == "'":
            out.append("\\'")
        elif ch == '\n':
            out.append('\\n')
        elif ch == '\t':
            out.append('\\t')
        else:
            out.append(ch)
    return ''.join(out)


def optdel(fn:str) -> None:
    """ 
    Delete the file `fn` if it exists on disk.
    
    :param fn: File path to remove when present.
    :type fn: str
    :return: None. Removes the file if found.
    :rtype: None
    """
    if os.path.exists(fn):
        os.remove(fn)
        #print(f"Deleted existing file: {fn}")   

def optdel_webui(component_path_attribute:str) -> None:
    """ 
    Delete the `webui.json` file located in the WebUI subfolder of the given component path when it exists.
    
    :param component_path_attribute: Component path inside the AIMMS project containing the WebUI folder.
    :type component_path_attribute: str
    :return: None. Removes the file if present.
    :rtype: None
    """
    webui_json_file = os.path.join(component_path_attribute, "WebUI", "webui.json")
    if os.path.exists(webui_json_file):
        os.remove(webui_json_file)
        #print(f"Deleted existing file: {webui_json_file}")  
