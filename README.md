# AIMMS How-To: Convert WinUI to WebUI with `w2w`

This repository contains **`WinUI_to_WebUI`**, the command-line tool discussed in the following AIMMS How-To article. It converts an AIMMS WinUI project to WebUI: it reads the AIMMS project in the current folder and writes the WebUI output back into that same project.

👉 **[Read the Full Article: Convert WinUI to WebUI](https://how-to.aimms.com/Articles/711/711-winui-to-webui.html)**

1. Download or build `WinUI_to_WebUI.exe` (see [building.md](building.md)).
2. Place `WinUI_to_WebUI.exe` somewhere on your PATH, or note its location.
3. Open a terminal, navigate to your AIMMS project folder (the one containing the `.aimms` file), and run:

## 🎯 What It Does

Moving an existing application from WinUI to WebUI by hand means rebuilding every page, widget and layout. `w2w` automates the bulk of that work:
- Reads all WinUI pages of the project and generates the corresponding WebUI pages and widgets.
- Adds the identifiers the WebUI pages need to a generated module in the main model and in each library.
- Writes a conversion log (`<project>_conversion.md`) listing warnings and anything that could not be converted.

## 🚀 Getting Started

### Prerequisites
- **AIMMS 26.8** installed, and a WinUI project to convert.
- **`WinUI_to_WebUI.exe`:** build it from source (see [building.md](building.md)) or obtain a copy from the AIMMS User Support Team.
- **A backup:** `WinUI_to_WebUI` modifies files inside your project folder. Commit your project to source control (or copy the folder) before running it.

### Running a conversion
1. **Install:** Place `WinUI_to_WebUI.exe` somewhere on your PATH, or note its location.
2. **Open:** Open a terminal in your AIMMS project folder (the one containing exactly one `.aimms` file).
3. **Convert:** Run:
   ```
   WinUI_to_WebUI
   ```
4. **Review:** Inspect the changes in your source control diff and read the conversion log.

See [usage.md](usage.md) for the full guide, including options such as converting a single page (`--page`) or data coloring (`--colors`), and the list of error messages.

## 🛠️ For Developers

### Repository layout

```
<<<<<<< HEAD
py/                          Python source code
GeneratedInterfaceIdentifiersLibrary/   \  bundled into WinUI_to_WebUI.exe at build time;
ModelEditAimmsPython/                   /  copied into each project during conversion
w2w.spec                     PyInstaller build spec
building.md                  How to build WinUI_to_WebUI.exe from source
usage.md                     How to use WinUI_to_WebUI.exe
=======
*.py                    Python source code (entry point: main.py)
ModelEditAimmsPython/   AIMMS library bundled into w2w.exe; copied into the project during a conversion
scripts/                Build (build_w2w.ps1, clean_w2w.ps1) and example-run scripts
w2w.spec                PyInstaller build spec
building.md             How to build w2w.exe from source
usage.md                How to use w2w.exe
>>>>>>> fa341d3dcc9adace7bc4b5b5dd87c288d4df5508
```

### Examples

The example projects live in a separate (AIMMS-internal) Git repository, which this repository does not track (`/examples/` is git-ignored). Clone it into the repository root:

```
git clone git@gitlab.aimms.com:aimms/user-support/customer-support/ChrisKuip/nirvana/0287-w2w-examples.git examples
```

## 🤝 Support & Feedback

This tool is maintained by the **AIMMS User Support Team**.
- Found an issue? [Open an issue](https://github.com/aimms/711-winui-to-webui/issues).
- Questions? Reach out via the [AIMMS Community](https://community.aimms.com).

---
*Maintained by the AIMMS User Support Team. We optimize the way you build optimization.*
