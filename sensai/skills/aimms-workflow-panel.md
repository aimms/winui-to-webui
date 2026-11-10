---
name: aimms-workflow-panel
description: Create a WebUI workflow panel (left-side step navigation) in an AIMMS app, built from a chosen parent page and the pages below it. Use when the user asks for a workflow panel or workflow steps, or mentions webui.json, WorkflowSteps, WorkflowDefinitions or workflows.configuration.
---

# AIMMS workflow panel

Builds a workflow panel from the page tree of an AIMMS WebUI project. The
child pages of a chosen **parent page** become the top-level steps, and their
children become child steps. It also moves the buttons that were used to
navigate those pages to the **Unassigned widgets** area of their page, so the
panel replaces them. Nothing is deleted, and no other widget is touched.

Tested with AIMMS 26.7, WebUI library 26.13 (webui.json version 4.67.0).

This skill is a single file. The helper script it needs is included below in
[Helper script](#helper-script-workflow_panelpy). Before the first step, write
that code block verbatim to a temporary file (your scratchpad, or a temp
folder; not inside the user's project) named `workflow_panel.py`, and run it
with `python -I <that path> <subcommand> <webui.json> ...`. It uses the
standard library only. Hand-editing `webui.json` is error-prone, so use the
script for it. The `.ams` edit is yours.

## Inputs to settle first

1. **Project paths.** Find `MainProject/WebUI/webui.json` and the model `.ams`
   (usually `MainProject/<name>.ams`). Ask if there are several.
2. **Parent page.** Run `list` to show the tree with slugs and ask the user
   which page is the top. Its children become the top-level steps.
3. **Workflow title** (default: parent page name).
4. **Icons.** Each step needs an `aimms-...` icon.
   `webui::AIMMSIcons` is the set of available names.
   Propose one per page from the [Available icons](#available-icons) list
   below (the names in `webui::AIMMSIcons`) and write a JSON map `{"slug": "aimms-xyz"}` to a temporary file for
   `--icons`. Names seen working:
   `aimms-lan`, `aimms-factory`, `aimms-atom`, `aimms-lab`. Don't invent names; if
   unsure, use the default and tell the user. See
   [Example icon map](#example-icon-map-data-reconciliation) for a complete map.
5. **Existing workflow.** Grep the `.ams` for `WorkflowSteps` and
   `WorkflowDefinitions`. If present, ask whether to replace them.

## Procedure

1. **Safety.** Check `git status` and `git check-ignore` on both files: converted
   apps often sit in an ignored `work/` folder, so git can't restore them. Before
   each write the script copies `webui.json` to `webui.json.workflow-panel.bak`.
   Copy the `.ams` yourself before editing it when it isn't tracked. AIMMS does not
   need to be closed, but if file changes are not picked up immediately the user
   may need to reload or reopen the project before compiling.
2. **Preview the steps.** Run
   `generate <webui.json> --parent <slug> --title "<T>" [--icons map.json] --out snippet.ams`
   (write `snippet.ams` to the same temporary folder).
   Read the stderr summary. Show the user the step list and any **EXCLUDED**
   pages (deeper than one child level; a workflow supports only one level).
   Ask whether to leave them out (default) or to restructure. More than 10
   top-level steps or 10 child steps per parent gets a warning; mention it.
3. **Write the model code.** Put the contents of `snippet.ams` in a
   `DeclarationSection` (for example `Workflow_Support`) in the model `.ams`.
   Keep the file's tab indentation. Keep `{ ... }`: this enables the use of
   expressions after the `:` in each entry.
   No comma after the last entry. See [Model declarations](#model-declarations-ams).
4. **Write the settings.** Run `settings <webui.json>`. It writes
   `workflows.configuration` and `workflows.information` into `"application"` in the
   exact format the WebUI needs, and empties stray top-level `aimms.widget.type`
   and `layoutId` keys. It replaces the Application Settings dialog, which you
   can't use. Never use the short form
   `{"aimms": {"contents": ["WorkflowSteps"]}}`; it validates but gives empty pages.
5. **Move the navigation buttons.** Only for pages that are workflow steps
   (excluded and parent pages are left alone). Run
   `unassign <webui.json> --ams <model.ams> --parent <slug> --dry-run` and read
   the list. The script classifies each button by the procedure behind its
   action (converter-generated `giim::pr_action_sequence_*` procedures, read
   from the `.ams`):
   - **MOVE**: the body only calls `webui::OpenPage(...)` (Main Navigation,
     Process Topology...), or is empty and the button is untitled, or titled
     Quit/Close (the arrow and Quit buttons).
   - **ASK**: the body is empty but the button has a real title (Print, Select
     Cases, Unit coordinates). These are unconverted actions and may be
     navigation. Show them to the user; they stay in place unless the user says
     to move them (`--include-ambiguous`).
   - Everything else is left alone: buttons that call a model procedure
     (`SolveTheModel`) or an action sequence that does more than open a page
     (Clear Dataset runs `NewCase()` first).

   Show the user the MOVE list and the ASK list, then run it without
   `--dry-run`. Moving sets the binding's `gridArea` to `Unassigned widgets`;
   the widget stays on the page and can be dragged back in the WebUI editor.
   Rerunning is safe. Empty grid columns that result are not removed; tell the
   user.
6. **Check.** Run
   `check <webui.json> --parent <slug> --ams <model.ams>`. Fix every ERROR and
   report every WARN. See [Troubleshooting](#troubleshooting).

## What to report

State what changed (files, number of steps, excluded pages, buttons moved and the ASK list), what the static
`check` found, and what only the user can verify.

## Workflow formats

### Page tree in webui.json

`application.pages.literal` is a tree of `{name, slug, type, children[]}`. The
slug is the page ID. Page content sits flat in `pages/<slug>` (with
`widgets.literal` and `bindings.literal`); widget definitions sit in
`widgets/<uri>`. `home` is a normal page with no content after conversion.

### Model declarations (`.ams`)

```
StringParameter WorkflowDefinitions {
    IndexDomain: (webui::indexWorkflowOrder, webui::indexWorkflowSpec);
    Definition: data { ( '1', 'title' ) : "Data Reconciliation" };
}
StringParameter WorkflowSteps {
    IndexDomain: (webui::indexWorkflowOrder, webui::indexNoOfPages,
                  webui::indexWorkflowPageSpec);
    Definition: {
        data {
            ( '1', '1', 'displayText'       ) : "Process Topology",
            ( '1', '1', 'icon'              ) : "aimms-lan",
            ( '1', '1', 'pageId'            ) : "process_topology",
            ( '1', '1', 'workflowPageState' ) : "Active",
            ( '1', '1', 'parentPageId'      ) : "",
            ( '1', '1', 'pageDataState'     ) : "",
            ( '1', '1', 'redirectPageId'    ) : "",

            ( '1', '2', 'displayText'       ) : "Units",
            ...
        }
    }
}
```

One line per field, a blank line between steps. The outer braces of
`Definition: { ... }` only enclose the attribute; the `data { ... }` is the value.
No comma after the last entry. `generate` produces exactly this.

| Field | Value |
|---|---|
| `displayText` | Name of the step in the panel. |
| `icon` | Icon from webui::AIMMSicons, with the `aimms-` prefix. |
| `pageId` | Page slug in `webui.json`; an element of `webui::allPageIds`. |
| `workflowPageState` | `Active`. Required: the default is hidden. |
| `parentPageId` | `pageId` of the parent step; empty for a top-level step. |
| `pageDataState`, `redirectPageId` | Leave empty. |

The step number (second index) is the display order, 1..N, across the whole list
(a child follows its parent).

### Settings in webui.json (exact format)

Both keys go inside the `"application"` object. `settings` writes them.

```json
"workflows.configuration": {
  "literal": {
    "identifier": "WorkflowSteps",
    "slice": [
      { "index": "webui::indexWorkflowOrder", "type": "free", "value": "webui::indexWorkflowOrder" },
      { "index": "webui::indexNoOfPages", "type": "free", "value": "webui::indexNoOfPages" },
      { "index": "webui::indexWorkflowPageSpec", "type": "free", "value": "webui::indexWorkflowPageSpec" }
    ]
  }
},
"workflows.information": {
  "aimms": {
    "contents": [ "WorkflowDefinitions" ],
    "slices": [
      {
        "identifier": "WorkflowDefinitions",
        "slice": [
          { "index": "webui::indexWorkflowOrder", "type": "free", "value": "webui::indexWorkflowOrder" },
          { "index": "webui::indexWorkflowSpec", "type": "free", "value": "webui::indexWorkflowSpec" }
        ]
      }
    ]
  }
}
```

If the user later changes these in the Application Settings dialog, the dialog
writes the same format, so the two ways are interchangeable.

### File writing

AIMMS writes `webui.json` as `json.dumps(indent=2, ensure_ascii=True)`: non-ASCII
is escaped (`©` becomes `©`), there is no trailing newline, and the line
endings are whatever git checked out (often CRLF on Windows). The script keeps
all of that. Keep it too if you ever edit the file outside the script, or the
diff will be huge.

## Troubleshooting

### Limits

- One level of child steps. Deeper pages don't appear in the panel.
- Recommended maximum: 10 top-level steps and 10 child steps per parent
  (AIMMS documentation). The Data Reconciliation example has three top-level steps
  and up to six or seven child steps each.

### No steps appear

- `workflowPageState` must be `Active` on every step (the default is hidden).
- `experimental-features.conf` (next to `webui.json`) must have
  `workflow_panel_v2 1`.

### The WebUI is empty

Check in this order:

1. The model compiles. A compile error leaves the WebUI empty.
2. The user is on a workflow page, not `home`. The WebUI opens on `home`, which
   the conversion leaves empty and which isn't a workflow step; no panel there is expected.
3. The definitions start with `data`.
4. `workflows.configuration` / `workflows.information` are in the exact format
   (`check` verifies; `settings` fixes).
5. Top-level `aimms.widget.type` and `layoutId` in `webui.json` are `{}`. The
   conversion can leave page keys at the top level (`aimms.widget.type`,
   `layoutId`, `bindings`, `widgets`) outside any `pages/...` object. When the
   WebUI saves the file it empties `aimms.widget.type` and `layoutId` to `{}`;
   `settings` does the same.

### Other

- Missing icon: check the name against [Available icons](#available-icons); it must match exactly and have the `aimms-` prefix.
- The WebUI rewrites `webui.json` on save. Re-run `check` after the user saves
  in the WebUI if anything looks off.

## Example icon map (Data Reconciliation)

The map used for the Data Reconciliation app. Reuse it as a starting point for
that app; for other apps, propose names per page.

```json
{
  "process_topology": "aimms-lan",
  "units": "aimms-factory",
  "components": "aimms-atom",
  "process_reactants": "aimms-lab",
  "reactant_composition": "aimms-pie-chart",
  "flows_and_components": "aimms-link",
  "flow_network": "aimms-map",
  "process_measurements": "aimms-meter",
  "measured_flows": "aimms-wave",
  "measured_compositions": "aimms-pie-chart2",
  "measurement_overview": "aimms-chart",
  "reconciliation": "aimms-cog",
  "measured_values": "aimms-database",
  "run_reconciliation_model": "aimms-play",
  "measured_vs_reconciled": "aimms-balance",
  "flow_chart": "aimms-stats-bars",
  "reconciled_values": "aimms-checkmark",
  "compare_multiple_cases": "aimms-copy"
}
```

## Helper script (`workflow_panel.py`)

Write this block verbatim to `workflow_panel.py` in a temporary folder before
use. Do not change it while copying.

```python
#!/usr/bin/env python3
"""Helper for the aimms-workflow-panel skill. Standard library only.

Subcommands (all take the path to MainProject/WebUI/webui.json first):

  list      <webui.json>                         show the page tree with slugs
  generate  <webui.json> --parent SLUG ...       write the .ams Definition snippet for the workflow
  settings  <webui.json> [--dry-run]             write workflows.configuration / .information, normalise top-level keys
  unassign  <webui.json> --ams FILE --parent SLUG  move navigation buttons of the workflow pages to 'Unassigned widgets'
  check     <webui.json> [--parent SLUG] [--ams FILE]   static checks, exit code 1 on errors

Run with:  python -I workflow_panel.py <subcommand> ...
webui.json is written like AIMMS writes it (indent=2, non-ASCII as \\uXXXX, no
trailing newline, the file's own line endings), so it round-trips byte for byte.
Before every write the current file is copied to webui.json.workflow-panel.bak.
"""
import argparse
import json
import re
import sys
from pathlib import Path

MAX_TOP = 10
MAX_CHILDREN = 10
DEFAULT_ICON = "aimms-lan"  # verified in a working example; pass --icons to choose others

WORKFLOW_CONFIGURATION = {
    "literal": {
        "identifier": "WorkflowSteps",
        "slice": [
            {"index": "webui::indexWorkflowOrder", "type": "free", "value": "webui::indexWorkflowOrder"},
            {"index": "webui::indexNoOfPages", "type": "free", "value": "webui::indexNoOfPages"},
            {"index": "webui::indexWorkflowPageSpec", "type": "free", "value": "webui::indexWorkflowPageSpec"},
        ],
    }
}
WORKFLOW_INFORMATION = {
    "aimms": {
        "contents": ["WorkflowDefinitions"],
        "slices": [
            {
                "identifier": "WorkflowDefinitions",
                "slice": [
                    {"index": "webui::indexWorkflowOrder", "type": "free", "value": "webui::indexWorkflowOrder"},
                    {"index": "webui::indexWorkflowSpec", "type": "free", "value": "webui::indexWorkflowSpec"},
                ],
            }
        ],
    }
}


# ---------------------------------------------------------------- helpers
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    """Write webui.json the way AIMMS does: indent=2, no trailing newline, non-ASCII
    escaped as \\uXXXX (AIMMS's own output has no raw non-ASCII). The file's
    existing line endings and escaping are kept, so the diff is only the real change."""
    p = Path(path)
    old = p.read_bytes()
    bak = p.with_name(p.name + ".workflow-panel.bak")  # own name: other skills keep their own .bak
    bak.write_bytes(old)  # always the state right before this write
    raw_non_ascii = any(c > 127 for c in old)
    text = json.dumps(data, indent=2, ensure_ascii=not raw_non_ascii)
    if b"\r\n" in old:  # git autocrlf checkouts on Windows are CRLF
        text = text.replace("\n", "\r\n")
    p.write_text(text, encoding="utf-8", newline="")
    print(f"wrote {p} (state before this write: {bak.name})")


def tree_root(data):
    try:
        return data["application"]["pages"]["literal"]
    except KeyError:
        sys.exit("error: no application.pages.literal in webui.json; is this a WebUI project file?")


def walk(node, depth=0, parent=None):
    yield node, depth, parent
    for c in node.get("children", []):
        yield from walk(c, depth + 1, node)


def find(root, slug):
    for n, _, _ in walk(root):
        if n.get("slug") == slug:
            return n
    sys.exit(f"error: no page with slug '{slug}'. Run the 'list' subcommand.")


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


# ---------------------------------------------------------------- list
def cmd_list(a):
    root = tree_root(load(a.webui))
    for n, d, _ in walk(root):
        kids = len(n.get("children", []))
        print(f"{'  ' * d}{n['name']}  [{n['slug']}]" + (f"  ({kids} children)" if kids else ""))


# ---------------------------------------------------------------- generate
def build_steps(root, parent_slug, max_depth=1):
    """Return (steps, excluded). Step = dict(name, slug, parent). Children of the
    parent page become top-level steps; their children become child steps."""
    parent = find(root, parent_slug)
    steps, excluded = [], []
    for top in parent.get("children", []):
        steps.append({"name": top["name"], "slug": top["slug"], "parent": ""})
        for child in top.get("children", []):
            steps.append({"name": child["name"], "slug": child["slug"], "parent": top["slug"]})
            for deeper, _, _ in walk(child):
                if deeper is not child:
                    excluded.append((deeper["name"], deeper["slug"], child["slug"]))
    return steps, excluded


def cmd_generate(a):
    data = load(a.webui)
    root = tree_root(data)
    steps, excluded = build_steps(root, a.parent)
    icons = json.loads(Path(a.icons).read_text(encoding="utf-8")) if a.icons else {}
    title = a.title or find(root, a.parent)["name"]
    out = []
    ind = "\t" * a.indent
    out.append(f"{ind}StringParameter WorkflowDefinitions {{")
    out.append(f"{ind}\tIndexDomain: (webui::indexWorkflowOrder, webui::indexWorkflowSpec);")
    out.append(f"{ind}\tDefinition: {{ ( '1', 'title' ) : {q(title)} }};")
    out.append(f"{ind}}}")
    out.append(f"{ind}StringParameter WorkflowSteps {{")
    out.append(f"{ind}\tIndexDomain: (webui::indexWorkflowOrder, webui::indexNoOfPages, webui::indexWorkflowPageSpec);")
    out.append(f"{ind}\tDefinition: {{")
    out.append(f"{ind}\t\t {{")
    blocks = []
    for i, s in enumerate(steps, 1):
        icon = icons.get(s["slug"], DEFAULT_ICON)
        rows = [
            ("displayText", s["name"]), ("icon", icon), ("pageId", s["slug"]),
            ("workflowPageState", "Active"), ("parentPageId", s["parent"]),
            ("pageDataState", ""), ("redirectPageId", ""),
        ]
        lines = [f"( '1', '{i}', {('%r' % k):<20} ) : {q(v)}" for k, v in rows]
        blocks.append(",\n".join(f"{ind}\t\t\t{l}" for l in lines))
    out.append(",\n\n".join(blocks))
    out.append(f"{ind}\t\t}}")
    out.append(f"{ind}\t}}")
    out.append(f"{ind}}}")
    text = "\n".join(out) + "\n"
    if a.out:
        Path(a.out).write_text(text, encoding="utf-8")
        print(f"wrote {a.out}")
    else:
        print(text)
    tops = sum(1 for s in steps if not s["parent"])
    print(f"# {len(steps)} steps: {tops} top-level, {len(steps) - tops} child", file=sys.stderr)
    if excluded:
        print("# EXCLUDED (deeper than one child level; a workflow supports one level):", file=sys.stderr)
        for n, s, under in excluded:
            print(f"#   {n} [{s}] under [{under}]", file=sys.stderr)
    if tops > MAX_TOP:
        print(f"# WARNING: {tops} top-level steps, documentation recommends at most {MAX_TOP}", file=sys.stderr)
    from collections import Counter
    for par, n in Counter(s["parent"] for s in steps if s["parent"]).items():
        if n > MAX_CHILDREN:
            print(f"# WARNING: [{par}] has {n} child steps, documentation recommends at most {MAX_CHILDREN}", file=sys.stderr)


# ---------------------------------------------------------------- settings
def normalise(data):
    changed = []
    app = data.setdefault("application", {})
    if app.get("workflows.configuration") != WORKFLOW_CONFIGURATION:
        app["workflows.configuration"] = WORKFLOW_CONFIGURATION
        changed.append("application.workflows.configuration")
    if app.get("workflows.information") != WORKFLOW_INFORMATION:
        app["workflows.information"] = WORKFLOW_INFORMATION
        changed.append("application.workflows.information")
    for key in ("aimms.widget.type", "layoutId"):
        if key in data and data[key] != {}:
            data[key] = {}
            changed.append(f"top-level {key} -> {{}}")
    return changed


def cmd_settings(a):
    data = load(a.webui)
    changed = normalise(data)
    if not changed:
        print("nothing to change; settings already in the exact format")
        return
    print("changes:\n  " + "\n  ".join(changed))
    if a.dry_run:
        print("(dry run, nothing written)")
    else:
        save(a.webui, data)


# ---------------------------------------------------------------- unassign
UNASSIGNED = "Unassigned widgets"
NAV_TITLES = {"quit", "close"}


def _strip_ams_comments(text):
    """Remove '!' line comments (outside strings) from AIMMS code."""
    out, in_s, i = [], None, 0
    while i < len(text):
        c = text[i]
        if in_s:
            out.append(c)
            if c == in_s:
                in_s = None
        elif c in "\"'":
            in_s = c
            out.append(c)
        elif c == "!":
            while i < len(text) and text[i] != "\n":
                i += 1
            continue
        else:
            out.append(c)
        i += 1
    return "".join(out)


def _block(text, start):
    """Text between the '{' at/after `start` and its matching '}' (strings respected)."""
    i = text.index("{", start)
    depth, in_s, j = 0, None, i
    while j < len(text):
        c = text[j]
        if in_s:
            if c == in_s:
                in_s = None
        elif c in "\"'":
            in_s = c
        elif c == "!":
            while j < len(text) and text[j] != "\n":
                j += 1
            continue
        elif c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
            if depth == 0:
                return text[i + 1:j]
        j += 1
    return text[i + 1:]


def procedure_kind(ams_text, name):
    """'open-page' (only webui::OpenPage/ClosePage calls), 'empty', 'functional' or None if not found."""
    name = name.split("::")[-1]
    m = re.search(r"\bProcedure\s+" + re.escape(name) + r"\s*\{", ams_text)
    if not m:
        return None
    body = _block(ams_text, m.start())
    b = re.search(r"\bBody\s*:\s*\{", body)
    if not b:
        return "empty"
    code = _strip_ams_comments(_block(body, b.start()))
    stmts = [x.strip() for x in code.split(";") if x.strip()]
    if not stmts:
        return "empty"
    if all(re.fullmatch(r"webui::(OpenPage|ClosePage)\s*\(.*\)", x, re.S) for x in stmts):
        return "open-page"
    return "functional"


def classify_button(wd, ams_text):
    """Return (class, reason); class is 'nav', 'ambiguous' or 'keep'."""
    act = wd.get("action", {}).get("literal", {})
    value = act.get("value", "") if isinstance(act, dict) else ""
    if not value.startswith("giim::pr_action_sequence_"):
        return "keep", f"action {value or '(none)'} is not a converter action sequence"
    kind = procedure_kind(ams_text, value)
    if kind is None:
        return "ambiguous", f"procedure {value} not found in the .ams"
    if kind == "open-page":
        return "nav", "only opens a page"
    if kind == "functional":
        return "keep", "action sequence does more than open a page"
    title = wd.get("title", {}).get("literal", "")
    name = wd.get("name", {}).get("literal", "")
    if title in ("", name) or title.strip().lower() in NAV_TITLES:
        return "nav", "empty action sequence (arrow / Quit / Close)"
    return "ambiguous", f"empty action sequence but titled '{title}'"


def cmd_unassign(a):
    data = load(a.webui)
    root = tree_root(data)
    ams = Path(a.ams).read_text(encoding="utf-8-sig", errors="replace")
    steps, _ = build_steps(root, a.parent)
    moves, ambiguous, kept = [], [], 0
    for st in steps:
        key = f"pages/{st['slug']}"
        page = data.get(key)
        if page is None:
            continue
        binds = page.setdefault("bindings", {"literal": []}).setdefault("literal", [])
        by_uri = {b["widgetUri"]: b for b in binds}
        for w in page.get("widgets", {}).get("literal", []):
            uri = w["uri"]
            wd = data.get(f"widgets/{uri}", {})
            if wd.get("aimms.widget.type", {}).get("literal") != "button":
                continue
            cls, why = classify_button(wd, ams)
            title = wd.get("title", {}).get("literal", "")
            if cls == "keep":
                kept += 1
                continue
            if cls == "ambiguous" and not a.include_ambiguous:
                ambiguous.append((st["slug"], uri, title, why))
                continue
            b = by_uri.get(uri)
            if b is not None and b.get("gridArea") == UNASSIGNED:
                continue  # already there
            if b is None:
                b = {"widgetUri": uri, "gridArea": UNASSIGNED, "dndId": UNASSIGNED + uri}
                binds.append(b)
            else:
                # dndId is left alone: the WebUI does the same when a widget is dragged there
                b["gridArea"] = UNASSIGNED
            moves.append((st["slug"], uri, title, why))
    for slug, uri, title, why in moves:
        print(f"MOVE  {slug:28s} {uri:42s} {title!r:28s} {why}")
    for slug, uri, title, why in ambiguous:
        print(f"ASK   {slug:28s} {uri:42s} {title!r:28s} {why}")
    print(f"{len(moves)} button(s) moved to '{UNASSIGNED}', {len(ambiguous)} ambiguous (left in place), "
          f"{kept} functional button(s) untouched")
    if not moves:
        return
    if a.dry_run:
        print("(dry run, nothing written)")
    else:
        save(a.webui, data)


# ---------------------------------------------------------------- check
AMS_ROW = re.compile(r"\(\s*'(\d+)'\s*,\s*'(\d+)'\s*,\s*'(\w+)'\s*\)\s*:\s*\"((?:[^\"\\]|\\.)*)\"")


def parse_ams_steps(text):
    m = re.search(r"StringParameter\s+WorkflowSteps\b.*?(?=\n\s*StringParameter\s|\Z)", text, re.S)
    if not m:
        return None, ["WorkflowSteps not found in the .ams file"]
    body = m.group(0)
    errs = []
    if re.search(r",\s*\}", body):
        errs.append("trailing comma before a closing brace in WorkflowSteps")
    steps = {}
    for wf, n, field, val in AMS_ROW.findall(body):
        steps.setdefault((wf, int(n)), {})[field] = val
    return steps, errs


def cmd_check(a):
    errs, warns = [], []
    p = Path(a.webui)
    data = load(p)
    root = tree_root(data)
    slugs = {n["slug"] for n, _, _ in walk(root)}

    app = data.get("application", {})
    if app.get("workflows.configuration") != WORKFLOW_CONFIGURATION:
        errs.append("application.workflows.configuration missing or not in the exact format (run 'settings')")
    if app.get("workflows.information") != WORKFLOW_INFORMATION:
        errs.append("application.workflows.information missing or not in the exact format (run 'settings')")
    for key in ("aimms.widget.type", "layoutId"):
        if key in data and data[key] != {}:
            errs.append(f"top-level '{key}' is not {{}}")

    if a.ams:
        steps, e = parse_ams_steps(Path(a.ams).read_text(encoding="utf-8-sig", errors="replace"))
        errs += e
        if steps:
            tops = [s for s in steps.values() if not s.get("parentPageId")]
            ids = {s.get("pageId") for s in steps.values()}
            for (wf, n), s in sorted(steps.items()):
                pid = s.get("pageId", "")
                if pid not in slugs:
                    errs.append(f"step {n}: pageId '{pid}' is not a page in webui.json")
                if f"pages/{pid}" not in data:
                    warns.append(f"step {n}: no 'pages/{pid}' object in webui.json (page has no content)")
                if s.get("workflowPageState") != "Active":
                    errs.append(f"step {n} ({pid}): workflowPageState must be 'Active'")
                par = s.get("parentPageId", "")
                if par:
                    if par not in ids:
                        errs.append(f"step {n} ({pid}): parentPageId '{par}' is not a step")
                    elif any(t.get("pageId") == par for t in tops) is False:
                        errs.append(f"step {n} ({pid}): parent '{par}' is itself a child; only one level is supported")
                if not s.get("displayText"):
                    errs.append(f"step {n} ({pid}): empty displayText")
                if not s.get("icon", "").startswith("aimms-"):
                    warns.append(f"step {n} ({pid}): icon '{s.get('icon')}' lacks the 'aimms-' prefix")
            if len(tops) > MAX_TOP:
                warns.append(f"{len(tops)} top-level steps (recommended max {MAX_TOP})")
            from collections import Counter
            for par, n in Counter(s.get("parentPageId") for s in steps.values() if s.get("parentPageId")).items():
                if n > MAX_CHILDREN:
                    warns.append(f"'{par}' has {n} child steps (recommended max {MAX_CHILDREN})")
            if a.parent:
                expected, _ = build_steps(root, a.parent)
                missing = {s["slug"] for s in expected} - ids
                if missing:
                    warns.append(f"pages under '{a.parent}' not in the workflow: {sorted(missing)}")

    for w in warns:
        print("WARN ", w)
    for e in errs:
        print("ERROR", e)
    print(f"{len(errs)} error(s), {len(warns)} warning(s)")
    sys.exit(1 if errs else 0)


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("list"); s.add_argument("webui"); s.set_defaults(f=cmd_list)

    s = sub.add_parser("generate"); s.add_argument("webui")
    s.add_argument("--parent", required=True, help="slug of the page at the top of the tree")
    s.add_argument("--title", help="workflow title (default: parent page name)")
    s.add_argument("--icons", help="JSON file mapping slug -> icon name (aimms-...)")
    s.add_argument("--indent", type=int, default=3, help="leading tabs in the snippet")
    s.add_argument("--out"); s.set_defaults(f=cmd_generate)

    s = sub.add_parser("settings"); s.add_argument("webui")
    s.add_argument("--dry-run", action="store_true"); s.set_defaults(f=cmd_settings)

    s = sub.add_parser("unassign"); s.add_argument("webui")
    s.add_argument("--ams", required=True, help="model .ams (to read the button action procedures)")
    s.add_argument("--parent", required=True, help="slug of the page at the top of the tree")
    s.add_argument("--include-ambiguous", action="store_true",
                   help="also move empty-action buttons that have a real title (Print, Select Cases...)")
    s.add_argument("--dry-run", action="store_true"); s.set_defaults(f=cmd_unassign)

    s = sub.add_parser("check"); s.add_argument("webui")
    s.add_argument("--parent"); s.add_argument("--ams"); s.set_defaults(f=cmd_check)

    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
```

## Available icons

These are all 1609 names in `webui::AIMMSIcons`, read from the model
(`webui::AIMMSIcons := data { ... }`). An icon must be one of them, exactly as
written and with the `aimms-` prefix. Search this list (grep) for a name that
fits the page instead of guessing. Names are case-sensitive, e.g. `aimms-IcoMoon`.

```text
aimms-home aimms-home2 aimms-home3 aimms-home4 aimms-home5 aimms-home6 aimms-home7 aimms-home8
aimms-home9 aimms-office aimms-city aimms-newspaper aimms-magazine aimms-design aimms-pencil
aimms-pencil2 aimms-pencil3 aimms-pencil4 aimms-pencil5 aimms-pencil6 aimms-pencil7 aimms-eraser
aimms-eraser2 aimms-eraser3 aimms-quill aimms-quill2 aimms-quill3 aimms-quill4 aimms-pen
aimms-pen-plus aimms-pen-minus aimms-pen2 aimms-pen3 aimms-pen4 aimms-pen5 aimms-marker
aimms-marker2 aimms-blog aimms-blog2 aimms-pen6 aimms-brush aimms-spray aimms-palette aimms-palette2
aimms-color-sampler aimms-toggle aimms-bucket aimms-bucket2 aimms-gradient aimms-eyedropper
aimms-eyedropper2 aimms-eyedropper3 aimms-droplet aimms-droplet2 aimms-droplet-contrast
aimms-color-clear aimms-paint-format aimms-stamp aimms-images aimms-image aimms-image2
aimms-image-compare aimms-images2 aimms-image3 aimms-images3 aimms-image4 aimms-image5 aimms-image6
aimms-camera aimms-camera2 aimms-camera3 aimms-shutter aimms-headphones aimms-headset aimms-music
aimms-music2 aimms-music3 aimms-music4 aimms-music5 aimms-music6 aimms-album aimms-cassette
aimms-tape aimms-piano aimms-guitar aimms-trumpet aimms-speakers aimms-play aimms-play2
aimms-clapboard-play aimms-clapboard aimms-media aimms-presentation aimms-movie aimms-film
aimms-film2 aimms-film3 aimms-film4 aimms-video-camera aimms-video-camera2 aimms-video-camera-slash
aimms-video-camera3 aimms-video-camera4 aimms-video-camera-slash2 aimms-video-camera5
aimms-recording aimms-dice aimms-gamepad aimms-gamepad2 aimms-gamepad3 aimms-pacman aimms-spades
aimms-clubs aimms-diamonds aimms-chess-king aimms-chess-queen aimms-chess-rook aimms-chess-bishop
aimms-chess-knight aimms-chess-pawn aimms-chess aimms-bullhorn aimms-megaphone aimms-new
aimms-connection aimms-connection2 aimms-connection3 aimms-connection4 aimms-podcast aimms-station
aimms-station2 aimms-antenna aimms-satellite-dish aimms-satellite-dish2 aimms-feed aimms-podcast2
aimms-antenna2 aimms-mic aimms-mic-off aimms-mic2 aimms-mic-off2 aimms-mic3 aimms-mic4 aimms-mic5
aimms-book aimms-book2 aimms-book-play aimms-book3 aimms-bookmark aimms-books aimms-archive
aimms-reading aimms-library aimms-library2 aimms-graduation aimms-file-text aimms-profile
aimms-file-empty aimms-file-empty2 aimms-files-empty aimms-files-empty2 aimms-file-plus
aimms-file-plus2 aimms-file-minus aimms-file-minus2 aimms-file-download aimms-file-download2
aimms-file-upload aimms-file-upload2 aimms-file-check aimms-file-check2 aimms-file-eye
aimms-file-eye2 aimms-file-text2 aimms-file-text3 aimms-file-picture aimms-file-picture2
aimms-file-music aimms-file-music2 aimms-file-play aimms-file-play2 aimms-file-video
aimms-file-video2 aimms-copy aimms-copy2 aimms-file-zip aimms-file-zip2 aimms-file-xml
aimms-file-xml2 aimms-file-css aimms-file-css2 aimms-file-presentation aimms-file-presentation2
aimms-file-stats aimms-file-stats2 aimms-file-locked aimms-file-locked2 aimms-file-spreadsheet
aimms-file-spreadsheet2 aimms-copy3 aimms-copy4 aimms-paste aimms-paste2 aimms-paste3 aimms-paste4
aimms-stack aimms-stack2 aimms-stack3 aimms-folder aimms-folder-search aimms-folder-download
aimms-folder-upload aimms-folder-plus aimms-folder-plus2 aimms-folder-minus aimms-folder-minus2
aimms-folder-check aimms-folder-heart aimms-folder-remove aimms-folder2 aimms-folder-open
aimms-folder3 aimms-folder4 aimms-folder-plus3 aimms-folder-minus3 aimms-folder-plus4
aimms-folder-minus4 aimms-folder-download2 aimms-folder-upload2 aimms-folder-download3
aimms-folder-upload3 aimms-folder5 aimms-folder-open2 aimms-folder6 aimms-folder-open3
aimms-certificate aimms-cc aimms-price-tag aimms-price-tag2 aimms-price-tags aimms-price-tag3
aimms-price-tags2 aimms-price-tag4 aimms-price-tags3 aimms-price-tag5 aimms-price-tags4
aimms-barcode aimms-barcode2 aimms-qrcode aimms-ticket aimms-ticket2 aimms-theater aimms-store
aimms-store2 aimms-cart aimms-cart2 aimms-cart3 aimms-cart4 aimms-cart5 aimms-cart-add
aimms-cart-add2 aimms-cart-remove aimms-basket aimms-bag aimms-bag2 aimms-percent aimms-coins
aimms-coin-dollar aimms-coin-euro aimms-coin-pound aimms-coin-yen aimms-piggy-bank aimms-wallet
aimms-cash aimms-cash2 aimms-cash3 aimms-cash4 aimms-credit-card aimms-credit-card2 aimms-calculator
aimms-calculator2 aimms-calculator3 aimms-chip aimms-lifebuoy aimms-phone aimms-phone2
aimms-phone-slash aimms-phone-wave aimms-phone-plus aimms-phone-minus aimms-phone-plus2
aimms-phone-minus2 aimms-phone-incoming aimms-phone-outgoing aimms-phone3 aimms-phone-slash2
aimms-phone-wave2 aimms-phone-hang-up aimms-phone-hang-up2 aimms-address-book aimms-address-book2
aimms-address-book3 aimms-notebook aimms-at-sign aimms-envelop aimms-envelop2 aimms-envelop3
aimms-envelop4 aimms-envelop5 aimms-mailbox aimms-pushpin aimms-pushpin2 aimms-location
aimms-location2 aimms-location3 aimms-location4 aimms-location5 aimms-location6 aimms-location7
aimms-compass aimms-compass2 aimms-compass3 aimms-compass4 aimms-compass5 aimms-compass6 aimms-map
aimms-map2 aimms-map3 aimms-map4 aimms-map5 aimms-direction aimms-reset aimms-history aimms-clock
aimms-clock2 aimms-clock3 aimms-clock4 aimms-watch aimms-watch2 aimms-alarm aimms-alarm-add
aimms-alarm-check aimms-alarm-cancel aimms-bell aimms-bell2 aimms-bell3 aimms-bell-plus
aimms-bell-minus aimms-bell-check aimms-bell-cross aimms-stopwatch aimms-calendar aimms-calendar2
aimms-calendar3 aimms-calendar4 aimms-calendar5 aimms-calendar-empty aimms-calendar-day
aimms-calendar-week aimms-printer aimms-printer2 aimms-printer3 aimms-printer4 aimms-shredder
aimms-mouse aimms-mouse2 aimms-mouse-left aimms-mouse-right aimms-keyboard aimms-keyboard2
aimms-typewriter aimms-display aimms-display2 aimms-display3 aimms-display4 aimms-laptop
aimms-mobile aimms-mobile2 aimms-tablet aimms-mobile3 aimms-tv aimms-radio aimms-cabinet
aimms-drawer aimms-drawer2 aimms-drawer-out aimms-drawer-in aimms-drawer3 aimms-box aimms-box-add
aimms-box-remove aimms-download aimms-upload aimms-floppy-disk aimms-floppy-disks
aimms-floppy-disks2 aimms-floppy-disk2 aimms-floppy-disk3 aimms-disk aimms-disk2 aimms-usb-stick
aimms-drive aimms-server aimms-database aimms-database2 aimms-database3 aimms-database4
aimms-database-menu aimms-database-add aimms-database-remove aimms-database-insert
aimms-database-export aimms-database-upload aimms-database-refresh aimms-database-diff
aimms-database-edit aimms-database-edit2 aimms-database-check aimms-database-arrow
aimms-database-time aimms-database-time2 aimms-undo aimms-redo aimms-rotate-ccw aimms-rotate-cw
aimms-rotate-ccw2 aimms-rotate-cw2 aimms-rotate-ccw3 aimms-rotate-cw3 aimms-flip-vertical
aimms-flip-vertical2 aimms-flip-horizontal aimms-flip-horizontal2 aimms-flip-vertical3
aimms-flip-vertical4 aimms-angle aimms-shear aimms-unite aimms-subtract aimms-interset aimms-exclude
aimms-align-left aimms-align-center-horizontal aimms-align-right aimms-align-top
aimms-align-center-vertical aimms-align-bottom aimms-undo2 aimms-redo2 aimms-forward aimms-reply
aimms-reply-all aimms-bubble aimms-bubbles aimms-bubbles2 aimms-bubble2 aimms-bubbles3
aimms-bubbles4 aimms-bubble-notification aimms-bubbles5 aimms-bubbles6 aimms-bubble3
aimms-bubble-dots aimms-bubble-lines aimms-bubble4 aimms-bubble-dots2 aimms-bubble-lines2
aimms-bubble5 aimms-bubble6 aimms-bubbles7 aimms-bubble7 aimms-bubbles8 aimms-bubble8
aimms-bubble-dots3 aimms-bubble-lines3 aimms-bubble9 aimms-bubble-dots4 aimms-bubble-lines4
aimms-bubbles9 aimms-bubbles10 aimms-bubble-blocked aimms-bubble-quote aimms-bubble-user
aimms-bubble-smiley aimms-bubble-check aimms-bubble-video aimms-bubble-link aimms-bubble-lock
aimms-bubble-star aimms-bubble-heart aimms-bubble-paperclip aimms-bubble-cancel aimms-bubble-plus
aimms-bubble-minus aimms-bubble-notification2 aimms-bubble-left aimms-bubble-right
aimms-bubble-first aimms-bubble-last aimms-bubble-reply aimms-bubble-forward aimms-bubble-reply2
aimms-bubble-forward2 aimms-user aimms-users aimms-user-plus aimms-user-minus aimms-user-cancel
aimms-user-block aimms-user-lock aimms-user-check aimms-users2 aimms-user2 aimms-users3
aimms-user-plus2 aimms-user-minus2 aimms-user-cancel2 aimms-user-block2 aimms-user-lock2
aimms-user-check2 aimms-user3 aimms-user4 aimms-user5 aimms-user6 aimms-users4 aimms-user-tie
aimms-user7 aimms-users5 aimms-collaboration aimms-vcard aimms-hat aimms-bowtie aimms-tie
aimms-hanger aimms-tshirt aimms-pants aimms-shorts aimms-sock aimms-laundry aimms-quotes-left
aimms-quotes-right aimms-quotes-left2 aimms-quotes-right2 aimms-hour-glass aimms-hour-glass2
aimms-hour-glass3 aimms-spinner aimms-spinner2 aimms-spinner3 aimms-spinner4 aimms-spinner5
aimms-spinner6 aimms-spinner7 aimms-spinner8 aimms-spinner9 aimms-spinner10 aimms-spinner11
aimms-microscope aimms-binoculars aimms-binoculars2 aimms-search aimms-zoom-in aimms-zoom-out
aimms-search2 aimms-zoom-in2 aimms-zoom-out2 aimms-search3 aimms-search4 aimms-zoom-in3
aimms-zoom-out3 aimms-search5 aimms-search6 aimms-enlarge aimms-shrink aimms-enlarge2 aimms-shrink2
aimms-enlarge3 aimms-shrink3 aimms-enlarge4 aimms-shrink4 aimms-enlarge5 aimms-shrink5
aimms-enlarge6 aimms-shrink6 aimms-enlarge7 aimms-shrink7 aimms-key aimms-key2 aimms-key3 aimms-key4
aimms-key5 aimms-keyhole aimms-lock aimms-lock2 aimms-lock3 aimms-lock4 aimms-unlocked aimms-lock5
aimms-unlocked2 aimms-safe aimms-wrench aimms-wrench2 aimms-wrench3 aimms-equalizer aimms-equalizer2
aimms-equalizer3 aimms-equalizer4 aimms-cog aimms-cogs aimms-cog2 aimms-cog3 aimms-cog4 aimms-cog5
aimms-cog6 aimms-cog7 aimms-factory aimms-hammer aimms-hammer-wrench aimms-knife aimms-screwdriver
aimms-screwdriver2 aimms-magic-wand aimms-magic-wand2 aimms-pulse aimms-pulse2 aimms-aid-kit
aimms-aid-kit2 aimms-stethoscope aimms-ambulance aimms-alarm2 aimms-pandage aimms-pandage2 aimms-bug
aimms-bug2 aimms-syringe aimms-syringe2 aimms-pill aimms-construction aimms-traffic-cone
aimms-traffic-lights aimms-pie-chart aimms-pie-chart2 aimms-pie-chart3 aimms-pie-chart4
aimms-pie-chart5 aimms-pie-chart6 aimms-pie-chart7 aimms-stats-dots aimms-stats-bars
aimms-pie-chart8 aimms-stats-bars2 aimms-stats-bars3 aimms-stats-bars4 aimms-stats-bars5
aimms-stats-bars6 aimms-chart aimms-stats-growth aimms-stats-decline aimms-stats-growth2
aimms-stats-decline2 aimms-stairs-up aimms-stairs-down aimms-stairs aimms-stairs2 aimms-ladder
aimms-rating aimms-rating2 aimms-rating3 aimms-cake aimms-podium aimms-stars aimms-medal-star
aimms-medal aimms-medal2 aimms-medal-first aimms-medal-second aimms-medal-third aimms-crown
aimms-trophy aimms-trophy2 aimms-trophy3 aimms-diamond aimms-diamond2 aimms-trophy4 aimms-gift
aimms-gift2 aimms-balloon aimms-pipe aimms-mustache aimms-mustache2 aimms-glass aimms-glass2
aimms-glass3 aimms-glass4 aimms-bottle aimms-bottle2 aimms-bottle3 aimms-bottle4 aimms-mug
aimms-fork-knife aimms-spoon-knife aimms-cook aimms-plate aimms-steak aimms-fish aimms-chicken
aimms-hamburger aimms-pizza aimms-cheese aimms-bread aimms-icecream aimms-milk aimms-cup aimms-cup2
aimms-coffee-bean aimms-coffee aimms-teapot aimms-leaf aimms-leaf2 aimms-apple aimms-grapes
aimms-cherry aimms-tree aimms-tree2 aimms-tree3 aimms-tree4 aimms-cactus aimms-mountains aimms-paw
aimms-footprint aimms-tent aimms-flower aimms-flower2 aimms-rocket aimms-meter aimms-meter2
aimms-meter-slow aimms-meter-medium aimms-meter-fast aimms-meter3 aimms-hammer2 aimms-balance
aimms-scale aimms-bomb aimms-fire aimms-fire2 aimms-lab aimms-atom aimms-atom2 aimms-magnet
aimms-magnet2 aimms-dumbbell aimms-skull aimms-skull2 aimms-lamp aimms-lamp2 aimms-lamp3
aimms-spotlight aimms-lamp4 aimms-lamp5 aimms-lamp6 aimms-lamp7 aimms-lamp8 aimms-broom
aimms-toiletpaper aimms-bin aimms-bin2 aimms-bin3 aimms-bin4 aimms-bin5 aimms-briefcase
aimms-briefcase2 aimms-briefcase3 aimms-airplane aimms-airplane2 aimms-airplane3 aimms-airplane4
aimms-paperplane aimms-car aimms-steering-wheel aimms-car2 aimms-gas aimms-bus aimms-truck
aimms-bike aimms-road aimms-train aimms-train2 aimms-ship aimms-boat aimms-chopper aimms-chopper2
aimms-cube aimms-cube2 aimms-cube3 aimms-cube4 aimms-pyramid aimms-pyramid2 aimms-package
aimms-puzzle aimms-puzzle2 aimms-puzzle3 aimms-puzzle4 aimms-glasses-3d aimms-glasses-3d2
aimms-glasses aimms-glasses2 aimms-brain aimms-accessibility aimms-accessibility2 aimms-strategy
aimms-target aimms-target2 aimms-target3 aimms-ammo aimms-gun aimms-gun-forbidden aimms-shield
aimms-shield-check aimms-shield-notice aimms-shield2 aimms-shield3 aimms-shield4 aimms-soccer
aimms-football aimms-archery aimms-bow aimms-sword aimms-tennis aimms-pingpong aimms-baseball
aimms-basketball aimms-golf aimms-golf2 aimms-hockey aimms-racing aimms-finish aimms-eight-ball
aimms-bowling aimms-bowling2 aimms-power aimms-power2 aimms-power3 aimms-switch aimms-switch2
aimms-power-cord aimms-power-cord2 aimms-outlet aimms-clipboard aimms-clipboard2 aimms-clipboard3
aimms-clipboard4 aimms-clipboard5 aimms-clipboard6 aimms-playlist aimms-playlist-add
aimms-list-numbered aimms-list aimms-list2 aimms-more aimms-more2 aimms-grid aimms-grid2 aimms-grid3
aimms-grid4 aimms-grid5 aimms-grid6 aimms-grid7 aimms-tree5 aimms-tree6 aimms-tree7 aimms-lan
aimms-lan2 aimms-lan3 aimms-menu aimms-circle-small aimms-menu2 aimms-menu3 aimms-menu4 aimms-menu5
aimms-menu6 aimms-menu7 aimms-menu8 aimms-menu9 aimms-menu10 aimms-cloud aimms-cloud-download
aimms-cloud-upload aimms-cloud-check aimms-cloud2 aimms-cloud-download2 aimms-cloud-upload2
aimms-cloud-check2 aimms-download2 aimms-download3 aimms-upload2 aimms-upload3 aimms-import
aimms-import2 aimms-download4 aimms-upload4 aimms-download5 aimms-upload5 aimms-download6
aimms-upload6 aimms-download7 aimms-upload7 aimms-download8 aimms-upload8 aimms-download9
aimms-upload9 aimms-download10 aimms-upload10 aimms-sphere aimms-sphere2 aimms-sphere3 aimms-planet
aimms-planet2 aimms-earth aimms-earth2 aimms-earth3 aimms-link aimms-unlink aimms-link2
aimms-unlink2 aimms-link3 aimms-unlink3 aimms-link4 aimms-unlink4 aimms-link5 aimms-unlink5
aimms-anchor aimms-flag aimms-flag2 aimms-flag3 aimms-flag4 aimms-flag5 aimms-flag6 aimms-flag7
aimms-flag8 aimms-attachment aimms-attachment2 aimms-eye aimms-eye-plus aimms-eye-minus
aimms-eye-blocked aimms-eye2 aimms-eye-blocked2 aimms-eye3 aimms-eye-blocked3 aimms-eye4
aimms-bookmark2 aimms-bookmark3 aimms-bookmarks aimms-bookmark4 aimms-spotlight2 aimms-starburst
aimms-snowflake aimms-temperature aimms-temperature2 aimms-weather-lightning
aimms-weather-lightning2 aimms-weather-rain aimms-weather-rain2 aimms-weather-snow
aimms-weather-snow2 aimms-weather-cloud-wind aimms-weather-cloud-wind2 aimms-weather-cloud-sun
aimms-weather-cloud-sun2 aimms-weather-cloudy aimms-weather-cloudy2 aimms-weather-sun-wind
aimms-weather-sun-wind2 aimms-sun aimms-sun2 aimms-moon aimms-day-night aimms-day-night2
aimms-weather-windy aimms-fan aimms-umbrella aimms-sun3 aimms-contrast aimms-brightness-contrast
aimms-brightness-high aimms-brightness-medium aimms-brightness-low aimms-bed aimms-bed2
aimms-furniture aimms-chair aimms-star-empty aimms-star-empty2 aimms-star-full aimms-star-empty3
aimms-star-half aimms-star-full2 aimms-star aimms-heart aimms-heart2 aimms-heart3 aimms-heart4
aimms-heart-broken aimms-heart5 aimms-heart6 aimms-heart-broken2 aimms-heart7 aimms-heart8
aimms-heart-broken3 aimms-lips aimms-lips2 aimms-thumbs-up aimms-thumbs-up2 aimms-thumbs-down
aimms-thumbs-down2 aimms-thumbs-up3 aimms-thumbs-down3 aimms-height aimms-man aimms-woman
aimms-man-woman aimms-male aimms-female aimms-peace aimms-yin-yang aimms-happy aimms-happy2
aimms-smile aimms-smile2 aimms-tongue aimms-tongue2 aimms-sad aimms-sad2 aimms-wink aimms-wink2
aimms-grin aimms-grin2 aimms-cool aimms-cool2 aimms-angry aimms-angry2 aimms-evil aimms-evil2
aimms-shocked aimms-shocked2 aimms-baffled aimms-baffled2 aimms-confused aimms-confused2
aimms-neutral aimms-neutral2 aimms-hipster aimms-hipster2 aimms-wondering aimms-wondering2
aimms-sleepy aimms-sleepy2 aimms-frustrated aimms-frustrated2 aimms-crying aimms-crying2
aimms-cursor aimms-cursor2 aimms-lasso aimms-lasso2 aimms-select aimms-select2 aimms-point-up
aimms-point-right aimms-point-down aimms-point-left aimms-pointer aimms-reminder
aimms-drag-left-right aimms-drag-left aimms-drag-right aimms-touch aimms-multitouch aimms-touch-zoom
aimms-touch-pinch aimms-hand aimms-grab aimms-stack-empty aimms-stack-plus aimms-stack-minus
aimms-stack-star aimms-stack-picture aimms-stack-down aimms-stack-up aimms-stack-cancel
aimms-stack-check aimms-stack-text aimms-stack-clubs aimms-stack-spades aimms-stack-hearts
aimms-stack-diamonds aimms-stack-user aimms-stack4 aimms-stack-music aimms-stack-play aimms-move
aimms-dots aimms-warning aimms-warning2 aimms-notification aimms-notification2 aimms-question
aimms-question2 aimms-question3 aimms-question4 aimms-question5 aimms-question6 aimms-plus
aimms-minus aimms-plus2 aimms-minus2 aimms-plus3 aimms-minus3 aimms-plus-circle aimms-minus-circle
aimms-plus-circle2 aimms-minus-circle2 aimms-info aimms-info2 aimms-cancel-circle
aimms-cancel-circle2 aimms-blocked aimms-cancel-square aimms-cancel-square2 aimms-cancel aimms-spam
aimms-cross aimms-cross2 aimms-cross3 aimms-checkmark aimms-checkmark2 aimms-checkmark3
aimms-checkmark4 aimms-checkmark5 aimms-spell-check aimms-spell-check2 aimms-enter aimms-exit
aimms-enter2 aimms-exit2 aimms-enter3 aimms-exit3 aimms-wall aimms-fence aimms-play3 aimms-pause
aimms-stop aimms-previous aimms-next aimms-backward aimms-forward2 aimms-play4 aimms-pause2
aimms-stop2 aimms-backward2 aimms-forward3 aimms-first aimms-last aimms-previous2 aimms-next2
aimms-eject aimms-volume-high aimms-volume-medium aimms-volume-low aimms-volume-mute
aimms-speaker-left aimms-speaker-right aimms-volume-mute2 aimms-volume-increase
aimms-volume-decrease aimms-volume-high2 aimms-volume-medium2 aimms-volume-medium3 aimms-volume-low2
aimms-volume-mute3 aimms-volume-increase2 aimms-volume-decrease2 aimms-volume-decrease3
aimms-volume-5 aimms-volume-4 aimms-volume-3 aimms-volume-2 aimms-volume-1 aimms-volume-0
aimms-volume-mute4 aimms-volume-mute5 aimms-loop aimms-loop2 aimms-loop3 aimms-infinite-square
aimms-infinite aimms-infinite2 aimms-loop4 aimms-shuffle aimms-shuffle2 aimms-wave aimms-wave2
aimms-split aimms-merge aimms-first2 aimms-last2 aimms-arrow-up aimms-arrow-up2 aimms-arrow-up3
aimms-arrow-up4 aimms-arrow-right aimms-arrow-right2 aimms-arrow-right3 aimms-arrow-right4
aimms-arrow-down aimms-arrow-down2 aimms-arrow-down3 aimms-arrow-down4 aimms-arrow-left
aimms-arrow-left2 aimms-arrow-left3 aimms-arrow-left4 aimms-arrow-up5 aimms-arrow-right5
aimms-arrow-down5 aimms-arrow-left5 aimms-arrow-up-left aimms-arrow-up6 aimms-arrow-up-right
aimms-arrow-right6 aimms-arrow-down-right aimms-arrow-down6 aimms-arrow-down-left aimms-arrow-left6
aimms-arrow-up-left2 aimms-arrow-up7 aimms-arrow-up-right2 aimms-arrow-right7
aimms-arrow-down-right2 aimms-arrow-down7 aimms-arrow-down-left2 aimms-arrow-left7
aimms-arrow-up-left3 aimms-arrow-up8 aimms-arrow-up-right3 aimms-arrow-right8
aimms-arrow-down-right3 aimms-arrow-down8 aimms-arrow-down-left3 aimms-arrow-left8 aimms-circle-up
aimms-circle-right aimms-circle-down aimms-circle-left aimms-circle-up2 aimms-circle-right2
aimms-circle-down2 aimms-circle-left2 aimms-circle-up-left aimms-circle-up3 aimms-circle-up-right
aimms-circle-right3 aimms-circle-down-right aimms-circle-down3 aimms-circle-down-left
aimms-circle-left3 aimms-circle-up-left2 aimms-circle-up4 aimms-circle-up-right2 aimms-circle-right4
aimms-circle-down-right2 aimms-circle-down4 aimms-circle-down-left2 aimms-circle-left4
aimms-arrow-resize aimms-arrow-resize2 aimms-arrow-resize3 aimms-arrow-resize4 aimms-arrow-resize5
aimms-arrow-resize6 aimms-arrow-resize7 aimms-arrow-resize8 aimms-square-up-left aimms-square-up
aimms-square-up-right aimms-square-right aimms-square-down-right aimms-square-down
aimms-square-down-left aimms-square-left aimms-arrow-up9 aimms-arrow-right9 aimms-arrow-down9
aimms-arrow-left9 aimms-arrow-up10 aimms-arrow-right10 aimms-arrow-down10 aimms-arrow-left10
aimms-arrow-up-left4 aimms-arrow-up11 aimms-arrow-up-right4 aimms-arrow-right11
aimms-arrow-down-right4 aimms-arrow-down11 aimms-arrow-down-left4 aimms-arrow-left11
aimms-arrow-up-left5 aimms-arrow-up12 aimms-arrow-up-right5 aimms-arrow-right12
aimms-arrow-down-right5 aimms-arrow-down12 aimms-arrow-down-left5 aimms-arrow-left12
aimms-arrow-up13 aimms-arrow-right13 aimms-arrow-down13 aimms-arrow-left13 aimms-arrow-up14
aimms-arrow-right14 aimms-arrow-down14 aimms-arrow-left14 aimms-circle-up5 aimms-circle-right5
aimms-circle-down5 aimms-circle-left5 aimms-circle-up6 aimms-circle-right6 aimms-circle-down6
aimms-circle-left6 aimms-arrow-up15 aimms-arrow-right15 aimms-arrow-down15 aimms-arrow-left15
aimms-arrow-up16 aimms-arrow-right16 aimms-arrow-down16 aimms-arrow-left16 aimms-menu-open
aimms-menu-open2 aimms-menu-close aimms-menu-close2 aimms-enter4 aimms-enter5 aimms-esc aimms-enter6
aimms-backspace aimms-backspace2 aimms-tab aimms-transmission aimms-transmission2 aimms-sort
aimms-sort2 aimms-move-up aimms-move-down aimms-sort-alpha-asc aimms-sort-alpha-desc
aimms-sort-numeric-asc aimms-sort-numberic-desc aimms-sort-amount-asc aimms-sort-amount-desc
aimms-sort-time-asc aimms-sort-time-desc aimms-battery-6 aimms-battery-5 aimms-battery-4
aimms-battery-3 aimms-battery-2 aimms-battery-1 aimms-battery-0 aimms-battery-charging
aimms-key-keyboard aimms-key-A aimms-key-up aimms-key-right aimms-key-down aimms-key-left
aimms-command aimms-shift aimms-ctrl aimms-opt aimms-checkbox-checked aimms-checkbox-unchecked
aimms-checkbox-partial aimms-square aimms-triangle aimms-triangle2 aimms-diamond3 aimms-diamond4
aimms-checkbox-checked2 aimms-checkbox-unchecked2 aimms-checkbox-partial2 aimms-radio-checked
aimms-radio-checked2 aimms-radio-unchecked aimms-toggle-on aimms-toggle-off aimms-checkmark-circle
aimms-circle aimms-circle2 aimms-circles aimms-circles2 aimms-crop aimms-crop2 aimms-make-group
aimms-ungroup aimms-vector aimms-vector2 aimms-rulers aimms-ruler aimms-pencil-ruler aimms-scissors
aimms-scissors2 aimms-scissors3 aimms-haircut aimms-comb aimms-filter aimms-filter2 aimms-filter3
aimms-filter4 aimms-font aimms-ampersand aimms-ligature aimms-ligature2 aimms-font-size
aimms-typography aimms-text-height aimms-text-width aimms-height2 aimms-width aimms-bold
aimms-underline aimms-italic aimms-strikethrough aimms-strikethrough2 aimms-font-size2 aimms-bold2
aimms-underline2 aimms-italic2 aimms-strikethrough3 aimms-omega aimms-sigma aimms-nbsp
aimms-page-break aimms-page-break2 aimms-superscript aimms-subscript aimms-superscript2
aimms-subscript2 aimms-text-color aimms-highlight aimms-pagebreak aimms-clear-formatting aimms-table
aimms-table2 aimms-insert-template aimms-pilcrow aimms-ltr aimms-rtl aimms-ltr2 aimms-rtl2
aimms-section aimms-paragraph-left aimms-paragraph-center aimms-paragraph-right
aimms-paragraph-justify aimms-paragraph-left2 aimms-paragraph-center2 aimms-paragraph-right2
aimms-paragraph-justify2 aimms-indent-increase aimms-indent-decrease aimms-paragraph-left3
aimms-paragraph-center3 aimms-paragraph-right3 aimms-paragraph-justify3 aimms-indent-increase2
aimms-indent-decrease2 aimms-share aimms-share2 aimms-new-tab aimms-new-tab2 aimms-popout
aimms-embed aimms-embed2 aimms-markup aimms-regexp aimms-regexp2 aimms-code aimms-circle-css
aimms-circle-code aimms-terminal aimms-unicode aimms-seven-segment-0 aimms-seven-segment-1
aimms-seven-segment-2 aimms-seven-segment-3 aimms-seven-segment-4 aimms-seven-segment-5
aimms-seven-segment-6 aimms-seven-segment-7 aimms-seven-segment-8 aimms-seven-segment-9 aimms-share3
aimms-share4 aimms-mail aimms-mail2 aimms-mail3 aimms-mail4 aimms-amazon aimms-google aimms-google2
aimms-google3 aimms-google-plus aimms-google-plus2 aimms-google-plus3 aimms-hangouts
aimms-google-drive aimms-facebook aimms-facebook2 aimms-instagram aimms-whatsapp aimms-spotify
aimms-telegram aimms-twitter aimms-vine aimms-vk aimms-renren aimms-sina-weibo aimms-rss aimms-rss2
aimms-youtube aimms-twitch aimms-vimeo aimms-vimeo2 aimms-lanyrd aimms-flickr aimms-flickr2
aimms-flickr3 aimms-flickr4 aimms-dribbble aimms-behance aimms-behance2 aimms-deviantart aimms-500px
aimms-steam aimms-steam2 aimms-dropbox aimms-onedrive aimms-github aimms-npm aimms-basecamp
aimms-trello aimms-wordpress aimms-joomla aimms-ello aimms-blogger aimms-blogger2 aimms-tumblr
aimms-tumblr2 aimms-yahoo aimms-yahoo2 aimms-tux aimms-appleinc aimms-finder aimms-android
aimms-windows aimms-windows8 aimms-soundcloud aimms-soundcloud2 aimms-skype aimms-reddit
aimms-hackernews aimms-wikipedia aimms-linkedin aimms-linkedin2 aimms-lastfm aimms-lastfm2
aimms-delicious aimms-stumbleupon aimms-stumbleupon2 aimms-stackoverflow aimms-pinterest
aimms-pinterest2 aimms-xing aimms-xing2 aimms-flattr aimms-foursquare aimms-yelp aimms-paypal
aimms-chrome aimms-firefox aimms-IE aimms-edge aimms-safari aimms-opera aimms-file-pdf
aimms-file-openoffice aimms-file-word aimms-file-excel aimms-libreoffice aimms-html-five
aimms-html-five2 aimms-css3 aimms-git aimms-codepen aimms-svg aimms-IcoMoon
```

## External references

- [Workflow panels (AIMMS docs)](https://documentation.aimms.com/webui/workflow-panels.html)
- [AIMMS icon list](https://documentation.aimms.com/_static/aimms-icons/icons-reference.html)
