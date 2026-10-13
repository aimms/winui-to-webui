# Using w2w — Practical Guide

`w2w` converts an AIMMS WinUI project to WebUI. It reads the project in its current folder and writes the WebUI output back into that same folder.

## Prerequisites

- `w2w.exe` — obtain a copy from your team or build it from source (see [building.md](building.md))
- AIMMS 26.6 installed — `w2w` opens the project with the latest installed 26.6.x
- A project without WebUI gets the WebUI repository library 26.12.5.5 added; a project that already references WebUI keeps its own version

## Before you start: back up your project

**w2w modifies files inside your AIMMS project folder.** It adds two support libraries and writes WebUI output directly into the project. Make sure you have a safe copy before running it.

The recommended approach is to work from a source-controlled repository (Git or otherwise). Commit or stash your current state before running the conversion, so you can review the changes and roll back if needed.

If you are not using source control, make a manual backup of the entire project folder first.

## Running a conversion

1. Open a terminal (Command Prompt or PowerShell).
2. Navigate to the folder that contains your `.aimms` project file:
   ```
   cd C:\path\to\your\project
   ```
3. Run the tool:
   ```
   w2w
   ```

The tool will:
- Detect the `.aimms` file in the current folder automatically.
- Copy two support libraries (`GeneratedInterfaceIdentifiersLibrary`, `ModelEditAimmsPython`) into the project.
- Process all WinUI pages and write the corresponding WebUI output.

Progress is printed to the console. A successful run may include `Warning:` lines for non-fatal issues (e.g. a PageManager.xml that could not be parsed); these are reported but do not stop the conversion. A run that is fatally blocked will print an error and exit with a non-zero code.

## Converting a single page

By default `w2w` rebuilds the entire `webui.json` for every component from scratch, discarding any manual edits made in the WebUI editor. To iterate on one page without disturbing the rest of an already-converted, hand-tuned WebUI, pass `--page`:

```
w2w --page pageName
```

`pageName` must match the `Name` attribute of the page in `PageManager.xml` (the same name used for its `Pages\<pageName>.xml` file) — not the WebUI slug.

Only that page's entry (and its widgets) in `webui.json` is replaced; every other page already present on disk is left byte-for-byte unchanged, including any manual layout/widget edits made in the WebUI editor. If a component (the main model or a library) doesn't have a `webui.json` yet but does have pages of its own (a non-empty `Pages` folder), it still gets a fresh base `webui.json` created — with no pages converted into it — so the overall multi-component WebUI stays coherent even though only one page is being converted right now. If the requested page isn't found in any component, the tool exits with an error and doesn't touch any file.

Note: the tool still processes every page internally on each run (needed to keep the generated identifier library consistent for all pages), so this does not meaningfully speed up the run — it only limits what gets written to `webui.json`.

## Converting data coloring

WinUI data coloring (a table's `Colors`/`Background_Color`, a chart's `Color`) is **not** converted by default: the generated stylesheet still colors widgets that don't use coloring, so it is opt-in for now. To convert it, pass `--colors`:

```
w2w --colors
```

This turns each coloring into a `webui::AnnotationsIdentifier` on the colored identifier, creates the `giim::s_AllColors` color set (with `p_Red`/`p_Green`/`p_Blue`/`p_ColorSlug`), and writes `WebUI\resources\css\w2w-color.css` in the main model. Without `--colors`, none of this is generated, and a `w2w-color.css` left behind by an earlier `--colors` run is removed. Can be combined with `--page` and `--newcolorset`.

## Converting network objects

A WinUI Network Object becomes either a WebUI **Map** widget (nodes placed by latitude/longitude) or a WebUI **Diagram** widget (nodes placed by x/y). Choose with `--network`:

```
w2w --network=auto
w2w --network=map
w2w --network=diagram
w2w --network=ignore
```

`auto` (the default) decides per Network Object:

1. a GIS background (shapefile layers) in the WinUI object → **map**;
2. otherwise, node coordinates whose names read as longitude (X) and latitude (Y), e.g. `p_Longitude( i )` / `Latitude_center( r )` → **map**;
3. otherwise → **diagram**.

`map` and `diagram` force that widget for every Network Object converted in the run. `ignore` converts no Network Object at all - they get no widget and take no space in the page's grid (their number is reported at the end of the conversion log). The choice and its reason are recorded per object in `<project>_conversion.md`.

To mix choices within one project, combine `--network` with `--page`: convert the whole project once with the default, then reconvert an individual page whose Network Object should be the other widget, e.g. `w2w --page "Network Tie Flows" --network=map`. Only that page is rewritten in `webui.json`.

Notes:

- A WebUI Diagram currently supports one arc set per widget. Only the first arc set of a Network Object is converted to a diagram; the others are listed in the conversion log.
- Diagram coordinates are rescaled from the WinUI visible area to a drawing space the size of the WinUI object times `--diagram-spread` (default 2.5), with the Y axis flipped; the diagram's initial zoom is 1/spread. WebUI draws each node as a labelled box, much larger than WinUI's dot, so the spread gives them room - e.g. `w2w --diagram-spread 4` for more, `--diagram-spread 1` for WinUI's own pixel size. This is done by generated parameters (`p_diagram_x_…`/`p_diagram_y_…`) in the generated interface module.
- GIS background layers, node/arc sizes, shapes and colors are not converted.
- When the WinUI visible area is computed at run time, the map's bounds are left unset (see the conversion log).

## Sharing page layouts

A page whose grid matches one of WebUI's standard layouts uses that standard layout. Every other page gets its own custom grid layout by default, so editing one page's layout in the WebUI editor never changes another page. To let pages with the same custom grid shape share one layout instead, pass `--share-layouts`:

```
w2w --share-layouts
```

Sharing keeps `webui.json` smaller, but then a layout edit on one page shows up on every page that shares it.

## Repointing AllColors element parameters

AIMMS's built-in `AllColors` system set isn't usable as-is by WebUI. Normally, `w2w` only repoints the `Range` of an identifier ranged over `AllColors` to its own generated `giim::s_AllColors` set when that identifier is actually used for data coloring by a converted widget (so only with `--colors`).

To instead repoint *every* `ElementParameter` anywhere in the project whose `Range` is (case-insensitively) `AllColors` — including ones no converted widget currently references — pass `--newcolorset`:

```
w2w --newcolorset
```

This can be combined with `--page`. It's off by default since it touches identifiers outside anything the current conversion run itself needs.

## Requirements for the project folder

- The folder must contain exactly one `.aimms` file.
- If there are zero or more than one `.aimms` files, the tool will report an error and stop.

## After the conversion

Review the changes in your source control diff, or compare manually against your backup. The key output is `MainProject\WebUI\webui.json` (and equivalent files for any sub-libraries in the project).

## Errors

| Message | Cause |
|---|---|
| `No .aimms file found in the current directory` | Run `w2w` from the folder that contains the `.aimms` file |
| `Multiple .aimms files found` | The folder contains more than one `.aimms` file; remove or move the extras |
| `Project folder '...' does not exist` | Internal error — the detected path no longer exists |
