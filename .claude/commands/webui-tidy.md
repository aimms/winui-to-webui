# /webui-tidy [page1,page2,...|all] — Tidy up WebUI layout from WinUI screenshots

Uses WinUI screenshots and the preliminary `webui.json` to improve the WebUI layout for a selection of pages. Scope: partition axes, page layout (grid areas and column widths), and table column widths.

## 1. Determine the project directory

- If the current working directory is inside the `711-winui-to-webui` repository (i.e. this skill's repository), ask the user for the path to the AIMMS project directory.
- Otherwise use the current working directory.

## 2. Determine which pages to process

The argument is: `$ARGUMENTS`

- If the argument is `all`: process every page that has both a screenshot and a webui entry.
- If the argument is a comma-separated list of page names or slugs: process only those pages.
- If the argument is empty:
  1. Offer to list available pages (reading page slugs from `MainProject\WebUI\webui.json`). Ask: "Would you like to see the list of available pages first?"
  2. After the user responds (or declines), ask which pages to process.
  3. Warn the user that each page consumes a significant number of tokens, so be selective for large applications.

## 3. Locate inputs

- Screenshots: `<projectdir>\winui_screenshots\<page-name>.png` (the filename matches the page name as written by `wss::pr_makeScreenshots`).
- WebUI definition: `<projectdir>\MainProject\WebUI\webui.json`.

If a screenshot is missing for a requested page, warn and skip that page.

## 4. For each selected page

Read the screenshot and the relevant sections of `webui.json` for that page, then apply the following improvements:

### Partition axes
For each table widget on the page, inspect the screenshot to determine which identifiers should be row headers vs column headers. Update `contents.partition` accordingly:
- Use `rowHeader` for dimensions that appear as rows in the screenshot.
- Use `colHeader` for dimensions that appear as columns.
- Put `<IDENTIFIER-SET>` in `rowHeader` when multiple identifiers are stacked vertically, or in `colHeader` when stacked horizontally.

### Page layout
Design a CSS grid layout that matches the visual arrangement in the screenshot:
- Set `gridTemplateColumns` to reflect the relative widths of columns (e.g. `"3fr 1fr"`).
- Set `gridTemplateAreas` to reflect the positions of widgets.
- Assign each widget a `gridArea` in the page bindings.
- Use descriptive area names (e.g. `area-a`, `area-b`, or semantic names).

### Widget titles
Add or correct widget `title` properties to match labels visible in the screenshot.

## 5. Write the updated webui.json

Edit `MainProject\WebUI\webui.json` in place with the improvements for the selected pages. Leave all other pages and widgets untouched.

## 6. Report

Summarise the changes made per page: which widgets were adjusted and what changed.
