# Upgrade guide for a single AIMMS WinUI application to an AIMMS WebUI application

Manual cleanup is still required after the automated conversion. Use this checklist to minimize surprises.

## Prep

1. Upgrade the AIMMS project to AIMMS 25.4 or newer. The converter depends on aimmspy fixes in 25.4+.
2. Ensure the AIMMS project can be started headless; aimmspy is used and this requires startup without user interaction.
3. If the AIMMS project already includes WebUI, ensure the WebUI version is 25.4+ for required fixes.
4. Every library that contains identifiers in UI expressions, or identifiers used in non-trivial action sequences needs to include all identifiers referenced in the interface. Practically: Open up the interface completely for all libraries, and undo this in the wrapup - see wehere the compiler errors occur.
5. Remove obsolete WinUI pages before converting. Every WinUI page is carried into `webui.json`, and each generated WebUI page needs review—so unused pages waste effort.

## Run the converter

Use the documented tool flow (GUI or CLI) to run WinUI→WebUI on the project.

## Finalize manually

### Visual review

- Choose [layouts per page](https://documentation.aimms.com/webui/webui-grid-pages.html#page-manager-with-grid-pages).
- Rebuild pivoting for pivot tables. For WinUI Pivot tables, pivoting is stored in Aimms state files and is not extracted by the converter.

### Review the conversion log

- The tool writes `<project_name>_conversion.md` with follow-up actions. Work through the listed items.

### Update UI interaction code

- WinUI dialogs are synchronous: prepare data → open dialog → handle input in one procedure.
- WebUI dialogs are asynchronous: in the starter procedure, prepare data and open the dialog with a callback; in the callback, check which button was used (OK/Cancel) and process the input.
- Rework any WinUI-only UI calls. [Available functions](https://documentation.aimms.com/functionreference/user-interface-related-functions/index.html).

### Undo unnecessary opening of interfaces of libraries

Libraries with adapted interface, should get their original interface restored.

It may happen that compiler errors occur in GeneratedInterfaceIdentifiersLibrary. Handle these as needed.