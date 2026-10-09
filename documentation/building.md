# Building w2w from Source

These instructions produce `dist\w2w.exe` — a self-contained Windows executable that requires no Python installation to run.

## Prerequisites

- [uv](https://docs.astral.sh/uv/) installed
- The repository checked out locally, with its `.venv` set up (`uv sync`) — this already has `lxml`, `aimmspy`, `python-slugify`, `PySide6`, and `pandas` per `pyproject.toml`
- `pyinstaller` added to that same `.venv`:

  ```
  uv pip install pyinstaller
  ```

Building from the project's own `.venv` (rather than a system-wide Python) keeps the build reproducible and matches how the project is normally run/tested (`uv run ...`, `scripts/run_example.py`, etc.).

## Quick build

```
.\scripts\clean_w2w.ps1
.\scripts\build_w2w.ps1
```

`build_w2w.ps1` runs `uv sync` first, so a missing or out-of-date `.venv` is created/updated automatically, and installs PyInstaller into it if needed. The manual steps below do the same thing by hand.

## Build steps

1. Open a terminal and navigate to the repository root:
   ```
   cd C:\path\to\0287-w2wpy
   ```

2. Delete any previous build output to ensure a clean build:
   ```
   Remove-Item -Recurse -Force build, dist
   ```

3. Run PyInstaller with the provided spec file, via `uv run` so it uses the project's `.venv`:
   ```
   uv run pyinstaller w2w.spec
   ```

4. The executable is written to:
   ```
   dist\w2w.exe
   ```

A `WARNING: Hidden import "jinja2" not found!` during the build is expected/harmless — nothing on `w2w`'s code paths uses it.

## What the build bundles

`w2w.spec` configures PyInstaller to:
- Include all local conversion modules as hidden imports
- Bundle `GeneratedInterfaceIdentifiersLibrary` and `ModelEditAimmsPython` as data — these are copied into each AIMMS project at conversion time
- Produce a single-file executable (`--onefile` equivalent)

## Notes

- Always delete `build\` and `dist\` before rebuilding after installing or upgrading any dependency. PyInstaller caches aggressively and will silently use the old bundle otherwise.
- The spec file pins the entry point to `main.py`. If `main.py` is replaced or renamed, update `w2w.spec` accordingly.
- `main_dev.py` is the original development entry point (hardcoded example paths) and is not included in the build.
