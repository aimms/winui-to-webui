import os
import sys
import pathlib
import winui_to_webui


def main_entry_point() -> None:
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
        # Libraries live at repo root, one level above py/
        tool_dir = pathlib.Path(__file__).parent.parent

    os.chdir(tool_dir)

    winui_to_webui.process_aimms_app(project_folder, project_name)


if __name__ == "__main__":
    main_entry_point()
