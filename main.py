import argparse
import io
import os
import sys
import pathlib
import winui_to_webui

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')


def main_entry_point() -> None:
    parser = argparse.ArgumentParser(description="Converts AIMMS WinUI to WebUI.")
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

    # Find the .aimms file in the current working directory
    cwd = pathlib.Path.cwd()
    aimms_files = list(cwd.glob("*.aimms"))

    if len(aimms_files) == 0:
        print("Error: No .aimms file found in the current directory.")
        sys.exit(1)
    if len(aimms_files) > 1:
        names = [f.name for f in aimms_files]
        print(f"Error: Multiple .aimms files found: {names}")
        sys.exit(1)

    project_name = aimms_files[0].stem
    project_folder = str(cwd)

    # winui_to_webui copies libraries relative to its own CWD, so switch to the
    # tool's directory before calling it (it will chdir to project_folder itself).
    if getattr(sys, 'frozen', False):
        # PyInstaller extracts bundled data to sys._MEIPASS, not next to the exe
        tool_dir = pathlib.Path(sys._MEIPASS)
    else:
        tool_dir = pathlib.Path(__file__).parent

    os.chdir(tool_dir)

    winui_to_webui.process_aimms_app(project_folder, project_name, page_name=args.page, new_color_set=args.newcolorset, colors=args.colors, network=args.network, diagram_spread=args.diagram_spread, share_layouts=args.share_layouts)


if __name__ == "__main__":
    main_entry_point()
