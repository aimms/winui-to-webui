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
   Propose one per page from the
   [icon list](https://documentation.aimms.com/_static/aimms-icons/icons-reference.html)
   and write a JSON map `{"slug": "aimms-xyz"}` to a temporary file for
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

- Missing icon: check the name against the AIMMS icon list; it needs the `aimms-` prefix.
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

## External references

- [Workflow panels (AIMMS docs)](https://documentation.aimms.com/webui/workflow-panels.html)
- [AIMMS icon list](https://documentation.aimms.com/_static/aimms-icons/icons-reference.html)
