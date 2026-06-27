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

    args = parser.parse_args()

    # Call the core logic function
    winui_to_webui.process_aimms_app(args.folder, args.file)
