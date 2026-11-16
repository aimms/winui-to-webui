# WinUI to WebUI Converter

[![Downloads](https://img.shields.io/github/downloads/aimms/winui-to-webui/total?style=for-the-badge&logo=github&labelColor=000081&color=1847c9)](https://github.com/aimms/winui-to-webui/releases)


This repository contains an AIMMS toolkit: **WinUI to WebUI Converter**. It converts the WinUI pages of an AIMMS project into WebUI pages and widgets, and writes a log of what it could not convert.

## 🔧 What This Toolkit Solves

Moving an existing application from WinUI to WebUI by hand means rebuilding every
page, widget and layout, and adding the identifiers each WebUI page needs.

This toolkit reads the WinUI pages of the project in the current folder and writes the
WebUI pages and widgets back into it. It adds the identifiers they need to a generated
module in the main model and in each library, and writes a conversion log with warnings
and the objects it could not convert.

## 📖 How to Use This Toolkit

To get the most out of this toolkit, we highly recommend reading our detailed step-by-step
guide on the AIMMS How-To website:

👉 **[Read the Full Article: Convert WinUI to WebUI](https://how-to.aimms.com/Articles/711/711-winui-to-webui.html)**

### Prerequisites
- **AIMMS**: You will need AIMMS installed to run the model. [Download the Free Academic Edition here](https://www.aimms.com/support/licensing/).
- **WebUI:** this toolkit runs in the AIMMS WebUI, for a modern, browser-based experience.
- **A WinUI project and a backup:** the tool modifies files inside your project folder, so commit it to source control or copy the folder before running it.

## 🚀 Getting Started

1. **Download the Release:** Go to the [Releases](https://github.com/aimms/winui-to-webui/releases) page and download the `.zip` file from the latest version.
2. **Open the Project:** Launch the `.aimms` file.
3. **Convert:** open a terminal in the folder with your `.aimms` file and run `WinUI_to_WebUI`.
4. **Review:** read the conversion log `<project>_conversion.md` and check the changes in your source control diff.

## 🤝 Support & Feedback

This toolkit is maintained by the **AIMMS User Support Team**.
- Found an issue? [Open an issue](https://github.com/aimms/winui-to-webui/issues).
- Questions? Reach out via the [AIMMS Community](https://community.aimms.com).

---
*Maintained by the AIMMS User Support Team. We optimize the way you build optimization.*
