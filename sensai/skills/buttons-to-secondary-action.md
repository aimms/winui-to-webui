---
name: buttons-to-secondary-action
description: Move some or all button widgets on an AIMMS WebUI page to the page's Secondary Actions (the page-action menu at the bottom right). The buttons are kept in the page's Unassigned widgets area; a StringParameter over webui::indexPageExtension/indexPageActionSpec and the secondarypageactions page setting are created. Use when the user asks to move, convert or replace buttons with secondary (page) actions, or mentions secondarypageactions, page actions, page extensions or indexPageActionSpec.
allowed-tools: Bash(python -I *buttons_to_secondary_action.py *), Bash(git status *), Bash(git check-ignore *), Read, Grep, Glob, Edit, Write
---

# Buttons to secondary actions

Moves some or all button widgets on a WebUI page to **secondary page
actions**: entries in the action menu at the bottom right of the page (see
[Configuring secondary actions](https://documentation.aimms.com/webui/page-settings.html#configuring-secondary-actions)).
Each moved button becomes one action with the same text and procedure. The
buttons themselves are **not deleted**: they go to the page's
**Unassigned widgets** area, where they no longer show but can be dragged back
in the WebUI editor. No other widget or page is touched.

Built from a working example (AIMMS 26.x, webui.json version 4.67.0): page
`home` with three buttons `button_wrk1..3` (procedures `pr_wrk1..3`), and page
`worked` offering the same three actions as secondary actions through
`sp_homepage_secondary_actions`.

This skill is a single file. The helper script it needs is included below in
[Helper script](#helper-script-buttons_to_secondary_actionpy). Before the first
step, write that code block verbatim to a temporary file (your scratchpad, or a
temp folder; not inside the user's project) named
`buttons_to_secondary_action.py`, and run it with
`python -I <that path> <subcommand> <webui.json> ...`. Do not embed the whole
helper in a long inline `python -c` command or generate such a command: copy
the code block itself into the temporary file, or extract that fenced code
block from this skill file with the file tools and then run the file. It uses
the standard library only. Hand-editing `webui.json` is error-prone, so use the
script for it. The `.ams` edit is yours.

Pass `--skill <path of this .md file>` to `move` and `check`: the script then
validates every icon against the [Available icons](#available-icons) list in
this file.

## Inputs to settle first

1. **Project paths.** Find `MainProject/WebUI/webui.json` and the model `.ams`
   (usually `MainProject/<name>.ams`). Ask if there are several.
2. **Page and buttons.** Run `list` (or `list --page <slug>`) to show each
   page's buttons with title, procedure and grid area. If the user didn't say
   which page or which buttons, ask. "All buttons" means `--all`: every button
   that is placed on the page (buttons already in Unassigned widgets are not
   taken). The order you pass in `--buttons` becomes the order in the menu.
   Pages converted from WinUI often carry leftover buttons that are already
   `UNASSIGNED`, titled with their own widget name or used for navigation
   (`Main Navigation`, page names, `Quit`), calling `giim::pr_action_sequence_...`
   procedures that are empty or only `webui::OpenPage`. When the user says
   "the action buttons", take the placed buttons that call real model
   procedures. Name the leftovers you skipped, but don't move them without
   being asked.
3. **Icons.** Buttons have no icon, but each action shows one. Pick one
   `aimms-...` icon per button that fits its title from the
   [Available icons](#available-icons) list below (grep this file for a word
   from the title), and write a JSON map `{"<widget uri>": "aimms-xyz"}` to a
   temporary file for `--icons`. Don't invent names; they are case-sensitive.
   A button without an entry gets the default icon (`aimms-office`); tell the
   user which buttons got it.
4. **Identifier.** Default `sp_<slug>_secondary_actions`; `--identifier` sets
   another. If the page already has secondary actions, the script reuses that
   identifier and appends after its last entry. Buttons whose procedure is
   already an action there get no new row; they are only moved.

## Procedure

1. **Safety.** Check `git status` and `git check-ignore` on both files:
   converted apps often sit in an ignored `work/` folder, so git can't restore
   them. Before each write the script copies `webui.json` to
   `webui.json.buttons-to-secondary-action.bak`. Copy the `.ams` yourself (for
   example to `<name>.ams.buttons-to-secondary-action.bak`) before editing it
   when it isn't tracked. Don't use an existing `webui.json.bak` to judge the
   diff: other skills leave older snapshots under that name. AIMMS does not
   need to be closed, but the WebUI rewrites `webui.json` on save: the user
   should not save from the WebUI editor while you work, and may need to
   reload or reopen the project before changes show.
2. **Preview.** Run
   `move <webui.json> --page <slug> --buttons <uri1,uri2> --icons map.json --skill <this .md> --ams <model.ams> --dry-run`
   (or `--all` instead of `--buttons`). Show the user the action list and
   every NOTE/WARN/ERROR:
   - **ERROR**: title bound to an identifier, no procedure action, or an icon
     not in the list. A title or procedure can't be copied as data: ask the
     user; `--force` moves anyway and leaves a placeholder for you to fix in
     the `.ams`. A wrong icon: pick another from the list.
   - **options not carried over**: anything other than title and action, such
     as a tooltip, styling or a `visible`/`disabled` binding. Secondary actions
     have only `displaytext`, `icon`, `procedure` and `state`. For visibility or
     enablement, see [Dynamic state](#dynamic-state).
   - More than 5 actions: AIMMS recommends about 5. More than 10: only 10 show.
3. **Apply.** Run the same command without `--dry-run`, with
   `--out snippet.ams` (write it to the same temporary folder). For each chosen
   button it sets the binding's `gridArea` to `Unassigned widgets` (creating the
   binding if there is none). The widget stays in the page's `widgets` list and
   its `widgets/<uri>` definition stays as it is. It adds `secondarypageactions`
   to the page. Rerunning is safe. Empty grid areas that result are not
   removed; tell the user.
4. **Write the model code.** The snippet is either a whole `StringParameter`
   declaration or, if the identifier already exists in the `.ams`, the rows to
   append. Put a new declaration near the procedures it calls or in a
   `DeclarationSection` such as `Page_Actions`. Keep the file's tab
   indentation, keep `Definition: { { ... } }`, and put no comma after the last
   entry. When appending, add a comma after the old last entry. See
   [Model declaration](#model-declaration-ams).
5. **Check.** Run
   `check <webui.json> --page <slug> --ams <model.ams> --skill <this .md>`.
   Fix every ERROR and report every WARN. See [Troubleshooting](#troubleshooting).
6. **Hand off.** You can't run AIMMS, so don't claim it works. Tell the user to
   reopen the project, compile (a compile error leaves the WebUI empty), open
   the page and confirm that the buttons are gone from the page, that they sit
   under Unassigned widgets in the page editor, and that the action menu at the
   bottom right shows each action with its icon and runs its procedure.

## What to report

State which buttons moved (and which were skipped, with the reason), the
identifier, the icons chosen (and any default icons), the files changed, what
`check` found, and what only the user can verify (icons render, procedures run).

## Formats

### Before: buttons on a page (webui.json)

The page lists the widget in `widgets` and places it in `bindings`. The widget
definition is a separate top-level `widgets/<uri>` object.

```json
"pages/home": {
  "aimms.widget.type": { "literal": "pagev2-grid" },
  "bindings": { "literal": [
    { "widgetUri": "button_wrk1", "gridArea": "area-a", "dndId": "area-abutton_wrk10" }
  ] },
  "layoutId": { "literal": "custom_..." },
  "widgets": { "literal": [
    { "uri": "button_wrk1", "layoutInfo": { "width": "2", "height": "1" } }
  ] }
},
"widgets/button_wrk1": {
  "action": { "literal": { "type": "procedure", "value": "pr_wrk1" } },
  "aimms.widget.type": { "literal": "button" },
  "name": { "literal": "button_wrk1" },
  "title": { "literal": "1 work" }
}
```

### After: page (webui.json)

The binding moves to Unassigned widgets (the `dndId` is left alone, as the
WebUI does when a widget is dragged there), and the page gets the
`secondarypageactions` setting. Page keys are written in alphabetical order.

```json
"pages/home": {
  "aimms.widget.type": { "literal": "pagev2-grid" },
  "bindings": { "literal": [
    { "widgetUri": "button_wrk1", "gridArea": "Unassigned widgets", "dndId": "area-abutton_wrk10" }
  ] },
  "layoutId": { "literal": "custom_..." },
  "secondarypageactions": {
    "aimms": {
      "contents": [ "sp_home_secondary_actions" ],
      "slices": [ {
        "identifier": "sp_home_secondary_actions",
        "slice": [
          { "index": "webui::indexPageExtension", "type": "free", "value": "webui::indexPageExtension" },
          { "index": "webui::indexPageActionSpec", "type": "free", "value": "webui::indexPageActionSpec" }
        ]
      } ]
    }
  },
  "widgets": { "literal": [
    { "uri": "button_wrk1", "layoutInfo": { "width": "2", "height": "1" } }
  ] }
}
```

`widgets/button_wrk1` is unchanged. The `secondarypageactions` object is what
the Page Settings > Page Extensions dialog writes too, so the two ways are
interchangeable.

### Model declaration (.ams)

```
StringParameter sp_home_secondary_actions {
	IndexDomain: (webui::indexPageExtension,webui::indexPageActionSpec);
	Definition: {
		{
			('1', 'displaytext'  ) : "1 work",
			('1', 'icon'         ) : "aimms-office",
			('1', 'procedure'    ) : "pr_wrk1",
			('1', 'state'        ) : "Active",

			('2', 'displaytext'  ) : "2 work",
			...
		}
	}
}
```

| Spec element | Value |
|---|---|
| `displaytext` | Menu text (lower case `displaytext`). Taken from the button title. |
| `icon` | Icon from [Available icons](#available-icons), with the `aimms-` prefix. |
| `procedure` | Procedure without arguments. Taken from the button action. |
| `state` | `Active`, `Inactive` (greyed out) or `Hidden`. The default is hidden, so always set it. |

The first index (`'1'`, `'2'`, ...) is the order in the menu. The WebUI shows at
most 10; AIMMS recommends about 5. The braces in `Definition: { ... }` are the
definition value itself; the inner `{ ... }` holds the data. No comma after the
last entry.

### Dynamic state

A button whose visibility or enablement was bound to the model (for example
`"visible": {"aimms": {"contents": ["p_canRun"]}}`) loses that behaviour as an
action. To keep it, the state must come from the model. Two options; ask the
user which:

- Give the declaration no `Definition` and fill it in a procedure (for example
  in `PostMainInitialization` and wherever `p_canRun` changes):
  `sp_x('1','state') := if p_canRun then "Active" else "Hidden" endif;`
- Keep the literal definition with state `Active`; the procedure itself checks
  the condition and shows a message.

`check` only reads literal rows. A parameter filled in a procedure gives a WARN
that the rows weren't checked.

### File writing

AIMMS writes `webui.json` as `json.dumps(indent=2, ensure_ascii=True)`: non-ASCII
is escaped (`©` becomes `©`), there is no trailing newline, and the line
endings are whatever git checked out (often CRLF on Windows). The script keeps
all of that, so the diff only shows the real change. Keep it too if you ever
edit the file outside the script.

## Troubleshooting

- **The WebUI is empty.** The model doesn't compile; check the declaration
  (trailing comma, unknown procedure, wrong index domain).
- **No action menu.** `secondarypageactions` is missing or not in the exact
  format (`check` verifies), or every action's `state` is empty or `Hidden`.
- **An action is missing.** Only the first 10 show; or its `state` is not
  `Active`/`Inactive`.
- **No icon.** The name must match the [Available icons](#available-icons)
  list exactly, with the `aimms-` prefix.
- **A button still shows.** Its binding's `gridArea` isn't `Unassigned widgets`
  (`check` warns when a button that is also an action is still placed). The
  WebUI rewrites `webui.json` on save; re-run `check` after the user saves in
  the WebUI if anything looks off.
- **Undo.** Drag the button back from Unassigned widgets in the page editor and
  remove its row from the StringParameter, or restore
  `webui.json.buttons-to-secondary-action.bak` (state right before the last write).

## Helper script (`buttons_to_secondary_action.py`)

Write this block verbatim to `buttons_to_secondary_action.py` in a temporary
folder before use. Do not change it while copying.

```python
#!/usr/bin/env python3
"""Helper for the buttons-to-secondary-action skill. Standard library only.

Moves button widgets on a WebUI page to the page's secondary actions (the
page-action menu at the bottom right). The buttons are not deleted: they go to
the page's 'Unassigned widgets' area, where they can be dragged back.

Subcommands (all take the path to MainProject/WebUI/webui.json first):

  list   <webui.json> [--page SLUG]
         pages with their buttons (title, procedure, area) and secondary actions
  move   <webui.json> --page SLUG (--buttons URI[,URI...] | --all)
         [--icons map.json] [--skill SKILL.md] [--identifier NAME]
         [--ams model.ams] [--force] [--out snippet.ams] [--dry-run]
         put the buttons in 'Unassigned widgets', attach the secondary actions
         to the page, and write the .ams snippet with the action rows
  check  <webui.json> --page SLUG [--ams model.ams] [--skill SKILL.md]
         static checks, exit code 1 on errors

Run with:  python -I buttons_to_secondary_action.py <subcommand> ...
webui.json is written like AIMMS writes it (indent=2, non-ASCII as \\uXXXX, no
trailing newline, the file's own line endings), so it round-trips byte for byte.
Before every write the current file is copied to
webui.json.buttons-to-secondary-action.bak.
"""
import argparse
import json
import re
import sys
from pathlib import Path

UNASSIGNED = "Unassigned widgets"
DEFAULT_ICON = "aimms-office"  # verified in a working example; pass --icons to choose others
VALID_STATES = {"Active", "Inactive", "Hidden"}
SPEC = ("displaytext", "icon", "procedure", "state")
MAX_SHOWN = 10        # WebUI shows at most 10 secondary actions
RECOMMENDED = 5       # AIMMS documentation recommends about five
PAGE_TYPES_WITH_ACTIONS = {"pagev2-grid", "pagev2"}  # normal pages; dialogs/side panels: warn

SLICE = [
    {"index": "webui::indexPageExtension", "type": "free", "value": "webui::indexPageExtension"},
    {"index": "webui::indexPageActionSpec", "type": "free", "value": "webui::indexPageActionSpec"},
]


def secondary_setting(identifier):
    return {"aimms": {"contents": [identifier], "slices": [{"identifier": identifier, "slice": SLICE}]}}


# ---------------------------------------------------------------- helpers
def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save(path, data):
    """Write webui.json the way AIMMS does: indent=2, no trailing newline, non-ASCII
    escaped as \\uXXXX. The file's existing line endings and escaping are kept,
    so the diff is only the real change."""
    p = Path(path)
    old = p.read_bytes()
    bak = p.with_name(p.name + ".buttons-to-secondary-action.bak")  # own name: other skills keep their own .bak
    bak.write_bytes(old)  # always the state right before this write
    raw_non_ascii = any(c > 127 for c in old)
    text = json.dumps(data, indent=2, ensure_ascii=not raw_non_ascii)
    if b"\r\n" in old:  # git autocrlf checkouts on Windows are CRLF
        text = text.replace("\n", "\r\n")
    p.write_text(text, encoding="utf-8", newline="")
    print(f"wrote {p} (state before this write: {bak.name})")


def walk(node, depth=0):
    yield node, depth
    for c in node.get("children", []):
        yield from walk(c, depth + 1)


def page_tree(data):
    try:
        return data["application"]["pages"]["literal"]
    except KeyError:
        sys.exit("error: no application.pages.literal in webui.json; is this a WebUI project file?")


def page_node(data, slug):
    for n, _ in walk(page_tree(data)):
        if n.get("slug") == slug:
            return n
    return None


def page_obj(data, slug):
    key = f"pages/{slug}"
    if key not in data:
        sys.exit(f"error: no '{key}' in webui.json. Run 'list' to see the pages.")
    return data[key]


def lit(obj, key, default=None):
    v = obj.get(key)
    if isinstance(v, dict) and "literal" in v:
        return v["literal"]
    return default


def page_widget_uris(page):
    return [w.get("uri") for w in (lit(page, "widgets") or [])]


def widget_type(data, uri):
    return lit(data.get(f"widgets/{uri}", {}), "aimms.widget.type")


def binding_of(page, uri):
    for b in lit(page, "bindings") or []:
        if b.get("widgetUri") == uri:
            return b
    return None


def area_of(page, uri):
    b = binding_of(page, uri)
    return b.get("gridArea") if b else None


def describe_button(data, uri):
    """Return (info, problems). info has uri, title, procedure, extra (unsupported options)."""
    w = data.get(f"widgets/{uri}", {})
    problems = []
    title = w.get("title")
    if isinstance(title, dict) and "literal" in title:
        title = title["literal"]
    elif title is None:
        title = uri
        problems.append("no title; the widget name is used as display text")
    else:
        problems.append(f"title is bound to the model ({json.dumps(title)}); display text needs manual work")
        title = None
    proc = None
    action = lit(w, "action")
    if isinstance(action, dict) and action.get("type") == "procedure":
        proc = action.get("value")
    elif lit(w, "procedure"):  # older button format
        proc = lit(w, "procedure")
    if not proc:
        problems.append(f"no procedure action found (action = {json.dumps(w.get('action'))})")
    handled = {"action", "aimms.widget.type", "name", "title", "procedure"}
    extra = sorted(k for k in w if k not in handled)
    return {"uri": uri, "title": title, "procedure": proc, "extra": extra}, problems


def parse_ams_param(text, ident):
    """Return (block text, rows {(ext, spec): value}) of a StringParameter, or (None, {})."""
    m = re.search(rf"StringParameter\s+{re.escape(ident)}\s*\{{.*?\n\s*\}}", text, re.S)
    if not m:
        return None, {}
    # the declaration ends at the first line holding only '}' at the declaration's indent
    start = m.start()
    line_start = text.rfind("\n", 0, start) + 1
    indent = text[line_start:start]
    end = re.compile(r"\n" + re.escape(indent) + r"\}").search(text, start)
    block = text[start:end.end()] if end else m.group(0)
    rows = {}
    for ext, spec, val in re.findall(r"\(\s*'([^']*)'\s*,\s*'([^']*)'\s*\)\s*:\s*\"((?:[^\"\\]|\\.)*)\"", block):
        rows[(ext, spec.lower())] = val
    return block, rows


def ams_procedures(text):
    return set(re.findall(r"^\s*Procedure\s+([A-Za-z_][\w:]*)", text, re.M))


def known_icons(skill_md):
    """Icon names from the 'Available icons' code block of the skill file."""
    text = Path(skill_md).read_text(encoding="utf-8")
    # anchored to the line start, so this line itself (inside the skill file) doesn't match
    m = re.search(r"^## Available icons$.*?^`{3}text\n(.*?)^`{3}", text, re.S | re.M)
    if not m:
        sys.exit(f"error: no 'Available icons' block in {skill_md}")
    return set(m.group(1).split())


def q(s):
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def insert_sorted(d, key, value):
    """Insert key into dict d at its alphabetical position (AIMMS writes page keys sorted)."""
    items = [(k, v) for k, v in d.items() if k != key]
    items.append((key, value))
    if list(d.keys()) == sorted(d.keys()):
        items.sort(key=lambda kv: kv[0])
    d.clear()
    d.update(items)


# ---------------------------------------------------------------- list
def cmd_list(a):
    data = load(a.webui)
    for n, depth in walk(page_tree(data)):
        slug = n.get("slug")
        if a.page and slug != a.page:
            continue
        page = data.get(f"pages/{slug}")
        head = f"{'  ' * depth}{n.get('name')}  [{slug}]  type={n.get('type', '-')}"
        if page is None:
            if a.page or n.get("type"):
                print(head)
            continue
        print(head)
        sec = page.get("secondarypageactions")
        if sec:
            print(f"{'  ' * depth}  secondary actions: {sec.get('aimms', {}).get('contents')}")
        for uri in page_widget_uris(page):
            if widget_type(data, uri) != "button":
                continue
            info, probs = describe_button(data, uri)
            area = area_of(page, uri)
            where = "UNASSIGNED" if area == UNASSIGNED else f"area={area}"
            print(f"{'  ' * depth}  button {uri}: title={info['title']!r} procedure={info['procedure']} {where}"
                  + (f" extra={info['extra']}" if info["extra"] else ""))
            for p in probs:
                print(f"{'  ' * depth}    ! {p}")


# ---------------------------------------------------------------- move
def cmd_move(a):
    data = load(a.webui)
    page = page_obj(data, a.page)
    node = page_node(data, a.page)
    warns, notes = [], []
    if node and node.get("type") not in PAGE_TYPES_WITH_ACTIONS:
        warns.append(f"page type '{node.get('type')}' may not support page actions (dialog or side panel?)")

    buttons_on_page = [u for u in page_widget_uris(page) if widget_type(data, u) == "button"]
    if a.all:
        chosen = [u for u in buttons_on_page if area_of(page, u) != UNASSIGNED]
        left = [u for u in buttons_on_page if u not in chosen]
        if left:
            notes.append(f"already in '{UNASSIGNED}', not taken by --all: {left}")
    else:
        chosen = [u.strip() for u in a.buttons.split(",") if u.strip()]
        bad = [u for u in chosen if u not in buttons_on_page]
        if bad:
            sys.exit(f"error: not a button on page '{a.page}': {bad}. Buttons there: {buttons_on_page}")
    if not chosen:
        sys.exit(f"error: no buttons to move on page '{a.page}'")

    # identifier: reuse an existing one on the page, else the given or derived name
    existing = page.get("secondarypageactions", {}).get("aimms", {}).get("contents") or []
    identifier = existing[0] if existing else (a.identifier or f"sp_{a.page}_secondary_actions")
    if existing and a.identifier and a.identifier != identifier:
        warns.append(f"page already uses '{identifier}'; --identifier '{a.identifier}' ignored")

    start, ams_rows, procs = 1, {}, None
    if a.ams:
        ams_text = Path(a.ams).read_text(encoding="utf-8-sig", errors="replace")
        block, ams_rows = parse_ams_param(ams_text, identifier)
        if block is not None:
            nums = [int(e) for e, _ in ams_rows if e.isdigit()]
            start = max(nums, default=0) + 1
        procs = ams_procedures(ams_text)
    elif existing:
        warns.append(f"page already has '{identifier}' but no --ams given; numbering starts at 1, "
                     "renumber after the existing entries when merging")
    done_procs = {v for (_, s), v in ams_rows.items() if s == "procedure"}

    icons = json.loads(Path(a.icons).read_text(encoding="utf-8")) if a.icons else {}
    valid_icons = known_icons(a.skill) if a.skill else None
    actions, errors = [], []
    for uri in chosen:
        info, probs = describe_button(data, uri)
        if info["procedure"] and info["procedure"] in done_procs:
            notes.append(f"{uri}: {identifier} already has an action for '{info['procedure']}'; "
                         "no new row, button only moved to Unassigned")
            info["skip_row"] = True
        for p in probs:
            (errors if ("needs manual" in p or "no procedure" in p) else warns).append(f"{uri}: {p}")
        if info["extra"]:
            warns.append(f"{uri}: options not carried over to the action: {info['extra']}")
        if uri not in icons:
            warns.append(f"{uri}: no icon given, using {DEFAULT_ICON}")
        info["icon"] = icons.get(uri, DEFAULT_ICON)
        if valid_icons is not None and info["icon"] not in valid_icons:
            errors.append(f"{uri}: icon '{info['icon']}' is not in the Available icons list")
        if procs is not None and info["procedure"] and info["procedure"] not in procs \
                and "::" not in info["procedure"]:
            warns.append(f"{uri}: procedure '{info['procedure']}' not found in {Path(a.ams).name}")
        actions.append(info)
    if errors and not a.force:
        for e in errors:
            print("ERROR", e)
        sys.exit("fix these first, or pass --force to move anyway (the .ams rows then need manual edits)")

    new_actions = [x for x in actions if not x.get("skip_row")]
    total = start - 1 + len(new_actions)
    if total > MAX_SHOWN:
        warns.append(f"{total} secondary actions; the WebUI shows only the first {MAX_SHOWN}")
    elif total > RECOMMENDED:
        warns.append(f"{total} secondary actions; AIMMS recommends about {RECOMMENDED}")

    # .ams snippet
    ind = "\t" * a.indent
    blocks = []
    for i, act in enumerate(new_actions, start):
        act["n"] = i
        rows = [("displaytext", act["title"] or f"<{act['uri']}>"), ("icon", act["icon"]),
                ("procedure", act["procedure"] or ""), ("state", "Active")]
        blocks.append(",\n".join(f"{ind}\t\t\t('{i}', {('%r' % k):<14}) : {q(v)}" for k, v in rows))
    body = ",\n\n".join(blocks)
    if not new_actions:
        snippet, mode = "", "none"
    elif ams_rows:
        snippet = (f"! Append these rows inside the Definition of the existing {identifier}\n"
                   f"! (add a comma after its current last entry):\n\n{body}\n")
        mode = "append"
    else:
        snippet = "\n".join([
            f"{ind}StringParameter {identifier} {{",
            f"{ind}\tIndexDomain: (webui::indexPageExtension,webui::indexPageActionSpec);",
            f"{ind}\tDefinition: {{",
            f"{ind}\t\t{{",
            body,
            f"{ind}\t\t}}",
            f"{ind}\t}}",
            f"{ind}}}",
        ]) + "\n"
        mode = "declare"

    # webui.json changes: buttons go to Unassigned widgets; nothing is deleted
    changes = []
    bindings = page.setdefault("bindings", {"literal": []}).setdefault("literal", [])
    for uri in chosen:
        b = binding_of(page, uri)
        if b is not None and b.get("gridArea") == UNASSIGNED:
            continue
        if b is None:
            bindings.append({"widgetUri": uri, "gridArea": UNASSIGNED, "dndId": UNASSIGNED + uri})
        else:
            # dndId is left alone: the WebUI does the same when a widget is dragged there
            b["gridArea"] = UNASSIGNED
        changes.append(f"pages/{a.page}: {uri} -> '{UNASSIGNED}'")
    want = secondary_setting(identifier)
    if page.get("secondarypageactions") != want:
        insert_sorted(page, "secondarypageactions", want)
        changes.append(f"pages/{a.page}: secondarypageactions -> {identifier}")

    # report
    print(f"page '{a.page}': {len(chosen)} button(s) to secondary actions '{identifier}'")
    for act in new_actions:
        print(f"  {act['n']}. {act['title']!r} -> {act['procedure']}  icon {act['icon']}  (from {act['uri']})")
    print("webui.json changes:\n  " + ("\n  ".join(changes) if changes else "(none)"))
    print(f".ams: {dict(declare='new declaration', append='append rows to existing', none='nothing to add')[mode]}"
          f" {identifier}")
    for n in notes:
        print("NOTE ", n)
    for w in warns:
        print("WARN ", w)
    for e in errors:
        print("ERROR", e, "(forced)")
    if a.dry_run:
        print("(dry run, nothing written)\n")
        print(snippet)
        return
    if snippet:
        if a.out:
            Path(a.out).write_text(snippet, encoding="utf-8")
            print(f"wrote {a.out}")
        else:
            print("\n" + snippet)
    if changes:
        save(a.webui, data)


# ---------------------------------------------------------------- check
def cmd_check(a):
    errs, warns = [], []
    data = load(a.webui)
    page = page_obj(data, a.page)
    node = page_node(data, a.page)
    if node is None:
        errs.append(f"'{a.page}' is not in the page tree (application.pages)")
    elif node.get("type") not in PAGE_TYPES_WITH_ACTIONS:
        warns.append(f"page type '{node.get('type')}' may not support page actions")

    sec = page.get("secondarypageactions")
    identifier = None
    if not sec:
        errs.append(f"pages/{a.page} has no secondarypageactions")
    else:
        contents = sec.get("aimms", {}).get("contents") or []
        if len(contents) != 1:
            errs.append(f"secondarypageactions.aimms.contents should hold one identifier, has {contents}")
        else:
            identifier = contents[0]
            if sec != secondary_setting(identifier):
                errs.append("secondarypageactions is not in the exact format (slices with "
                            "indexPageExtension / indexPageActionSpec, type free)")

    uris = page_widget_uris(page)
    for b in lit(page, "bindings") or []:
        if b.get("widgetUri") not in uris:
            errs.append(f"binding for '{b.get('widgetUri')}' but the widget is not in pages/{a.page}.widgets")
    for u in uris:
        if f"widgets/{u}" not in data:
            errs.append(f"page lists widget '{u}' but there is no widgets/{u}")

    if a.ams and identifier:
        text = Path(a.ams).read_text(encoding="utf-8-sig", errors="replace")
        block, rows = parse_ams_param(text, identifier)
        if block is None:
            errs.append(f"StringParameter {identifier} not found in {Path(a.ams).name}")
        else:
            if not re.search(r"IndexDomain\s*:\s*\(\s*webui::indexPageExtension\s*,\s*webui::indexPageActionSpec\s*\)", block):
                errs.append(f"{identifier}: IndexDomain must be (webui::indexPageExtension,webui::indexPageActionSpec)")
            if re.search(r",\s*\}", block):
                errs.append(f"{identifier}: trailing comma before a closing brace")
            procs = ams_procedures(text)
            valid_icons = known_icons(a.skill) if a.skill else None
            exts = sorted({e for e, _ in rows}, key=lambda s: (not s.isdigit(), int(s) if s.isdigit() else s))
            if not exts:
                warns.append(f"{identifier}: no literal rows found (defined by expression?); not checked")
            action_procs = set()
            for e in exts:
                r = {s: v for (x, s), v in rows.items() if x == e}
                for need in ("displaytext", "procedure", "state"):
                    if not r.get(need):
                        errs.append(f"{identifier} '{e}': missing {need}")
                if r.get("state") and r["state"] not in VALID_STATES:
                    errs.append(f"{identifier} '{e}': state '{r['state']}' not in {sorted(VALID_STATES)}")
                icon = r.get("icon")
                if icon and not icon.startswith("aimms-"):
                    warns.append(f"{identifier} '{e}': icon '{icon}' lacks the 'aimms-' prefix")
                if icon and valid_icons is not None and icon not in valid_icons:
                    errs.append(f"{identifier} '{e}': icon '{icon}' is not in the Available icons list")
                p = r.get("procedure")
                if p:
                    action_procs.add(p)
                    if p not in procs and "::" not in p:
                        errs.append(f"{identifier} '{e}': procedure '{p}' not found in the .ams")
                bad = set(r) - set(SPEC)
                if bad:
                    errs.append(f"{identifier} '{e}': unknown spec element(s) {sorted(bad)}")
            if len(exts) > MAX_SHOWN:
                warns.append(f"{len(exts)} actions; the WebUI shows only the first {MAX_SHOWN}")
            elif len(exts) > RECOMMENDED:
                warns.append(f"{len(exts)} actions; AIMMS recommends about {RECOMMENDED}")
            for u in uris:
                if widget_type(data, u) != "button":
                    continue
                info, _ = describe_button(data, u)
                if info["procedure"] in action_procs and area_of(page, u) != UNASSIGNED:
                    warns.append(f"button {u} is still placed on the page and also a secondary action "
                                 f"('{info['procedure']}')")

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

    s = sub.add_parser("list"); s.add_argument("webui"); s.add_argument("--page")
    s.set_defaults(f=cmd_list)

    s = sub.add_parser("move"); s.add_argument("webui")
    s.add_argument("--page", required=True, help="slug of the page")
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--buttons", help="comma-separated widget URIs of the buttons to move, in action order")
    g.add_argument("--all", action="store_true",
                   help=f"every button on the page that is not already in '{UNASSIGNED}'")
    s.add_argument("--icons", help="JSON file mapping widget URI -> icon name (aimms-...)")
    s.add_argument("--skill", help="this skill's .md file; icons are validated against its Available icons list")
    s.add_argument("--identifier", help="string parameter name (default sp_<slug>_secondary_actions)")
    s.add_argument("--ams", help="model .ams; used to continue numbering and to check procedures")
    s.add_argument("--force", action="store_true", help="move even when a button needs manual work")
    s.add_argument("--indent", type=int, default=1, help="leading tabs in the snippet")
    s.add_argument("--out", help="write the .ams snippet to this file")
    s.add_argument("--dry-run", action="store_true")
    s.set_defaults(f=cmd_move)

    s = sub.add_parser("check"); s.add_argument("webui")
    s.add_argument("--page", required=True); s.add_argument("--ams")
    s.add_argument("--skill", help="this skill's .md file; icons are validated against its Available icons list")
    s.set_defaults(f=cmd_check)

    a = ap.parse_args()
    a.f(a)


if __name__ == "__main__":
    main()
```

## Available icons

These are all 1609 names in `webui::AIMMSIcons`, read from the model
(`webui::AIMMSIcons := data { ... }`). An icon must be one of them, exactly as
written and with the `aimms-` prefix. Search this list (grep) for a name that
fits the button instead of guessing. Names are case-sensitive, e.g. `aimms-IcoMoon`.

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

- [Configuring secondary actions (AIMMS docs)](https://documentation.aimms.com/webui/page-settings.html#configuring-secondary-actions)
- [AIMMS icon list](https://documentation.aimms.com/_static/aimms-icons/icons-reference.html)
