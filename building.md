# Building w2w from Source

These instructions produce `dist\w2w.exe`, a single-file Windows executable that runs without a Python installation.

## Prerequisites

- **Windows** with PowerShell.
- **[uv](https://docs.astral.sh/uv/)** on your PATH. The build script uses it to create the project's `.venv` with the right Python (3.14, see `.python-version`) and the dependencies pinned in `uv.lock`.
- **The repository** cloned locally.

You do not need to install Python packages yourself.

## Build

From the repository root:

```
.\scripts\clean_w2w.ps1
.\scripts\build_w2w.ps1
```

The executable is written to `dist\w2w.exe`.

`build_w2w.ps1`:
1. Runs `uv sync` to create or update `.venv` from `pyproject.toml` and `uv.lock`.
2. Installs PyInstaller into `.venv` if it is missing (a build-only tool, not a project dependency). Pass `-SkipDependencyCheck` to skip this check.
3. Runs PyInstaller with `w2w.spec`, using the `.venv` Python.

`clean_w2w.ps1` removes `build\` and `dist\`. Run it before every build after adding or upgrading a dependency: PyInstaller caches aggressively and otherwise silently reuses the old bundle.

## Why the .venv matters

The executable must be built with the Python that has the runtime dependencies (`aimmspy`, `lxml`, `pandas`, `PySide6`, ...). Building with a Python that lacks `aimmspy` still succeeds, but the resulting exe fails every conversion with `ModuleNotFoundError: No module named 'aimmspy'`. The build script avoids this by always using the project's `.venv`.

## What the build bundles

`w2w.spec` configures PyInstaller to:
- Use `main.py` as the entry point.
- Include all conversion modules as hidden imports. When you add a new module, add it to `hiddenimports` in `w2w.spec`.
- Bundle `ModelEditAimmsPython` (copied into each project during a conversion) and `w2w-colors.template.css` as data.
- Produce a single-file console executable.

## Running from source

To run the converter without building the exe, use the `.venv` from the repository root and start it from your AIMMS project folder:

```
cd C:\path\to\your\project
C:\path\to\711-winui-to-webui\.venv\Scripts\python.exe C:\path\to\711-winui-to-webui\main.py
```

`main_dev.py` is a development entry point with hardcoded example paths; it is not part of the build.
