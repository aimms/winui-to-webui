
# Import ingredients from aimmspy.
from aimmspy.project.project import Project, Model
from aimmspy.utils import find_aimms_path



def initialize_aimms_model( am_pn:str) -> Model:
    """
    Initialize and return an aimmspy Model object for the AIMMS project with name `am_pn` in the current working directory.
    
    :param am_pn: Name of the AIMMS project (without extension) to open.
    :type am_pn: str
    :return: Model handle created by aimmspy for interacting with the AIMMS project.
    :rtype: Model
    """
    aimms_project = Project(
        # path to the AIMMS Bin folder  
        aimms_path=find_aimms_path("26.2"), 

        # Path to the AIMMS project file .
        #aimms_project_file=projectfile,
        aimms_project_file = am_pn + ".aimms",
        #exposed_identifier_set_name = "meap.s_publicIdentifiers"
        exposed_identifier_set_name = "AllIdentifiers"  
    )
    aimms_model : Model = aimms_project.get_model(__file__)

    return aimms_model
