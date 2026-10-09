#from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
import io
import os
import sys
#import lxml.etree as ET
#import pathlib
import winui_to_webui

# Matches main.py: without this, a print() containing a non-cp1252 character (e.g. an emoji
# warning marker) crashes once stdout/stderr is redirected to a file instead of a console.
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


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
    # Network Object examples - w2w0035: x/y coordinates (diagram), w2w0036: latitude/longitude (map):
    project_folder = os.path.join( 'examples', 'w2w0009', 'work' )
    project_name   = 'w2w0009'
 
    # 01datareconciliation does not have _Example Style Library, 02datareconciliation does.
    # project_folder = os.path.join( 'applications', '02datareconciliation', 'work' )
    # project_name   = 'Data Reconciliation'

    # project_folder = os.path.join( 'applications', '30jbs', 'work' )
    # project_name   = 'OCC'

    # project_folder = os.path.join( 'applications', '40rsc', 'work' )
    # project_name   = 'RSC'

    # project_folder = os.path.join( 'applications', '50NGMM_TO_AIMMS', 'work', 'models', 'main', 'aimms_endpoint' )
    # project_name   = 'aimms_endpoint'

    # Set to True to also repoint every ElementParameter in the project whose Range is
    # (case-insensitively) AIMMS's built-in AllColors system set to giim::s_AllColors instead,
    # not just the ones a converted widget actually references (see cli.py's --newcolorset).
    new_color_set = False # default False, alternative: True

    # Set to True to convert WinUI data coloring (table Colors, chart Color) into WebUI
    # annotations and a generated w2w-color.css (see cli.py's --colors).
    colors = False # default False, alternative: True

    # How a WinUI Network Object is converted (see cli.py's --network):
    # "auto" (map for a GIS background or longitude/latitude coordinate names, else diagram),
    # "map", "diagram", or "ignore" (no widget). Try it on examples w2w0035 (x/y) and w2w0036 (lat/lon).
    network = "auto" # alternatives: "map", "diagram", "ignore"

    # Spread of a converted network diagram's nodes (see cli.py's --diagram-spread); zoom starts at 1/spread.
    diagram_spread = 2.5 # 1 = WinUI pixel size

    # Set to True to let pages with the same grid shape share one layout (see cli.py's --share-layouts).
    share_layouts = False # default False, alternative: True

    # project_folder = 'C:\\u\\s\\work\\GE\\77888\\work'
    # project_folder = os.path.join( 'c:\\', 'u', 's', 'work', 'GE', '77888', 'work' )
    # project_name   = 'MCE'

    # G-AIMMS:
    # project_folder = os.path.join('applications', 'witch_apprentice_1a_GatheringIngredients', 'work' )
    # project_name   = 'GatheringIngredients'
    # project_folder = os.path.join('applications', 'witch_apprentice_1b_GatheringIngredients', 'work' )
    # project_name   = 'GatheringIngredientsSublevel'
    # project_folder = os.path.join('applications', 'witch_apprentice_2a_SpellAssignment', 'work' )
    # project_name   = 'SpellAssignment'
    # project_folder = os.path.join('applications', 'witch_apprentice_2b_SpellAssignment', 'work' )
    # project_name   = 'SpellAssignmentSublevel'
    # project_folder = os.path.join('applications', 'witch_apprentice_3a_HealingPotion', 'work' )
    # project_name   = 'HealingPotion'
    # project_folder = os.path.join('applications', 'witch_apprentice_3b_HealingPotion', 'work' )
    # project_name   = 'HealingPotionSublevel'

    # Launching customer:
    # project_folder = os.path.join('applications', 'jbs', 'work' )
    # project_name   = 'OCC'

    # The SHARC model.
    # project_folder = os.path.join('c:\\', 'ODOO', 'Shell', '73018', 'test', 'work' )
    # project_name   = 'FCC'

    winui_to_webui.process_aimms_app(project_folder, project_name, new_color_set=new_color_set, colors=colors, network=network, diagram_spread=diagram_spread, share_layouts=share_layouts)

if __name__ == "__main__":
    main_entry_point()
