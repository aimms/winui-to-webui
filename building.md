# Building w2w from Source

These instructions produce `dist\w2w.exe` — a self-contained Windows executable that requires no Python installation to run.

## Prerequisites

- Python 3.13 or later (system-wide install, not a venv)
- The following packages installed in that Python environment:

  ```
  pip install pyinstaller lxml aimmspy python-slugify PySide6 pandas
  ```

  Alternatively, use the requirements file:

  ```
  pip install -r py/requirements.txt
  ```

- The repository cloned locally

## Build steps

1. Open a terminal and navigate to the repository root:
   ```
   cd C:\path\to\711-winui-to-webui
   ```

2. Delete any previous build output to ensure a clean build:
   ```
   Remove-Item -Recurse -Force build, dist
   ```

3. Run PyInstaller with the provided spec file:
   ```
   pyinstaller w2w.spec
   ```

4. The executable is written to:
   ```
   dist\w2w.exe
   ```

## What the build bundles

`w2w.spec` configures PyInstaller to:
- Include all local conversion modules from `py/` as hidden imports
- Bundle `GeneratedInterfaceIdentifiersLibrary` and `ModelEditAimmsPython` as data — these are copied into each AIMMS project at conversion time
- Produce a single-file executable

## Notes

- Always delete `build\` and `dist\` before rebuilding after installing or upgrading any dependency. PyInstaller caches aggressively and will silently use the old bundle otherwise.
- The spec file pins the entry point to `py/main.py`. If this changes, update `w2w.spec` accordingly.
- `py/main_dev.py` is a development entry point with hardcoded example paths and is not part of the build.
