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

- Screenshots: `<projectdir>\winui_screenshots\<page-name>.png` (the filename matches the page name as written by `wss::pr_makeScreenshots`). Extra screenshots for pages that were missing may be in a sibling folder such as `winui_screenshot_2`; ask when a page has none.
- WebUI definition: `<projectdir>\MainProject\WebUI\webui.json`.

If a screenshot is missing for a requested page, warn and skip that page.

Before writing, check that AIMMS is closed: no `aimms.exe` process and no `*.aimmslockfile` in the project folder.

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

### Keep the layout simple
The user prefers a simple, stacked layout that is comfortable to read over a pixel copy of the WinUI page.
- Stack tables in one column (`1fr`, rows `1fr 11fr 11fr`) when that reads well; use two columns only for tables that sit side by side in WinUI.
- Merge empty grid areas and drop their items; every area must be a rectangle.
- Reuse an existing layout when it fits; rewrite an own layout in place or delete it when it becomes unused.
- A scalar title bar with several selectors and add buttons gets crowded: use two rows, the selector in the top row and its small add button directly below, one column per selector, a selector without button (e.g. a unit selector) last.
- Row gap is about 20 px, so areas that must look equal need equal row counts.

### Column widths
Set `custom.column.widths` for the row header (`type: rowHeader`, `colKey` = the partition entry, `width` about 20-26) and `default.column.width` (about 14-28, wider for text columns) so headers and values are readable. Do not touch the partition when it already matches the screenshot.

### Display Domain
A column or table that shows nothing in WebUI while WinUI shows empty rows needs `displaydomain` = `"1"` on its identifiers (a free index left for the rows makes this safe). Apply the rules of `/webui-displaydomain` for every table you tidy, one page at a time, and say so in the report. The user checks at least `fuel_types`-like pages: every identifier of every table.

### Widget titles
Add or correct widget `title` properties to match labels visible in the screenshot. Shorten generated titles such as `Startup Fuel Cost (ue,fh)` to the label WinUI shows.

## 5. Write the updated webui.json

Edit `MainProject\WebUI\webui.json` in place with the improvements for the selected pages. Leave all other pages and widgets untouched. Edit by text-level insertion/replacement that keeps AIMMS's CRLF formatting, not by re-serializing the JSON, then verify the file parses and the diff contains only the planned changes.

## 6. Report

Summarise the changes made per page: which widgets were adjusted and what changed.

Then ask the user to open the pages in AIMMS and give feedback before the next batch (work by workflow tab). Pages are committed one per commit, only on request; AIMMS re-save noise (Options.txt, Rsc.ams, reordered keys) stays out of the commits.
