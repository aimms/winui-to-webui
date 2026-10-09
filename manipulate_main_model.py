#from lxml import etree as ET
import lxml.etree as ET


def ensureSystemLibrary(project_file:str, syslib:str) -> None:
    """
    Ensure a system library entry exists in the AIMMS project file, adding it when absent.
    
    :param project_file: Path to the AIMMS project file (.aimms) to update.
    :type project_file: str
    :param syslib: Name of the system library that must be present.
    :type syslib: str
    :return: None. Modifies the project file in-place if the system library is missing.
    :rtype: None
    """
    # print(f"ensureSystemLibrary({project_file}, {syslib})")
    project_file_xml_tree = ET.parse(project_file)
    project_file_xml_tree_root = project_file_xml_tree.getroot()

    # Check if the system library is present.
    lib_present = 0
    for component in project_file_xml_tree_root:
        if component.tag == "Library":
            if 'System' in component.attrib:
                if component.get('Path') == syslib:
                    lib_present = 1

    # if it is not present, insert it as the first library.
    if lib_present == 0:
        syslib_dict = { 'System' : "true", 'Path' : syslib }
        new_syslib = ET.Element('Library', syslib_dict)  
        project_file_xml_tree_root.insert(1,new_syslib)
        ET.indent(project_file_xml_tree, space='    ', level=0)
        project_file_xml_tree.write(project_file, encoding='utf-8', xml_declaration=True)

    return

def ensureRepositoryLibrary(project_file:str, repolib:str, repodict:dict) -> None:
    """
    Ensure a repository library entry exists in the AIMMS project file, inserting it with provided metadata when absent.
    
    :param project_file: Path to the AIMMS project file (.aimms) to update.
    :type project_file: str
    :param repolib: Name of the repository library that must be present.
    :type repolib: str
    :param repodict: Attribute dictionary describing the repository library entry.
    :type repodict: dict
    :return: None. Updates the project XML if the repository library is not found.
    :rtype: None
    """
    # print(f"ensureRepositoryLibrary({project_file}, {repolib})")
    project_file_xml_tree = ET.parse(project_file)
    project_file_xml_tree_root = project_file_xml_tree.getroot()

    # Check if the system library is present.
    lib_present = 0
    for component in project_file_xml_tree_root:
        if component.tag == "RepositoryLibrary":
            if component.get('Name') == repolib:
                lib_present = 1

    # if it is not present, insert it as a repo library.
    if lib_present == 0:
        new_repolib = ET.Element('RepositoryLibrary', repodict)  
        project_file_xml_tree_root.insert(2,new_repolib)
        ET.indent(project_file_xml_tree, space='    ', level=0)
        project_file_xml_tree.write(project_file, encoding='utf-8', xml_declaration=True)

    return 

def ensureExistingLibrary(project_file:str, thislib:str) -> None:
    """
    Ensure an existing library entry is present in the AIMMS project file, appending it when missing.
    
    :param project_file: Path to the AIMMS project file (.aimms) to update.
    :type project_file: str
    :param thislib: Relative path of the library that should be referenced.
    :type thislib: str
    :return: None. Writes the library entry to the project file if it does not exist.
    :rtype: None
    """
    # print(f"ensureExistingLibrary({project_file}, {thislib})")
    project_file_xml_tree = ET.parse(project_file)
    project_file_xml_tree_root = project_file_xml_tree.getroot()

    # Check if the system library is present.
    lib_present = 0
    for component in project_file_xml_tree_root:
        if component.tag == "Library":
            if component.get('Path') == thislib:
                lib_present = 1

    # if it is not present, insert it as a repo library.
    if lib_present == 0:
        thislib_dict = { "Path" : thislib }
        new_lib = ET.Element('Library', thislib_dict)  
        project_file_xml_tree_root.append(new_lib)
        ET.indent(project_file_xml_tree, space='    ', level=0)
        project_file_xml_tree.write(project_file, encoding='utf-8', xml_declaration=True)

    return

def removeLibrary(project_file:str, thislib:str) -> None:
    """
    Remove a specific library entry from the AIMMS project file when present.
    
    :param project_file: Path to the AIMMS project file (.aimms) to update.
    :type project_file: str
    :param thislib: Relative path of the library to remove.
    :type thislib: str
    :return: None. Writes the modified project XML after removing the library entry.
    :rtype: None
    """
    # print(f"removeLibrary({project_file}, {thislib})")
    project_file_xml_tree = ET.parse(project_file)
    project_file_xml_tree_root = project_file_xml_tree.getroot()

    # Check if the library is present and remove it.
    for component in project_file_xml_tree_root:
        if component.tag == "Library":
            if component.get('Path') == thislib:
                project_file_xml_tree_root.remove(component)

    ET.indent(project_file_xml_tree, space='    ', level=0)
    project_file_xml_tree.write(project_file, encoding='utf-8', xml_declaration=True)

    return
