import re
import os
import pathlib
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

    match = re.match(pattern, expression.strip())

    if not match:
        # Should not happen with this pattern, but good practice
        print(f"Warning: Unable to parse expression '{expression}'")
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
