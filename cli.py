#import sys
import argparse
import winui_to_webui

def cli_entry_point() -> None:
    """
    Parse command-line arguments for headless conversion and invoke the WinUI-to-WebUI converter.
    
    :return: None. Parses CLI arguments and triggers conversion based on provided folder and project file.
    :rtype: None
    """
    parser = argparse.ArgumentParser(description="Converts AIMMS WinUI to WebUI.")

    # Define the required arguments for headless mode
    parser.add_argument('folder', type=str, help='The path to the AIMMS project.')
    parser.add_argument('file', type=str, help='The name of the aimms project file (without extension .aimms).')
    parser.add_argument('--page', type=str, default=None,
                         help='Name of a single WinUI page (PageManager.xml "Name" attribute) to convert. '
                              'When given, only that page is (re)converted; every other page already present '
                              'in the existing WebUI/webui.json files is left untouched.')
    parser.add_argument('--newcolorset', action='store_true',
                         help='Repoint every ElementParameter in the project whose Range is (case-insensitively) '
                              "AIMMS's built-in AllColors system set to the main model's own giim::s_AllColors "
                              'instead, not just the ones a converted widget actually references.')
    parser.add_argument('--colors', action='store_true',
                         help='Convert WinUI data coloring (table Colors, chart Color) into WebUI annotations '
                              'and a generated w2w-color.css. Off by default.')
    parser.add_argument('--network', choices=['map', 'diagram', 'auto', 'ignore'], default='auto',
                         help='How to convert a WinUI Network Object: map (Map widget, latitude/longitude), '
                              'diagram (Diagram widget, x/y), or auto (default): map when the object has a GIS '
                              'background or longitude/latitude coordinate names, otherwise diagram; '
                              'or ignore (no widget at all).')
    parser.add_argument('--diagram-spread', type=float, default=2.5, metavar='FACTOR',
                         help='Spread the nodes of a converted network diagram by FACTOR (default 2.5), '
                              'with the initial zoom at 1/FACTOR - more room between the node boxes. 1 = WinUI pixel size.')
    parser.add_argument('--share-layouts', action='store_true',
                         help='Let pages with the same custom grid shape share one layout. Off by default: every page '
                              'gets its own custom layout, so editing the layout of one page never changes another page. '
                              'A page matching a WebUI standard layout always uses that standard layout.')

    args = parser.parse_args()

    # Call the core logic function
    winui_to_webui.process_aimms_app(args.folder, args.file, page_name=args.page, new_color_set=args.newcolorset, colors=args.colors, network=args.network, diagram_spread=args.diagram_spread, share_layouts=args.share_layouts)
