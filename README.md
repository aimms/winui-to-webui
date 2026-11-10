# w2w — WinUI to WebUI Converter

`w2w` is a command-line tool that converts an AIMMS WinUI project to WebUI.
It reads the AIMMS project in the current directory and writes the WebUI output back into that same project.

## Quick start

1. Download or build `WinUI_to_WebUI.exe` (see [building.md](building.md)).
2. Place `WinUI_to_WebUI.exe` somewhere on your PATH, or note its location.
3. Open a terminal, navigate to your AIMMS project folder (the one containing the `.aimms` file), and run:
   ```
   WinUI_to_WebUI
   ```

See [usage.md](usage.md) for full instructions, including the backup requirement.

## Repository layout

```
py/                          Python source code
GeneratedInterfaceIdentifiersLibrary/   \  bundled into WinUI_to_WebUI.exe at build time;
ModelEditAimmsPython/                   /  copied into each project during conversion
w2w.spec                     PyInstaller build spec
building.md                  How to build WinUI_to_WebUI.exe from source
usage.md                     How to use WinUI_to_WebUI.exe
```

## Examples

The example projects live in a separate git repository, which this repository does not track (`/examples/` is git-ignored). Clone it into the repository root:

```
git clone git@gitlab.aimms.com:aimms/user-support/customer-support/ChrisKuip/nirvana/0287-w2w-examples.git examples
```

## Support & Feedback

This tool is maintained by the **AIMMS User Support Team**.

- Found an issue? [Open an issue](../../issues).
- Questions? Reach out via the [AIMMS Community](https://community.aimms.com).

---
*Maintained by the AIMMS User Support Team. We optimize the way you build optimization.*
