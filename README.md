<p align="center"><img src="./.assets/banner.png" alt="aimms toolkit: Operating WinUI_to_WebUI" width="100%"></p>

# Operating WinUI_to_WebUI

[![Downloads](https://img.shields.io/github/downloads/aimms/winui-to-webui/total?style=for-the-badge&logo=github&labelColor=0B0B0C&color=2B37C9)](https://github.com/aimms/winui-to-webui/releases)

This repository contains an aimms toolkit: **Operating WinUI_to_WebUI**. It converts the WinUI pages of an aimms project into WebUI pages and widgets, and writes a log of what it could not convert.

## What this toolkit solves

Moving an application from the aimms WinUI to the aimms WebUI by hand means rebuilding every
page, widget and layout, and adding the identifiers each WebUI page needs.

This toolkit reads the WinUI pages of the project in the current folder and writes the
WebUI pages and widgets back into it. It adds the identifiers they need to a generated
module in the main model and in each library, and writes a conversion log with the
objects it could not convert, so you know what to finish by hand.

## How to use this toolkit

To get the most out of this toolkit, we highly recommend reading our detailed step-by-step guide on the aimms How-to website:

**[Read the full article: Operating WinUI_to_WebUI](https://how-to.aimms.com/Articles/711/711-operating-winui-to-webui-converter.html)**

### Prerequisites

- **Windows:** `WinUI_to_WebUI.exe` is a Windows executable. No Python installation is needed.
- **aimms Developer 26.8** with a license: the converter opens your project with aimms. Tested with aimms 26.8.1.2. [Licensing](https://www.aimms.com/support/licensing/).
- **A WinUI project and a backup:** the tool modifies files inside your project folder, so commit it to source control or copy the folder before you run it.

## Getting started

1. **Download the release:** go to the [Releases](https://github.com/aimms/winui-to-webui/releases) page, download the `.zip` file from the latest version, and unpack it. It contains `WinUI_to_WebUI.exe`.
2. **Back up your project:** commit it to source control, or copy the project folder.
3. **Convert:** open a terminal in the folder with your `.aimms` file and run `WinUI_to_WebUI`.
4. **Review:** read the conversion log `<project>_conversion.md`, and check the changes in your source control diff.

## Support and feedback

This toolkit is maintained by the **aimms User Support Team**.

- Found an issue? [Open an issue](https://github.com/aimms/winui-to-webui/issues).
- Questions? Reach out via the [aimms Community](https://community.aimms.com).

---

<sub>Maintained by the aimms User Support Team. We optimize the way you build optimization.</sub>
