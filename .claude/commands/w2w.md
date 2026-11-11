# /w2w — Convert WinUI project to WebUI

Runs `WinUI_to_WebUI.exe` on an AIMMS project to generate a preliminary `webui.json`. Assumes `WinUI_to_WebUI.exe` is on the PATH.

**Before running: make sure the project is committed or backed up — w2w writes directly into the project folder.**

## 1. Determine the project directory

- If the current working directory is inside the `711-winui-to-webui` repository (i.e. this skill's repository), ask the user for the path to the AIMMS project directory.
- Otherwise use the current working directory.

## 2. Find the .aimms file

Glob for `*.aimms` in the project directory (not recursive). There must be exactly one; report an error and stop if not.

## 3. Run WinUI_to_WebUI

```
cd <projectdir>
WinUI_to_WebUI
```

Wait for it to complete. Progress is printed to the console. Warnings are non-fatal; an error with a non-zero exit code means the conversion failed.

## 4. Report

Tell the user what was produced: the location of the updated `MainProject\WebUI\webui.json` (and any sub-library equivalents mentioned in the output).
