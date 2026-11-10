# Using w2w — Practical Guide

`w2w` converts an AIMMS WinUI project to WebUI. It reads the project in its current folder and writes the WebUI output back into that same folder.

## Prerequisites

- `WinUI_to_WebUI.exe` — obtain a copy from your team or build it from source (see [building.md](building.md))
- AIMMS model in AIMMS 25.9

## Before you start: back up your project

**w2w modifies files inside your AIMMS project folder.** It adds two support libraries and writes WebUI output directly into the project. Make sure you have a safe copy before running it.

The recommended approach is to work from a source-controlled repository (Git or otherwise). Commit or stash your current state before running the conversion, so you can review the changes and roll back if needed.

If you are not using source control, make a manual backup of the entire project folder first.

## Running a conversion

1. Open a terminal (Command Prompt or PowerShell).
2. Navigate to the folder that contains your `.aimms` project file:
   ```
   cd C:\path\to\your\project
   ```
3. Run the tool:
   ```
   WinUI_to_WebUI
   ```

The tool will:
- Detect the `.aimms` file in the current folder automatically.
- Copy two support libraries (`GeneratedInterfaceIdentifiersLibrary`, `ModelEditAimmsPython`) into the project.
- Process all WinUI pages and write the corresponding WebUI output.

Progress is printed to the console. A successful run may include `Warning:` lines for non-fatal issues (e.g. a PageManager.xml that could not be parsed); these are reported but do not stop the conversion. A run that is fatally blocked will print an error and exit with a non-zero code.

## Requirements for the project folder

- The folder must contain exactly one `.aimms` file.
- If there are zero or more than one `.aimms` files, the tool will report an error and stop.

## After the conversion

Review the changes in your source control diff, or compare manually against your backup. The key output is `MainProject\WebUI\webui.json` (and equivalent files for any sub-libraries in the project).

## Errors

| Message | Cause |
|---|---|
| `No .aimms file found in the current directory` | Run `WinUI_to_WebUI` from the folder that contains the `.aimms` file |
| `Multiple .aimms files found` | The folder contains more than one `.aimms` file; remove or move the extras |
| `Project folder '...' does not exist` | Internal error — the detected path no longer exists |
