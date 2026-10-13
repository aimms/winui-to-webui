# /winscreenshots — Take WinUI page screenshots

Adds the WinScreenshots library to an AIMMS project, runs AIMMS to screenshot all WinUI pages, then reverts the project to its original state. Screenshots are kept in `winui_screenshots/`.

**AIMMS must be running on the primary monitor (monitor 1).**

## 1. Determine the project directory

- If the current working directory is inside the `711-winui-to-webui` repository (i.e. this skill's repository), ask the user for the path to the AIMMS project directory.
- Otherwise use the current working directory.

## 2. Find the .aimms file

Glob for `*.aimms` in the project directory (not recursive). There must be exactly one; report an error and stop if not.

## 3. Find the latest AIMMS installation

List subdirectories of `$env:LOCALAPPDATA\AIMMS\IFA\Aimms\`. Each folder name has the form `<major>.<minor>.<patch>.<build>-x64-<toolset>`. Sort by the numeric version tuple `(major, minor, patch, build)` and pick the highest. The executable is `<folder>\Bin\aimms.exe`.

## 4. Locate the support files

The support files live in the `winscreenshots/` folder at the root of this repository (the repository containing this skill at `.claude/commands/winscreenshots.md`).

## 5. Record the current state (needed for revert)

Note which of the following already exist in the project directory:
- `WinScreenshots/` folder
- `pyproject.toml`
- `pyaimms_bridge.py`
- `screenshot.py`
- `.python-version`
- `uv.lock`
- `.venv/`

Also save the full content of the `.aimms` file.

## 6. Modify the .aimms file

Add these two lines inside `<References>` just before `</References>`, unless they are already present:

```xml
	<RepositoryLibrary UUID="5A2255CE-23DB-4CB2-85F9-F62B349FE944" Name="pyaimms" Version="26.1.3.1" />
	<Library Path="WinScreenshots" />
```

## 7. Copy support files to the project directory

From `winscreenshots/` in this repository, copy to the project directory:
- `WinScreenshots/` → `<projectdir>/WinScreenshots/`
- `pyproject.toml` → `<projectdir>/pyproject.toml` (skip if it already existed)
- `pyaimms_bridge.py` → `<projectdir>/pyaimms_bridge.py`
- `screenshot.py` → `<projectdir>/screenshot.py`

## 8. Set up the Python environment

Run `uv sync` in the project directory.

## 9. Run AIMMS

Run the following command and wait for it to complete:

```
<aimms_exe> <path-to-.aimms-file> --maximize --run-only wss::pr_makeScreenshots
```

Screenshots are saved by AIMMS to `<projectdir>\winui_screenshots\`.

## 10. Revert the project

Restore the project exactly to the state recorded in step 5:
- Write back the original `.aimms` content saved in step 5.
- Remove `WinScreenshots/` (always added by this skill).
- Remove `pyaimms_bridge.py` and `screenshot.py` (always added).
- If `pyproject.toml` did not exist before: remove it, `uv.lock`, `.python-version`, and `.venv/`.
- If `pyproject.toml` already existed: leave it and `.venv/` alone.
- Remove `__pycache__/` if it was created.
- Remove `model_stub.py` and `model_stub.pyi` if they were created by this run.
- Do **not** remove `winui_screenshots/`.
