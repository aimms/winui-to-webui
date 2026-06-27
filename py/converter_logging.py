converter_log_filename: str = ''

def exoticW(messages: list[str], component_dict:dict, purpose:str, page_name:str) -> None:
    """
    Log messages to the conversion log and append a human-readable location summary derived from the component and page context.
    
    :param messages: The messages that need to be logged.
    :type messages: list[str]
    :param component_dict: Specification of the component (main project or library).
    :type component_dict: dict
    :param purpose: Description of the object purpose within the interface.
    :type purpose: str
    :param page_name: Name of the page where the messages originate.
    :type page_name: str
    :return: None. Writes messages to the converter log file.
    :rtype: None
    """
    if component_dict["Prefix"] == '':
        component_name = 'MainProject'
    else:
        component_name = component_dict["DisplayName"]
    loc_list = [f"Location: on page '{page_name}' purpose {purpose} of '{component_name}'."]
    exotic(messages + loc_list)

def exotic(messages: list[str]) -> None:
    """
    Log conversion-related messages to the converter log file without adding location context.
    
    :param messages: List of messages to write to the log.
    :type messages: list[str]
    :return: None. Writes formatted messages to the converter log file.
    :rtype: None
    """
    with open(converter_log_filename, 'a', encoding='utf-8') as f:
        lineNo = 0
        for message in messages:
            if lineNo == 0:
                f.write(f"* [ ] {message}\n")
            else:
                f.write(f"      {message}\n")
            lineNo += 1
        f.write("\n")

def lines(these:list[str]) -> None:
    """
    Write literal lines to the converter log file without additional formatting.
    
    :param these: List of literal strings to append to the log.
    :type these: list[str]
    :return: None. Appends the provided lines to the converter log file.
    :rtype: None
    """
    with open(converter_log_filename, 'a', encoding='utf-8') as f:
        for line in these:
            f.write(f"{line}\n")
        f.write("\n")

def open_log(project_name: str):
    """
    Initialize the converter log file for the given project and write the header content.
    
    :param project_name: Name of the AIMMS project being converted.
    :type project_name: str
    :return: None. Creates or overwrites the converter log file and writes the intro text.
    :rtype: None
    """
    global converter_log_filename

    converter_log_filename = f"{project_name}_conversion.md"
    start_lines = [
        f"# Log of upgrading AIMMS application {project_name} with a WebUI interface", 
        "", 
        f"This file logs the upgrade of AIMMS application {project_name} with a WebUI interface by using its WinUI information.",
        "It serves as a todo list for providing the finishing touch.",
        "",
        "Mark items done with ✅, and mark items declined with ✘." 
        ]
    with open(converter_log_filename,'w', encoding='utf-8') as f:
        for line in start_lines:
            f.write(line)
            f.write("\n")
        f.write("\n")
