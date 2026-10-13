from aimmspy.project.project import Project, Model
from aimmspy.model.enums.data_return_types import DataReturnTypes

project : Project = Project(
    exposed_identifier_set_name = "AllIdentifiers",
    data_type_preference = DataReturnTypes.PANDAS
)

aimms_model : Model = project.get_model("model_stub.py")
