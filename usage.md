# Using w2w

`w2w` converts an AIMMS WinUI project to WebUI. It reads the project in the current folder and writes the WebUI output back into that same folder.

## Prerequisites

- **`w2w.exe`:** build it from source (see [building.md](building.md)) or obtain a copy from the AIMMS User Support Team.
- **AIMMS 26.6:** `w2w` opens the project with the latest installed AIMMS 26.6.x.
- **WebUI library:** a project that already references WebUI keeps its own version. A project without WebUI gets the WebUI repository library 26.12.5.5 added.

## Before you start: back up your project

**`w2w` modifies files inside your AIMMS project folder.** It adds generated identifiers to your model and writes the WebUI output directly into the project.

The recommended approach is to work from a source-controlled repository (Git or otherwise). Commit or stash your current state before running the conversion, so you can review the changes and roll back if needed. If you are not using source control, copy the entire project folder first.

## Running a conversion

1. Open a terminal (Command Prompt or PowerShell).
2. Go to the folder that contains your `.aimms` file:
   ```
   cd C:\path\to\your\project
   ```
   The folder must contain exactly one `.aimms` file.
3. Run the tool:
   ```
   w2w
   ```

The tool will:
- Detect the `.aimms` file in the current folder.
- Add the `AimmsPro` system library and the WebUI repository library, if the project does not reference them yet.
- Convert all WinUI pages and write the WebUI output for the main model and every library that has pages.
- Add the identifiers the WebUI pages need to a generated module in each component (`GeneratedInterfaceIdentifiersMain`, prefix `giim`, in the main model; `GeneratedInterfaceIdentifiersLibrary`, prefix `giil`, in each library).

During the run it temporarily copies the `ModelEditAimmsPython` library into the project and removes it again at the end.

Progress is printed to the console. `Warning:` lines report non-fatal issues (e.g. a `PageManager.xml` that could not be parsed); they do not stop the conversion. A fatal problem prints an error and exits with a non-zero code.

## After the conversion

Review the changes in your source control diff, or compare against your backup:

- `MainProject\WebUI\webui.json` (and the equivalent file for each library with pages) holds the converted pages.
- `<project>_conversion.md` is the conversion log: warnings, objects that were not converted, and the choices made per object.

## Options

| Option | Effect |
|---|---|
| `--page <name>` | Convert a single page; leave every other page in `webui.json` untouched. |
| `--colors` | Convert WinUI data coloring. Off by default. |
| `--network=auto\|map\|diagram\|ignore` | How to convert Network Objects. Default `auto`. |
| `--diagram-spread <factor>` | Spacing of nodes in a converted network diagram. Default `2.5`. |
| `--share-layouts` | Let pages with the same custom grid shape share one layout. |
| `--newcolorset` | Repoint every element parameter ranged over `AllColors`, not only the ones used for coloring. |

Run `w2w --help` for the built-in summary. Each option is described below.

### Converting a single page

By default `w2w` rebuilds the entire `webui.json` of every component from scratch, discarding any manual edits made in the WebUI editor. To iterate on one page without disturbing the rest of an already converted, hand-tuned WebUI, pass `--page`:

```
w2w --page pageName
```

`pageName` must match the `Name` attribute of the page in `PageManager.xml` (the same name used for its `Pages\<pageName>.xml` file), not the WebUI slug.

- Only that page's entry (and its widgets) in `webui.json` is replaced. Every other page already on disk stays byte-for-byte unchanged, including manual layout and widget edits.
- A component (the main model or a library) that has pages but no `webui.json` yet still gets a fresh base `webui.json`, with no pages converted into it, so the multi-component WebUI stays coherent.
- If the page is not found in any component, the tool exits with an error and does not touch any file.

The tool still processes every page internally (to keep the generated identifiers consistent for all pages), so `--page` does not make the run much faster. It only limits what is written to `webui.json`.

### Converting data coloring

WinUI data coloring (a table's `Colors`/`Background_Color`, a chart's `Color`) is **not** converted by default, because the generated stylesheet also colors widgets that don't use coloring. To convert it, pass `--colors`:

```
w2w --colors
```

This turns each coloring into a `webui::AnnotationsIdentifier` on the colored identifier, creates the `giim::s_AllColors` color set (with `p_Red`, `p_Green`, `p_Blue` and `p_ColorSlug`), and writes `WebUI\resources\css\w2w-color.css` in the main model.

Without `--colors`, none of this is generated, and a `w2w-color.css` left behind by an earlier `--colors` run is removed. Can be combined with `--page` and `--newcolorset`.

### Converting network objects

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

`map` and `diagram` force that widget for every Network Object in the run. `ignore` converts no Network Object at all: they get no widget and take no space in the page's grid (their number is reported at the end of the conversion log). The choice and its reason are recorded per object in `<project>_conversion.md`.

To mix choices within one project, combine `--network` with `--page`: convert the whole project once with the default, then reconvert a page whose Network Object should be the other widget, e.g. `w2w --page "Network Tie Flows" --network=map`.

Notes:

- A WebUI Diagram supports one arc set per widget. Only the first arc set of a Network Object is converted; the others are listed in the conversion log.
- Diagram coordinates are rescaled from the WinUI visible area to a drawing space the size of the WinUI object times `--diagram-spread` (default 2.5), with the Y axis flipped; the diagram's initial zoom is 1/spread. WebUI draws each node as a labelled box, much larger than WinUI's dot, so the spread gives them room. Use e.g. `--diagram-spread 4` for more room, or `--diagram-spread 1` for WinUI's own pixel size. The rescaling is done by generated parameters (`p_diagram_x_…`/`p_diagram_y_…`) in the generated module.
- GIS background layers, node/arc sizes, shapes and colors are not converted.
- When the WinUI visible area is computed at run time, the map's bounds are left unset (see the conversion log).

### Sharing page layouts

A page whose grid matches one of WebUI's standard layouts uses that standard layout. Every other page gets its own custom grid layout by default, so editing one page's layout in the WebUI editor never changes another page. To let pages with the same custom grid shape share one layout instead, pass `--share-layouts`:

```
w2w --share-layouts
```

Sharing keeps `webui.json` smaller, but a layout edit on one page then shows up on every page that shares it.

### Repointing AllColors element parameters

AIMMS's built-in `AllColors` set is not usable as-is by WebUI. Normally, `w2w` repoints the `Range` of an identifier ranged over `AllColors` to its own generated `giim::s_AllColors` set only when a converted widget uses that identifier for data coloring (so only with `--colors`).

To repoint *every* element parameter in the project whose `Range` is `AllColors` (case-insensitive), including ones no converted widget references, pass `--newcolorset`:

```
w2w --newcolorset
```

This can be combined with `--page`. It is off by default because it changes identifiers outside what the conversion itself needs.

## Errors

| Message | Cause |
|---|---|
| `No .aimms file found in the current directory` | Run `w2w` from the folder that contains the `.aimms` file. |
| `Multiple .aimms files found` | The folder contains more than one `.aimms` file; remove or move the extras. |
| `Page '...' not found in any component of the project` | The `--page` name does not match any page `Name` in a `PageManager.xml`. |
| `Project folder '...' does not exist` | Internal error: the detected path no longer exists. |
