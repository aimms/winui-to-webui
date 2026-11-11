# /webui-displaydomain page1[,page2,...] — Set the Display Domain of table identifiers, one page at a time

In a converted project, a WebUI table does not show rows for identifiers without data, although the WinUI table did, unless the Display Domain of the identifier is set to `1`. This skill sets `contents.N.displaydomain` to `{"literal": "1"}` for the identifiers of the tables on the selected pages where the WinUI table would have shown them.

**Work one page at a time.** A run over all 151 not-yet-refined pages of the RSC project made AIMMS loop infinitely, even with empty data, and was reverted. The cause is not known. Do not offer an `all` option, and do not process more pages than the user named.

## 1. Determine the project directory

- If the current working directory is inside the `711-winui-to-webui` repository (i.e. this skill's repository), ask the user for the path to the AIMMS project directory.
- Otherwise use the current working directory.

Before writing, check that AIMMS is closed: no `aimms.exe` process and no `*.aimmslockfile` in the project folder.

## 2. Determine which pages to process

The argument is: `$ARGUMENTS`

- Process only the pages named (page slugs as in `MainProject\WebUI\webui.json` under `pages/<slug>`, or the WinUI page names in `MainProject\Pages\*.xml`).
- If the argument is empty, ask which page to process. Suggest one page, not a list.

## 3. Locate inputs

- WebUI definition: `<projectdir>\MainProject\WebUI\webui.json` (CRLF line endings in the working copy; keep them).
- WinUI page specs: `<projectdir>\MainProject\Pages\<Page Name>.xml` (sub-pages and templates may be in `Templates\`).

## 4. For each selected page

List the page's table widgets (`widgets/table_<slug>_<n>` bound on `pages/<slug>`) and decide per table whether it qualifies.

### Rule 1 — several identifiers, each on a column
The table has at least two identifiers (`contents.N.identifier`) and `<IDENTIFIER-SET>` is in `contents.partition.colHeader`. In the WinUI this is the classic `Table`, `Sparse List` and `Composite Table` objects, which need no XML lookup.

### Rule 2 — the WinUI table has dense indices
The WinUI object is a `Pivot Table` that has at least one *dense index*, written in its XML as `Show_All_Elements`:

- `<Indices><Defaults><Show_All_Elements>1` makes every index dense, unless the index overrides it.
- A per-index `<Show_All_Elements>` inside `Explicit_Index`, `Identifier_Index`, `Case_Index` or `Suffix_Index` overrides the default (`0` = not dense, `1` = dense).
- When the element is absent, the index is not dense (AIMMS only writes the element when it is set; observed: 130 of 172 pivot tables carry `Defaults=1`).
- `Dense_Aggregation_restricts_to_Domain` is a different property that every pivot table has; ignore it.

A table qualifies when it meets **rule 1 or rule 2**. When the user's request says otherwise, follow the user.

### Finding the XML object of a widget
1. `table_<slug>_<n>`: `<n>` is the position of the object among the `PageObject` elements of the page's XML file (`iter('PageObject')`, document order, 1-based). Accept the object only if it is a `Pivot Table` and its `Contents/Explicit_Identifier/Identifier` names (last `::` component, arguments removed) equal the widget's `contents.N.identifier` names in order.
2. Otherwise (pages with sub-pages or templates share the counter, so `n` can point past the file or at another object type) look for pivot tables in all `Pages\*.xml` and `Templates\*.xml` with exactly the same identifier-name list. If all candidates agree on dense / not dense, use that; if they disagree, do **not** change the table on rule 2 and list it in the report.
3. Tables without a pivot XML match qualify only through rule 1.

Things seen on real pages that the two steps above miss:
- The widget number counts only the objects that were converted, so it can differ from the XML position (an unconverted `Selection Object` before the table shifts it). Compare the identifier names and the object type, not only the number.
- A set-valued identifier in the XML (`UnitCombinedCycleGroup( ud, ccg )`) shows up in the widget as a generated indicator (`giim::bp_indicator_UnitCombinedCycleGroup`). Treat the two as the same name when matching.
- A table whose XML object has `<Hidden>"Yes"</Hidden>` is never shown and the converter parks its widget in `Unassigned widgets`. Leave it alone and say so in the report.

### What to change
For every `contents.N.identifier` of a qualifying table that has **no** `contents.N.displaydomain` yet, add `contents.N.displaydomain` = `{"literal": "1"}`. Leave an existing `displaydomain` untouched, whatever its value (for example `"-2"`, or a `Domain` set by the converter).

**Identifiers with their own `<Domain>`:** when the XML identifier has a `<Domain>` element (`Explicit_Identifier/Domain`, e.g. `showSUProfile( SelectedDisplayUnit, iSuType, ipt )`), the WinUI table only showed the tuples in that domain, so `"1"` would show rows WinUI never showed. The converter only turns a `Domain` directly under `Contents` into a display domain, so these are dropped. Write the domain identifier instead, in the form the converter uses:

```
"contents.N.displaydomain": {
  "literal": { "identifier": "showSUProfile",
               "slice": [ { "index": "u", "type": "element-parameter", "value": "SelectedDisplayUnit" },
                          { "index": "iSuType", "type": "free", "value": "iSuType" },
                          { "index": "ipt", "type": "free", "value": "ipt" } ] }
}
```

The `index` names are the *declared* domain indices of the domain identifier (look it up in the model, e.g. `IndexDomain: (u,iSuType,ipt)`), not those of the content identifier: a content identifier from another namespace has its own index (`lsum::u`), which must not be copied. `type` and `value` follow the slice of the content identifier at the same position. Check the result against an existing converter-made display domain in the same `webui.json` (for example `table_cost_curves_5`).

Do not change scalars, charts or anything but table widgets.

## 5. Write webui.json

Edit by text insertion, not by re-serializing the JSON, so the formatting stays as AIMMS wrote it. Insert, directly after the closing `},` of each `"contents.N.identifier"` entry (4-space indentation, CRLF line endings):

```
    "contents.N.displaydomain": {
      "literal": "1"
    },
```

Then verify: the file parses, and compared with the version before the edit the only differences are the added `displaydomain` keys of the planned widgets.

## 6. Report, then stop

For each page report the tables changed (widget, rule 1 / rule 2 / both, number of identifiers), the tables left alone and why (already filled, no match, ambiguous). Then ask the user to open the page in AIMMS and confirm it behaves before the next page is processed. If AIMMS hangs, do not continue with other pages: note the widget names and contents of that page, so the rule can be refined, and revert the page.

## 7. Commit (when the user asks)

One commit per page, containing only that page's `displaydomain` additions, message e.g. `Set the display domain of the identifiers on page <slug>`. When composing a partial `webui.json` for a commit, build it from whole top-level blocks (`"widgets/x": {` ... next top-level key) and check object by object against the working file; zero-context or fuzzy hunk staging has put changes into the wrong table before. Blobs in the repository are LF, the working copy is CRLF.
