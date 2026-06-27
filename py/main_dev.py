#from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
import os
#import lxml.etree as ET
#import pathlib
import winui_to_webui


def main_entry_point() -> None:
    """
    Launch the WinUI-to-WebUI conversion in interactive mode using predefined example project paths.

    :return: None. Sets the project folder/name and triggers the conversion workflow.
    :rtype: None
    """
    # # Change the current working directory to the script's directory
    # script_dir = os.path.dirname(os.path.abspath(__file__))
    # os.chdir(script_dir)
    # EXAMPLES_DIR = pathlib.Path(__file__).parent.parent / "examples"

    # take an example
    project_folder = os.path.join( 'examples', 'w2w0001', 'work' )
    project_name   = 'w2w0001'

    # Just test a specific project.
    # project_folder = os.path.join( 'tests', 'w2w0001', 'work' )
    # project_name   = 'w2w0001'

    # G-AIMMS:
    # project_folder = os.path.join('applications', '0293witchapprentice', 'WitchsApprentice', 'Level 1 - GatheringIngredients' )
    # project_name   = 'GatheringIngredients'
    # project_folder = os.path.join('applications', '0293witchapprentice', 'WitchsApprentice', 'Level 1b - GatherIngredients' )
    # project_name   = 'GatheringIngredientsSublevel'
    # project_folder = os.path.join('applications', '0293witchapprentice', 'WitchsApprentice', 'Level 2 - SpellAssignment' )
    # project_name   = 'SpellAssignment'
    # project_folder = os.path.join('applications', '0293witchapprentice', 'WitchsApprentice', 'Level 2b - SpellAssignment' )
    # project_name   = 'SpellAssignmentSublevel'
    # project_folder = os.path.join('applications', '0293witchapprentice', 'WitchsApprentice', 'Level 3 - HealingPotion' )
    # project_name   = 'HealingPotion'
    # project_folder = os.path.join('applications', '0293witchapprentice', 'WitchsApprentice', 'Level 3b - HealingPotion' )
    # project_name   = 'HealingPotionSublevel'


    # Launching customer:
    # project_folder = os.path.join('applications', 'jbs', 'work' )
    # project_name   = 'OCC'

    # The SHARC model.
    # project_folder = os.path.join('c:\\', 'ODOO', 'Shell', '73018', 'test', 'work' )
    # project_name   = 'FCC'

    winui_to_webui.process_aimms_app(project_folder, project_name)

if __name__ == "__main__":
    main_entry_point()
