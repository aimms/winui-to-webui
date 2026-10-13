"""Lazy, per-component scaffolding for GeneratedInterfaceIdentifiers.

Each component gets its own nested `Module ... { Prefix: ...; ... }`, placed as the last
child of that component's own root - rather than one shared, project-registered library.
The main model and every library get their own DISTINCTLY-named/prefixed module -
GeneratedInterfaceIdentifiersMain/giim for the main model, GeneratedInterfaceIdentifiersLibrary
/giil for every library (that second name/prefix is still reused identically across every
library, same as before) - see get_prefix(). Earlier, every component (main model included)
reused the exact same name and prefix ("GeneratedInterfaceIdentifiers"/"gii"), which meant a
library could never bare-reference something declared in the main model's own copy (AIMMS
resolves a bare "gii::x" against the CURRENT scope's own "gii", not the main model's) - only
reachable via the "::"-prefixed absolute form, which is easy to get wrong or omit after a
later edit. Giving the main model a prefix no library ever reuses removes that trap entirely:
"giim::x" is unambiguous from anywhere in the project, no "::" needed.

These functions queue the AddIdentifier/SetAttribute commands into gii_dict["_edit_queue"]
(applied later via ams_file_editor.AmsProject, once AIMMS is done) the first time they're
actually needed for a given component, memoized on component_dict so a second call is a
no-op.

Every one of these scaffolding names (each module, its per-page Sections, its helper sets) is
deliberately reused identically across every library, so every command that names one of them as
a `parent`/`identifier` passes `file_hint=component_dict["AmsPath"]` to disambiguate which
component's copy is meant (see ams_file_editor.py).

Within a component's own module, every generated identifier/procedure is filed into a Section
named after the WebUI page slug that first needed it (see ensure_page_section) instead of being
dumped unsorted directly into the module - a large project can otherwise generate hundreds of
identifiers with no organization at all. An identifier reused by a later page is never moved or
duplicated into that page's own Section - see _note_page_usage/_register_usage, both of which
instead just note the extra page in the identifier's own Comment.
"""

import re
from typing import List, Optional, Tuple

import ams_file_editor as afe
import win_color

MAIN_MODULE_NAME = "GeneratedInterfaceIdentifiersMain"
MAIN_PREFIX = "giim"
LIBRARY_MODULE_NAME = "GeneratedInterfaceIdentifiersLibrary"
LIBRARY_PREFIX = "giil"
# Underscores stand in for the spaces "Page support for " reads as - plain AIMMS identifiers
# can't contain spaces (see ams_file_editor._IDENTIFIER_NAME_RE) - matching this project's own
# convention for multi-word Section names elsewhere (e.g. "App_Start_Stop", "Quantities_and_Units").
# ams_file_editor.AmsProject.prune_empty_sections() is scoped to exactly this prefix, so it only
# ever removes Sections this module itself generated - never a user's own pre-existing Section.
PAGE_SECTION_NAME_PREFIX = "Page_support_for_"
READONLY_SET_NAME = "s_readonly_values"
VISIBILITY_SET_NAME = "s_visibility_values"
ALL_COLORS_SET_NAME = "s_AllColors"
RED_PARAM_NAME = "p_Red"
GREEN_PARAM_NAME = "p_Green"
BLUE_PARAM_NAME = "p_Blue"
COLOR_SLUG_PARAM_NAME = "p_ColorSlug"


def get_prefix(component_dict: dict) -> str:
    """Returns the "giim"/"giil" prefix this component's own GeneratedInterfaceIdentifiers
    module has (or will have, once ensure_module() actually creates it) - a pure function of
    component_dict, safe to call before ensure_module()."""
    return MAIN_PREFIX if component_dict["Prefix"] == "" else LIBRARY_PREFIX


def _module_name(component_dict: dict) -> str:
    return MAIN_MODULE_NAME if component_dict["Prefix"] == "" else LIBRARY_MODULE_NAME


def ensure_module(gii_dict: dict, component_dict: dict) -> str:
    """Ensures this component has its own GeneratedInterfaceIdentifiers module (see get_prefix()
    for which name/prefix), as the last child of its own root Model/LibraryModule. Returns its
    name - the parent to use for anything that today would sit directly in the shared library
    (e.g. ad-hoc procedures)."""
    module_name = _module_name(component_dict)
    ams_path = component_dict["AmsPath"]
    if not component_dict.get("_gii_module_ready"):
        root_name = afe.find_root_identifier(ams_path)
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=module_name, type="module", parent=root_name, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=module_name, attribute="Prefix", value=get_prefix(component_dict), file_hint=ams_path))
        # Every identifier this module generates is either a display-only support parameter or
        # dead once conversion is done (e.g. gii::sp_libraryLocation, initialized fresh from
        # DirectoryOfLibraryProject on every LibraryInitialization) - none of it belongs in a
        # saved case/data file, same as the old central GeneratedInterfaceIdentifiersLibrary
        # LibraryModule template already declared (see GeneratedInterfaceIdentifiersLibrary/
        # GeneratedInterfaceIdentifiers.ams, "Property: NoSave;" - that file itself is a stale,
        # no-longer-copied-in leftover from before each component got its own nested module, but
        # confirms the real AIMMS syntax/precedent).
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=module_name, attribute="Property", value="NoSave", file_hint=ams_path))
        component_dict["_gii_module_ready"] = True
    return module_name


def ensure_page_section(gii_dict: dict, component_dict: dict, page_slug: str) -> str:
    """Ensures a Section "Page_support_for_<page_slug>" (PAGE_SECTION_NAME_PREFIX) exists for the
    given WebUI page, and returns its name to use as the `parent` for any identifier/procedure
    generated while converting that page.

    Nested to mirror WinUI's own PageManager.xml page tree, rather than sitting flat as a direct
    child of the module: a page's Section is created INSIDE its own parent page's Section
    (recursively, ensuring every ancestor's Section exists first), falling back to a direct child
    of the module only for a top-level page (or one with no recorded parent at all - see below).
    win_pagemanager.process_page_xml_node populates gii_dict["_page_parent_slug"][(id(
    component_dict), page_slug)] with each page's immediate parent slug (None for a top-level
    page) as PageManager.xml is walked, well before any widget on that page can need a Section -
    a page whose own parent's Section doesn't exist yet is entirely normal (PageManager.xml's
    children are fully converted before their own parent page's widgets are, see
    process_page_xml_node), which is exactly why this recurses to create it on demand instead of
    assuming it's already there.

    Filing generated identifiers by the page that actually needs them (rather than dumping every
    one of them, unsorted, straight into the module) keeps a large project's generated
    identifiers navigable - every ensure_*/dedup_* call below that mints a new identifier takes a
    page_slug for exactly this. An identifier reused by a LATER page is never moved or
    duplicated into that page's own Section - see _note_page_usage and _register_usage, both of
    which instead just note the extra page in the identifier's own Comment, leaving it in place
    under whichever page's Section first needed it.

    A Section is purely an organizational/visual grouping in AIMMS, not a namespace - unlike the
    module itself, it never appears in a qualified reference, so nesting identifiers one or more
    levels deeper here needs no change anywhere identifiers are referenced (still "{prefix}::{gii
    prefix}::{name}", exactly as when they sat directly in the module).

    Falls back to the module itself when page_slug is empty, or has no recorded parent - project-
    wide generation with no single introducing page (see ensure_all_colors_values/
    ensure_color_literal_elements/identifier_element_text.generate_pr_adaptNamesForPresentationInWebUI,
    none of which route through here: each runs once, after every page has already been
    converted, aggregating across the whole project rather than being triggered by any one page)
    lands the same way a top-level page's own Section does. Memoized per (component, page_slug).
    Returns the Section's bare name."""
    module_name = ensure_module(gii_dict, component_dict)
    if page_slug == "":
        return module_name
    ams_path = component_dict["AmsPath"]
    cache = gii_dict.setdefault("_page_section_cache", {})
    cache_key = (id(component_dict), page_slug)
    if cache_key not in cache:
        parent_page_slug = gii_dict.get("_page_parent_slug", {}).get(cache_key)
        parent = ensure_page_section(gii_dict, component_dict, parent_page_slug) if parent_page_slug else module_name
        section_name = f"{PAGE_SECTION_NAME_PREFIX}{_sanitize_identifier_fragment(page_slug)}"
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=section_name, type="section", parent=parent, file_hint=ams_path))
        cache[cache_key] = section_name
    return cache[cache_key]


def _note_page_usage(gii_dict: dict, component_dict: dict, registry_name: str, cache_key, identifier_name: str, page_slug: str) -> None:
    """Shared helper for the simple, name-based ensure_* caches below (ensure_not_parameter,
    ensure_hidden_condition_parameter, ensure_indicator_index, ensure_indicator_parameter,
    ensure_suffix_parameter, ensure_readonly_values, ensure_visibility_values): the identifier
    itself is filed under whichever page's Section first needed it (see ensure_page_section) and
    never moves - a LATER call for the same cache_key from a DIFFERENT page_slug instead just
    queues a Comment noting every extra page that references it, the same spirit as
    dedup_parameter/dedup_procedure's own usage-comment tracking (see _register_usage), just
    keyed by page rather than by a caller-supplied free-text usage description. A no-op the first
    time (nothing to "also" note yet) and for a page_slug already recorded.

    :param registry_name: gii_dict key for this family's own page-tracking registry - callers
        must each use a distinct registry_name, same rule as _ensure_sanitized_expr_parameter's
        cache_name."""
    registry = gii_dict.setdefault(registry_name, {})
    key = (id(component_dict), cache_key)
    pages = registry.setdefault(key, [])
    if page_slug in pages:
        return
    pages.append(page_slug)
    if len(pages) > 1:
        comment_text = "Also used on page(s): " + ", ".join(f"'{p}'" for p in pages[1:])
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=identifier_name, attribute="Comment",
                                                          value=f'"{comment_text}"', file_hint=component_dict["AmsPath"]))


def ensure_readonly_values(gii_dict: dict, component_dict: dict, page_slug: str) -> str:
    """Ensures this component's own s_readonly_values helper set, filed under page_slug's own
    Section the first time any page needs it (see ensure_page_section) - reused as-is, never
    duplicated or moved, by every later page that also needs a readonly condition (see
    _note_page_usage)."""
    ams_path = component_dict["AmsPath"]
    if not component_dict.get("_gii_readonly_set_ready"):
        parent = ensure_page_section(gii_dict, component_dict, page_slug)
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=READONLY_SET_NAME, type="set", parent=parent, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=READONLY_SET_NAME, attribute="Definition", value="data { False, True }", file_hint=ams_path))
        component_dict["_gii_readonly_set_ready"] = True
    _note_page_usage(gii_dict, component_dict, "_readonly_values_pages", (), READONLY_SET_NAME, page_slug)
    return READONLY_SET_NAME


def ensure_visibility_values(gii_dict: dict, component_dict: dict, page_slug: str) -> str:
    """Ensures this component's own s_visibility_values helper set, filed under page_slug's own
    Section the first time any page needs it (see ensure_page_section) - reused as-is, never
    duplicated or moved, by every later page that also needs a visibility condition (see
    _note_page_usage)."""
    ams_path = component_dict["AmsPath"]
    if not component_dict.get("_gii_visibility_set_ready"):
        parent = ensure_page_section(gii_dict, component_dict, page_slug)
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=VISIBILITY_SET_NAME, type="set", parent=parent, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=VISIBILITY_SET_NAME, attribute="Definition", value="data { Default, 'Never Show', 'Always Show' }", file_hint=ams_path))
        component_dict["_gii_visibility_set_ready"] = True
    _note_page_usage(gii_dict, component_dict, "_visibility_values_pages", (), VISIBILITY_SET_NAME, page_slug)
    return VISIBILITY_SET_NAME


def _wrap_data_pairs(pairs: list, max_line_length: int = 128) -> str:
    """Wraps a `data { <pairs> }` literal (pairs already formatted, e.g. "'red' : 255") across
    multiple lines, each kept within max_line_length characters - a single very long line (like
    a hundred-plus-color set or parameter) can otherwise render as empty in the AIMMS IDE's
    attribute editor.

    Packs whole pairs onto each line and never splits inside one - textwrap.wrap() on the joined
    string would happily break inside a multi-word quoted element name like 'old text font'
    (wherever the wrap column happened to fall), leaving the two halves on separate lines. AIMMS
    then reads that as a different element than the intact 'old text font' literal used
    elsewhere (e.g. in p_Red/p_Green/p_Blue's own Definition, wrapped at a different column), causing
    a spurious "element ... is not in the range set" error."""
    lines = []
    current = ""
    for i, pair in enumerate(pairs):
        piece = pair if i == len(pairs) - 1 else pair + ","
        if current and len(current) + 1 + len(piece) > max_line_length - 8:
            lines.append(current)
            current = piece
        else:
            current = f"{current} {piece}" if current else piece
    if current:
        lines.append(current)
    lines[0] = "data { " + lines[0]
    lines[-1] = lines[-1] + " }"
    return "\n".join(lines)


def _wrap_data_literal(elements: list, max_line_length: int = 128) -> str:
    """Wraps a `data { 'a', 'b', ... }` set literal - see _wrap_data_pairs."""
    return _wrap_data_pairs([f"'{element}'" for element in elements], max_line_length)


def ensure_all_colors_values(gii_dict: dict, main_model_component_dict: dict, color_rgb: dict) -> str:
    """Ensures the main model's own s_AllColors set and p_Red/p_Green/p_Blue/p_ColorSlug(i_color)
    parameters - color_rgb is the merged {name: (r, g, b)} registry: the 147 standard CSS/HTML
    color names (https://www.w3schools.com/Tags/ref_colornames.asp) plus whatever project-
    specific colors were discovered from WinUI page styling and each component's own
    Settings/UserColors.xml (see win_color_scan.py and win_object_tools.py's merge of the two,
    which applies the w3c-names-win-on-clash priority). Needed because an identifier ranged over
    AIMMS's built-in AllColors system set isn't usable as-is by WebUI: any such identifier used
    for data coloring has its own Range repointed to s_AllColors instead (see
    win_object_tools.investigate_contents).

    s_AllColors element names are kept exactly as discovered, spaces and all - some pre-existing
    identifier already ranged over AllColors can have a Definition that quotes a multi-word
    built-in member (e.g. 'light grey') verbatim, and repointing its Range without also rewriting
    that formula would break if the name here didn't match exactly. p_ColorSlug maps every name
    to a CSS-safe single-token slug instead (see win_color.css_class_slug) - win_object_tools.py's
    "color-%s" annotation formula goes through p_ColorSlug rather than embedding a name that may
    not itself be a valid CSS class-name token.

    Always created in the main model, regardless of which component the identifiers being
    repointed/colored live in - referencing it is then always the unambiguous "giim::s_AllColors"
    (or giim::p_Red/p_Green/p_Blue/p_ColorSlug), from anywhere in the project."""
    module_name = ensure_module(gii_dict, main_model_component_dict)
    ams_path = main_model_component_dict["AmsPath"]
    if not main_model_component_dict.get("_gii_all_colors_set_ready"):
        color_names = sorted(color_rgb.keys())
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=ALL_COLORS_SET_NAME, type="set", parent=module_name, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=ALL_COLORS_SET_NAME, attribute="Index", value="i_color", file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=ALL_COLORS_SET_NAME, attribute="Definition", value=_wrap_data_literal(color_names), file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=ALL_COLORS_SET_NAME, attribute="Comment",
            value='"The 147 standard CSS/HTML color names (see https://www.w3schools.com/Tags/ref_colornames.asp), '
                  'merged with any project-specific colors found in WinUI page styling and Settings/UserColors.xml - '
                  'duplicated locally because AIMMS\'s built-in AllColors system set is not usable as-is by WebUI."',
            file_hint=ams_path))

        for param_name, channel in ((RED_PARAM_NAME, 0), (GREEN_PARAM_NAME, 1), (BLUE_PARAM_NAME, 2)):
            gii_dict["_edit_queue"].append(afe.AddIdentifier(name=param_name, type="parameter", parent=module_name, file_hint=ams_path))
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="IndexDomain", value="i_color", file_hint=ams_path))
            pairs = [f"'{name}' : {color_rgb[name][channel]}" for name in color_names]
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Definition", value=_wrap_data_pairs(pairs), file_hint=ams_path))

        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=COLOR_SLUG_PARAM_NAME, type="string parameter", parent=module_name, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=COLOR_SLUG_PARAM_NAME, attribute="IndexDomain", value="i_color", file_hint=ams_path))
        slug_pairs = [f'\'{name}\' : "{win_color.css_class_slug(name)}"' for name in color_names]
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=COLOR_SLUG_PARAM_NAME, attribute="Definition", value=_wrap_data_pairs(slug_pairs), file_hint=ams_path))

        main_model_component_dict["_gii_all_colors_set_ready"] = True
    return ALL_COLORS_SET_NAME


_UNSAFE_IDENT_CHARS_RE = re.compile(r"[^A-Za-z0-9_]")


def _color_literal_param_name(color_name: str) -> str:
    """Turns an s_AllColors element name into a valid AIMMS identifier fragment - not every
    color name is one already (a UserColor like "default selection" has a space)."""
    safe = _UNSAFE_IDENT_CHARS_RE.sub("_", color_name)
    if not safe or safe[0].isdigit():
        safe = f"_{safe}"
    return f"ep_color_literal_{safe}"


def register_color_literal(gii_dict: dict, color_name: str) -> str:
    """Records that `color_name` (an s_AllColors element that was found as a literal RGB value
    or a quoted color name, rather than an existing AllColors-ranged identifier - see
    win_object_tools.investigate_contents's color handling) needs its own ElementParameter,
    realized later by ensure_color_literal_elements() once the main model's own component_dict
    is known. Returns the fully-qualified reference to use right away: safe to embed as text
    immediately, since the identifier only needs to actually exist by the time
    ams_file_editor.AmsProject.apply() runs, not at the moment this reference is queued.

    Giving a literal color its own ElementParameter (Range: s_AllColors) - rather than embedding
    a bare quoted element literal directly in a formatString(...) call - is what AIMMS needs to
    resolve "the second argument is of type element" formatting: a bare quoted literal doesn't
    carry a range set on its own."""
    gii_dict.setdefault("_color_literal_names", set()).add(color_name)
    return f"{MAIN_PREFIX}::{_color_literal_param_name(color_name)}"


_UNSAFE_NOT_PARAM_CHARS_RE = re.compile(r"[^A-Za-z0-9_]")


def _sanitize_identifier_fragment(text: str) -> str:
    """Turns arbitrary identifier/expression text into a valid AIMMS identifier fragment - used
    for the part of a generated name derived from something else's own name/expression (see
    ensure_not_parameter, ensure_indicator_index, ensure_indicator_parameter)."""
    safe = _UNSAFE_NOT_PARAM_CHARS_RE.sub("_", text.strip())
    if not safe or safe[0].isdigit():
        safe = f"_{safe}"
    return safe


def _ensure_sanitized_expr_parameter(gii_dict: dict, component_dict: dict, page_slug: str, cache_name: str, name_prefix: str,
                                      source_expr: str, definition: str, range_value: Optional[str] = None,
                                      id_type: str = "parameter") -> str:
    """Shared core for ensure_not_parameter, ensure_hidden_condition_parameter and
    ensure_image_path_parameter: mints (or reuses, memoized per (component, source_expr)) an
    identifier of type `id_type` named "<name_prefix><sanitized source_expr>", filed under
    page_slug's own Section (see ensure_page_section) the first time any page needs it. Returns
    the bare name - qualify with get_prefix(component_dict) + "::" at the call site, same as
    READONLY_SET_NAME/VISIBILITY_SET_NAME above.

    _sanitize_identifier_fragment replaces every unsafe character with the same single '_', so
    two textually different source expressions can legitimately collapse onto the same base
    name (e.g. "...)=CARD(...)" and "...)<CARD(...)" both turn '=' / '<' into '_'). Disambiguated
    the same way aimms_slug.aimms_slug() does: an incrementing numeric suffix per component,
    tried until a name not already owned by some *other* source_expr is found.

    A later call for the same source_expr from a DIFFERENT page_slug reuses the identifier as-is
    (never moves it into that page's Section) and just notes the extra page in its Comment - see
    _note_page_usage.

    :param cache_name: gii_dict key for this family's own memoization cache - callers must each
        use a distinct cache_name (ensure_not_parameter, ensure_hidden_condition_parameter and
        ensure_image_path_parameter mint semantically different identifiers, even when given the
        same source_expr, so they must never share one cache or one name-ownership map).
    :param id_type: Declared AIMMS type to create - "parameter" (the default, used by
        ensure_not_parameter/ensure_hidden_condition_parameter) or "string parameter" (used by
        ensure_image_path_parameter)."""
    ams_path = component_dict["AmsPath"]
    cache = gii_dict.setdefault(cache_name, {})
    cache_key = (id(component_dict), source_expr)
    if cache_key not in cache:
        parent = ensure_page_section(gii_dict, component_dict, page_slug)
        base_name = f"{name_prefix}{_sanitize_identifier_fragment(source_expr)}"
        owners = gii_dict.setdefault(f"{cache_name}_owners", {}).setdefault(id(component_dict), {})
        param_name = base_name
        suffix = 2
        while owners.get(param_name, source_expr) != source_expr:
            param_name = f"{base_name}_{suffix}"
            suffix += 1
        owners[param_name] = source_expr
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=param_name, type=id_type, parent=parent, file_hint=ams_path))
        if range_value is not None:
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Range", value=range_value, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Definition", value=definition, file_hint=ams_path))
        cache[cache_key] = param_name
    param_name = cache[cache_key]
    _note_page_usage(gii_dict, component_dict, f"{cache_name}_pages", source_expr, param_name, page_slug)
    return param_name


def ensure_not_parameter(gii_dict: dict, component_dict: dict, page_slug: str, source_expr: str) -> str:
    """Ensures a binary Parameter p_Not<source_expr> (Definition: `not <source_expr>`) exists in
    this component's own GeneratedInterfaceIdentifiers module, for a WebUI widget whose WinUI
    <Hidden> condition has no existing "opposite" parameter to reuse as its "widget.visible"
    binding (WinUI's Hidden and WebUI's widget.visible have opposite polarity - see
    win_object_tools.resolve_widget_visibility). Memoized per (component, source_expr) so every
    widget sharing the same Hidden condition reuses one negation parameter."""
    return _ensure_sanitized_expr_parameter(gii_dict, component_dict, page_slug, "_not_param_cache", "p_Not",
                                             source_expr, f"not {source_expr}", range_value="binary")


def ensure_hidden_condition_parameter(gii_dict: dict, component_dict: dict, page_slug: str, body_expr: str) -> str:
    """Ensures a Parameter p_hidden_<body_expr> (Definition: `body_expr`) exists in this
    component's own GeneratedInterfaceIdentifiers module, for a WinUI <Hidden> condition written
    with the "VALUE := <body>" dynamic-substitution form (see win_object_tools.
    resolve_widget_visibility): unlike a plain boolean-expression Hidden condition, that raw
    "VALUE := ..." text is WinUI-only pseudo-syntax and isn't itself valid inside an AIMMS
    Definition, so <body> alone becomes this parameter's Definition. The caller then wraps a
    reference to it in its own ensure_not_parameter negation Parameter, the same as any other
    Hidden condition - "widget.visible" only accepts a bare identifier reference, never a "not
    <ref>" expression string. Memoized per (component, body_expr) so every widget sharing the
    same Hidden condition reuses one parameter."""
    return _ensure_sanitized_expr_parameter(gii_dict, component_dict, page_slug, "_hidden_condition_param_cache",
                                             "p_hidden_", body_expr, body_expr)


def ensure_indicator_index(gii_dict: dict, component_dict: dict, page_slug: str, domain_set: str) -> str:
    """Ensures an Index i_indicator_<domain_set> (Range: domain_set) exists in this component's
    own GeneratedInterfaceIdentifiers module, filed under page_slug's own Section the first time
    any page needs it (see ensure_page_section) - the shared iteration index every binary
    indicator Parameter displaying a Set against this same domain set is built over (see
    ensure_indicator_parameter and win_object_tools._substitute_set_indicator_reference: WinUI
    can display a raw Set directly in a Table or Selection Object, but WebUI can't bind to one,
    only to an ordinary indexed Parameter). Memoized per (component, domain_set) so every Set
    displayed against the same domain shares one index - reused as-is, never duplicated or moved,
    by every later page (see _note_page_usage). Returns the bare name.

    :param gii_dict: Runtime library dictionary; any new-identifier commands are queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param page_slug: Slug of the WebUI page that (for this call) needs the index - see
        win_object_tools.page_slug_from_stable_id.
    :type page_slug: str
    :param domain_set: The (already namespace-qualified) set the index ranges over.
    :type domain_set: str
    :return: The bare Index name.
    :rtype: str
    """
    ams_path = component_dict["AmsPath"]
    cache = gii_dict.setdefault("_indicator_index_cache", {})
    cache_key = (id(component_dict), domain_set)
    if cache_key not in cache:
        parent = ensure_page_section(gii_dict, component_dict, page_slug)
        index_name = f"i_indicator_{_sanitize_identifier_fragment(domain_set)}"
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=index_name, type="index", parent=parent, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=index_name, attribute="Range", value=domain_set, file_hint=ams_path))
        cache[cache_key] = index_name
        # Nested inside this component's own GeneratedInterfaceIdentifiers module - see
        # is_synthetic_index for why that matters to a caller registering its
        # webui::IdentifierElementText fallback text.
        gii_dict.setdefault("_synthetic_index_names", set()).add((id(component_dict), index_name))
        # Reverse of `cache` (domain_set -> index_name), keyed the same way - see
        # indicator_index_domain_set, which a Pivot Table's own row/column placement needs
        # (win_object_tools.investigate_contents): the WinUI IDE's .DeveloperState
        # (win_pivot_state.py) records a relation's row/column arrangement by each dimension's
        # own domain Set name (e.g. "s_u"), never by this freshly minted Index ("i_indicator_s_u").
        gii_dict.setdefault("_indicator_index_domain_sets", {})[(id(component_dict), index_name)] = domain_set
    index_name = cache[cache_key]
    _note_page_usage(gii_dict, component_dict, "_indicator_index_pages", domain_set, index_name, page_slug)
    return index_name


def indicator_index_domain_set(gii_dict: dict, component_dict: dict, index_name: str) -> Optional[str]:
    """The domain Set an indicator Index (see ensure_indicator_index) was minted to range over,
    if index_name is one of this component's synthetic indicator indices - None otherwise (the
    common case: an ordinary, already-declared model Index, which needs no such translation).

    :param gii_dict: Runtime library dictionary; the synthetic-identifier registry lives here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param index_name: The bare Index name being looked up.
    :type index_name: str
    :return: The domain Set's own name, or None if index_name isn't one of this component's
        indicator indices.
    :rtype: Optional[str]
    """
    return gii_dict.get("_indicator_index_domain_sets", {}).get((id(component_dict), index_name))


def is_synthetic_index(gii_dict: dict, component_dict: dict, index_name: str) -> bool:
    """True when index_name is itself a synthetic Index minted by ensure_indicator_index (so it
    lives nested inside this component's own GeneratedInterfaceIdentifiers module, and needs that
    module's own prefix to be a valid webui::IdentifierElementText key - see
    win_object_tools.investigate_contents). False for an ordinary, already-declared model Index -
    including one that merely happens to be the IndexDomain of a synthetic Parameter such as
    ensure_suffix_parameter's (that Parameter is new, but its own indices are real, top-level
    ones inherited from the identifier it stands in for, not nested inside the giim/giil module
    themselves)."""
    return (id(component_dict), index_name) in gii_dict.get("_synthetic_index_names", set())


def qualify_synthetic_index(gii_dict: dict, component_dict: dict, index_name: str) -> str:
    """Fully-qualifies index_name (the library's own project prefix, if any, plus giim/giil) when
    it's a synthetic Index minted into this component's own GeneratedInterfaceIdentifiers module
    (see ensure_indicator_index/is_synthetic_index) - any reference to it OUTSIDE that module (a
    WebUI widget's own content slice, row/column/header partition list, or displaydomain -
    win_object_tools.investigate_contents/web_page.add_data_widget - or, for a library, even
    outside that library's own project) needs this qualified form: a bare "i_indicator_s_u"
    doesn't resolve there, only "giim::i_indicator_s_u" (or "gui::giil::i_indicator_s_u" from
    outside the library) does - same lesson as the generated indicator Parameter's own reference
    (win_object_tools._substitute_set_indicator_reference) and its webui::IdentifierElementText
    fallback text. An ordinary, already-declared model Index is returned unchanged.

    :param gii_dict: Runtime library dictionary; the synthetic-identifier registry lives here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param index_name: The bare Index name to potentially qualify.
    :type index_name: str
    :return: The qualified reference, or index_name unchanged when it isn't synthetic.
    :rtype: str
    """
    if not is_synthetic_index(gii_dict, component_dict, index_name):
        return index_name
    prefix_parts = [p for p in (component_dict['Prefix'], get_prefix(component_dict)) if p]
    return "::".join(prefix_parts + [index_name])


def ensure_indicator_parameter(gii_dict: dict, component_dict: dict, page_slug: str, display_set: str, index_names: List[str]) -> str:
    """Ensures a binary Parameter bp_indicator_<display_set> (IndexDomain: index_names, Range:
    binary, Definition: "1 $ ( index_names... in display_set )") exists in this component's own
    GeneratedInterfaceIdentifiers module, filed under page_slug's own Section the first time any
    page needs it (see ensure_page_section) - a WebUI-displayable stand-in for a WinUI Table or
    Selection Object bound directly to display_set (see ensure_indicator_index and
    win_object_tools._substitute_set_indicator_reference). Memoized per (component, display_set)
    so the same set is never given two indicator parameters - reused as-is, never duplicated or
    moved, by every later page (see _note_page_usage). Returns the bare name.

    display_set is usually a plain Set (one entry in index_names, membership tested directly -
    "index_name in display_set"), but can also be a "relation" Set declared with a tuple
    SubsetOf, e.g. "Set s_uvw { SubsetOf: (s_u,s_v,s_w); }" - one entry in index_names per
    dimension, membership tested as a tuple - "(i_a,i_b,i_c) in display_set" - see
    win_object_tools._substitute_set_indicator_reference for how a WinUI reference to either
    shape reaches here.

    :param gii_dict: Runtime library dictionary; any new-identifier commands are queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param page_slug: Slug of the WebUI page that (for this call) needs the parameter - see
        win_object_tools.page_slug_from_stable_id.
    :type page_slug: str
    :param display_set: The (already namespace-qualified) set whose membership is indicated.
    :type display_set: str
    :param index_names: The bare Index name(s) to range over, in display_set's own tuple order
        (see ensure_indicator_index) - each must already range over the matching dimension of
        display_set's own domain.
    :type index_names: List[str]
    :return: The bare Parameter name.
    :rtype: str
    """
    ams_path = component_dict["AmsPath"]
    cache = gii_dict.setdefault("_indicator_param_cache", {})
    cache_key = (id(component_dict), display_set)
    if cache_key not in cache:
        parent = ensure_page_section(gii_dict, component_dict, page_slug)
        param_name = f"bp_indicator_{_sanitize_identifier_fragment(display_set)}"
        membership_ref = index_names[0] if len(index_names) == 1 else f"({', '.join(index_names)})"
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=param_name, type="parameter", parent=parent, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="IndexDomain", value=", ".join(index_names), file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Range", value="binary", file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Definition",
                                                          value=f"1 $ ( {membership_ref} in {display_set} )", file_hint=ams_path))
        cache[cache_key] = param_name
        # A freshly generated identifier only exists as a queued text edit (see ams_file_editor.py,
        # applied once AIMMS is done) - the LIVE AIMMS session used elsewhere in this run for
        # modeledit_aimmspy2.getDim/getDomainIndex can't see it yet, and would report it as
        # undeclared. Record its known dimension/domain-index names here so callers that need
        # them (win_object_tools.investigate_contents, web_page.add_data_widget) can use this
        # instead of querying the live model - see synthetic_domain_indices().
        gii_dict.setdefault("_synthetic_dims", {})[(id(component_dict), param_name)] = list(index_names)
    param_name = cache[cache_key]
    _note_page_usage(gii_dict, component_dict, "_indicator_param_pages", display_set, param_name, page_slug)
    return param_name


def ensure_suffix_parameter(gii_dict: dict, component_dict: dict, page_slug: str, bare_name: str, suffix: str,
                             index_names: List[str], definition: str) -> str:
    """Ensures a Parameter p_<bare_name>_<suffix> (IndexDomain: index_names, Definition:
    definition) exists in this component's own GeneratedInterfaceIdentifiers module, filed under
    page_slug's own Section the first time any page needs it (see ensure_page_section) - standing
    in for a suffixed Variable/Constraint reference (e.g. "v_x.Lower(i_a)") that WebUI's content
    binding can't resolve directly - see win_object_tools._substitute_suffix_reference. AIMMS's
    own ".Level" suffix is the sole exception (never routed here): a bare reference already means
    Level, so the suffix is simply dropped instead of minting a parameter for it.

    Memoized per (component, bare_name, suffix) so every widget referencing the same suffixed
    identifier reuses one parameter - reused as-is, never duplicated or moved, by every later
    page (see _note_page_usage). Returns the bare name - qualify with get_prefix(component_dict)
    + "::" at the call site, same as ensure_indicator_parameter.

    :param gii_dict: Runtime library dictionary; any new-identifier commands are queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param page_slug: Slug of the WebUI page that (for this call) needs the parameter - see
        win_object_tools.page_slug_from_stable_id.
    :type page_slug: str
    :param bare_name: The (already namespace-qualified) suffixed identifier's own name, without
        its suffix - e.g. "v_x", or "giil::v_x" for a library identifier.
    :type bare_name: str
    :param suffix: The AIMMS suffix, e.g. "Lower" or "Marginal" (any casing as written in WinUI).
    :type suffix: str
    :param index_names: bare_name's own domain index names, in order - becomes the new
        Parameter's IndexDomain (empty when bare_name is a scalar).
    :type index_names: List[str]
    :param definition: The new Parameter's Definition - the original suffixed reference text.
    :type definition: str
    :return: The bare Parameter name.
    :rtype: str
    """
    ams_path = component_dict["AmsPath"]
    cache = gii_dict.setdefault("_suffix_param_cache", {})
    cache_key = (id(component_dict), bare_name, suffix.lower())
    if cache_key not in cache:
        parent = ensure_page_section(gii_dict, component_dict, page_slug)
        param_name = f"p_{_sanitize_identifier_fragment(bare_name)}_{suffix.lower()}"
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=param_name, type="parameter", parent=parent, file_hint=ams_path))
        if index_names:
            gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="IndexDomain", value=", ".join(index_names), file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Definition", value=definition, file_hint=ams_path))
        cache[cache_key] = param_name
        # Not yet live in the AIMMS session used elsewhere in this run (only queued as a text
        # edit, applied once AIMMS is done) - record its known dimension the same way
        # ensure_indicator_parameter does, so investigate_contents/add_data_widget's
        # modeledit_aimmspy2.getDim/getDomainIndex fallback isn't needed for it.
        gii_dict.setdefault("_synthetic_dims", {})[(id(component_dict), param_name)] = index_names
    param_name = cache[cache_key]
    _note_page_usage(gii_dict, component_dict, "_suffix_param_pages", (bare_name, suffix.lower()), param_name, page_slug)
    return param_name


def synthetic_domain_indices(gii_dict: dict, component_dict: dict, name: str) -> Optional[List[str]]:
    """The domain index names for a synthetic indicator Parameter registered via
    ensure_indicator_parameter, if `name` is one of this component's - None otherwise (the
    common case: fall back to modeledit_aimmspy2.getDim/getDomainIndex against the live model).

    Registered under the bare name (see ensure_indicator_parameter), but `name` here may be
    either bare or fully qualified ("giim::bp_indicator_X" - the form
    win_object_tools._substitute_set_indicator_reference's own returned reference now uses, since
    the widget content binding it feeds needs the qualified form to resolve). Falls back to the
    part after the last "::" on a qualified miss, same convention as ams_file_editor._resolve.

    :param gii_dict: Runtime library dictionary; the synthetic-identifier registry lives here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param name: The identifier name being looked up, bare or qualified.
    :type name: str
    :return: The identifier's domain index names in order, or None if it isn't a synthetic
        indicator Parameter registered for this component.
    :rtype: Optional[List[str]]
    """
    registry = gii_dict.get("_synthetic_dims", {})
    key = (id(component_dict), name)
    if key in registry:
        return registry[key]
    if "::" in name:
        bare_name = name.rsplit("::", 1)[-1]
        return registry.get((id(component_dict), bare_name))
    return None


def _normalize_for_comparison(text: Optional[str]) -> str:
    """Collapses all whitespace in `text` down to single spaces, for equivalence comparison
    only - the identifier that actually wins a dedup match still gets its own original,
    unnormalized text written out (see _register_usage)."""
    return " ".join((text or "").split())


def _register_usage(gii_dict: dict, component_dict: dict, key: tuple, candidate_name: str, usage: str) -> Tuple[str, bool, afe.SetAttribute]:
    """Shared lookup-or-register core for dedup_parameter/dedup_procedure.

    `key` already includes everything that makes two identifiers equivalent (see those two
    functions) - this just does the registry bookkeeping: reuse the identifier already
    registered for an identical `key` in this component, or register `candidate_name` as the
    new canonical one. Either way, `usage` is appended to that identifier's running list of
    "why it exists" notes, and a SetAttribute command covering the full list so far is built and
    returned - NOT queued here, since queuing it immediately would run it before an is_new
    caller's own AddIdentifier for this exact identifier (still to come, after this returns),
    which ams_file_editor would then fail to resolve. The caller must queue the returned command
    itself, after its own (conditional) AddIdentifier - see dedup_parameter/dedup_procedure.

    Safe to build this command fresh on every call (not just the first) since
    ams_file_editor._set_field replaces a previously written field (single- or multi-line) in
    place, so each longer joined text simply supersedes the last once applied in order. Entries
    are joined with a real newline, one usage per line - ams_file_editor._format_field_lines then
    writes this as AIMMS's own multi-line "Attr: { ... }" block convention instead of a single
    "Attr: value;" line, and _set_field's own re-edit logic finds and replaces that whole block
    (not just its opening line) on every later call, so it grows correctly as more usages are
    added.

    :param gii_dict: Runtime library dictionary; the dedup registry lives here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted - dedup is
        scoped per component, never across a library boundary.
    :type component_dict: dict
    :param key: Equivalence key, already namespace/whitespace-normalized by the caller.
    :type key: tuple
    :param candidate_name: The bare name this identifier would be created with if nothing
        equivalent exists yet.
    :type candidate_name: str
    :param usage: One-line description of why this call needs the identifier (e.g. what
        widget/page/attribute it's for).
    :type usage: str
    :return: (name, is_new, comment_command) - the bare name to actually use, whether the caller
        still needs to queue its own AddIdentifier/attribute commands, and the Comment command
        the caller must queue itself (after its own AddIdentifier when is_new, otherwise
        immediately - the winning identifier's own AddIdentifier is necessarily already queued
        from an earlier call by then).
    :rtype: Tuple[str, bool, afe.SetAttribute]
    """
    registry = gii_dict.setdefault("_dedup_registry", {})
    full_key = (component_dict["AmsPath"], *key)
    entry = registry.get(full_key)
    is_new = entry is None
    if is_new:
        entry = {"name": candidate_name, "usages": []}
        registry[full_key] = entry
    entry["usages"].append(usage)
    comment_text = "\n".join(entry["usages"])
    comment_command = afe.SetAttribute(identifier=entry["name"], attribute="Comment",
                                        value=f'"{comment_text}"', file_hint=component_dict["AmsPath"])
    return entry["name"], is_new, comment_command


def dedup_parameter(gii_dict: dict, component_dict: dict, id_type: str, index_domain: str,
                     range_value: Optional[str], definition: str, candidate_name: str, usage: str) -> Tuple[str, bool, afe.SetAttribute]:
    """
    Reuses an equivalent parameter already registered for this component during this run, if
    one exists, instead of minting a redundant new one - two parameters are equivalent when
    they have the same declared type (parameter / element parameter / string parameter), the
    same Range (only compared for an element parameter - the other two never set Range in the
    call sites that use this), the same IndexDomain, and the same Definition text.

    The caller MUST queue the returned comment_command itself - after its own AddIdentifier
    when is_new is True, otherwise immediately (see _register_usage for why).

    :param gii_dict: Runtime library dictionary; the dedup registry lives here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param id_type: Declared AIMMS type - "parameter", "element parameter", or "string parameter".
    :type id_type: str
    :param index_domain: The identifier's IndexDomain text (possibly "").
    :type index_domain: str
    :param range_value: The identifier's Range text, or None - only meaningful (compared) when
        id_type is "element parameter".
    :type range_value: Optional[str]
    :param definition: The identifier's Definition text.
    :type definition: str
    :param candidate_name: The bare name this identifier would be created with if nothing
        equivalent exists yet.
    :type candidate_name: str
    :param usage: One-line description of why this call needs the identifier.
    :type usage: str
    :return: (name, is_new, comment_command) - see _register_usage.
    :rtype: Tuple[str, bool, afe.SetAttribute]
    """
    key = (
        "parameter",
        id_type,
        _normalize_for_comparison(range_value) if id_type == "element parameter" else None,
        _normalize_for_comparison(index_domain),
        _normalize_for_comparison(definition),
    )
    return _register_usage(gii_dict, component_dict, key, candidate_name, usage)


def dedup_procedure(gii_dict: dict, component_dict: dict, body: str, candidate_name: str, usage: str) -> Tuple[str, bool, afe.SetAttribute]:
    """
    Reuses an equivalent procedure already registered for this component during this run, if
    one exists, instead of minting a redundant new one - two procedures are equivalent when
    they have the same Body text (e.g. many buttons across many pages whose action sequence is
    just "close the page" end up with an identical generated body).

    The caller MUST queue the returned comment_command itself - after its own AddIdentifier
    when is_new is True, otherwise immediately (see _register_usage for why).

    :param gii_dict: Runtime library dictionary; the dedup registry lives here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param body: The procedure's Body text.
    :type body: str
    :param candidate_name: The bare name this procedure would be created with if nothing
        equivalent exists yet.
    :type candidate_name: str
    :param usage: One-line description of why this call needs the procedure.
    :type usage: str
    :return: (name, is_new, comment_command) - see _register_usage.
    :rtype: Tuple[str, bool, afe.SetAttribute]
    """
    key = ("procedure", _normalize_for_comparison(body))
    return _register_usage(gii_dict, component_dict, key, candidate_name, usage)


def ensure_color_literal_elements(gii_dict: dict, main_model_component_dict: dict) -> None:
    """Realizes the ElementParameter for every color name registered via register_color_literal()
    during the widget walk: one ep_color_literal_<name> per distinct color, each
    `Range: s_AllColors; Definition: '<name>';`. Called once, alongside ensure_all_colors_values
    (which must run first so s_AllColors itself exists for these to range over)."""
    module_name = ensure_module(gii_dict, main_model_component_dict)
    ams_path = main_model_component_dict["AmsPath"]
    for color_name in sorted(gii_dict.get("_color_literal_names", set())):
        param_name = _color_literal_param_name(color_name)
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=param_name, type="element parameter", parent=module_name, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Range", value=ALL_COLORS_SET_NAME, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Definition", value=f"'{color_name}'", file_hint=ams_path))


_FILENAME_FROM_PATH_FUNCTION_NAME = "fcn_filenameFromPath"

# Raw so every "\\" below is exactly two literal backslash characters in the .ams source text
# (AIMMS string literals use '\' as an escape character, same as sp_broomstick/sp_puma's own
# Definition elsewhere - "cauldron\\pictures\\..." - so two source-level backslashes give one
# literal backslash at AIMMS runtime).
_FILENAME_FROM_PATH_BODY = r"""p_posSlash := FindNthString(
	SearchString  :  sp_path,
	Key           :  "\\",
	Nth           :  -1,
	CaseSensitive :  1,
	WordOnly      :  0,
	IgnoreWhite   :  0);
if not p_posSlash then
	p_posSlash := FindNthString(
		SearchString  :  sp_path,
		Key           :  "/",
		Nth           :  -1,
		CaseSensitive :  1,
		WordOnly      :  0,
		IgnoreWhite   :  0);
endif ;
if p_posSlash then
	if p_posSlash = StringLength( sp_path ) then
		raise error "Unable to determine filename." ;
	endif ;
	fcn_filenameFromPath := substring( sp_path, p_posSlash + 1, stringlength( sp_path ) );
else
	fcn_filenameFromPath := sp_path ;
endif ;
"""


def ensure_filename_from_path_function(gii_dict: dict, main_model_component_dict: dict) -> str:
    """Ensures the main model's own fcn_filenameFromPath Function exists - given a (possibly
    backslash- or forward-slash-separated) path string, returns just its trailing filename
    component. Used by every generated per-Picture defining procedure (see
    ensure_image_reference_parameter) to turn whatever a dynamically-selected image identifier
    evaluates to at runtime into the bare filename WebUI's image widget needs - it only ever
    loads images from its own WebUI/resources/images folder, addressed by filename alone (see
    win_picture.winpage_picture).

    Always created in the main model (Module GeneratedInterfaceIdentifiersMain), regardless of
    which component ends up calling it - referencing it is then always the unambiguous
    "giim::fcn_filenameFromPath", from anywhere in the project (same convention as e.g.
    ensure_all_colors_values). Idempotent (memoized via
    main_model_component_dict["_gii_filename_from_path_ready"]). Returns the bare name."""
    module_name = ensure_module(gii_dict, main_model_component_dict)
    ams_path = main_model_component_dict["AmsPath"]
    if not main_model_component_dict.get("_gii_filename_from_path_ready"):
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=_FILENAME_FROM_PATH_FUNCTION_NAME, type="function", parent=module_name, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=_FILENAME_FROM_PATH_FUNCTION_NAME, attribute="Arguments", value="(sp_path)", file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=_FILENAME_FROM_PATH_FUNCTION_NAME, attribute="Range", value="string", file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=_FILENAME_FROM_PATH_FUNCTION_NAME, attribute="Body", value=_FILENAME_FROM_PATH_BODY, file_hint=ams_path))

        gii_dict["_edit_queue"].append(afe.AddIdentifier(name="sp_path", type="string parameter", parent=_FILENAME_FROM_PATH_FUNCTION_NAME, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier="sp_path", attribute="Property", value="Input", file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name="p_posSlash", type="parameter", parent=_FILENAME_FROM_PATH_FUNCTION_NAME, file_hint=ams_path))

        main_model_component_dict["_gii_filename_from_path_ready"] = True
    return _FILENAME_FROM_PATH_FUNCTION_NAME


def ensure_image_destination_folder_expr(gii_dict: dict, component_dict: dict) -> str:
    """Returns the AIMMS expression text for this component's own WebUI/resources/images folder,
    ending in a trailing backslash and ready to embed directly in a generated defining
    procedure's filecopy(...) call (see ensure_image_reference_parameter) - a bare filename can
    just be concatenated onto it.

    The main model's own folder is always named "MainProject" - a fixed WinUI convention, unlike
    a library's own folder, which matches that library's own DisplayName - so for the main model
    (component_dict['Prefix'] == "") this is simply a literal expression, no runtime lookup
    needed.

    For a library, the folder isn't known until AIMMS itself resolves it
    (DirectoryOfLibraryProject - the project could be opened from any location), so this lazily
    creates a per-library sp_libraryLocation StringParameter and a
    pr_initGenerateInterfaceidentifiersLibrary procedure that assigns it (in this component's own
    GeneratedInterfaceIdentifiersLibrary module, as direct children of the module - shared
    infrastructure for the whole library, not any one page, so it doesn't route through
    ensure_page_section), and queues a call to that procedure onto the *existing*
    LibraryInitialization procedure's Body (AppendToBody - safe even when LibraryInitialization
    has no Body yet, same mechanism as identifier_element_text.ensure_lifecycle_procedures' call
    into PostMainInitialization). Idempotent per component (memoized via
    component_dict["_gii_library_location_ready"]).

    :return: An AIMMS expression (not itself a valid statement/identifier reference on its own -
        e.g. "sp_libraryLocation + \"WebUI\\\\resources\\\\images\\\\\"") for this component's
        images folder, referencing only identifiers reachable bare from within this same
        component's own GeneratedInterfaceIdentifiers module (the scope
        ensure_image_reference_parameter's own generated procedure runs in).
    :rtype: str
    """
    if component_dict["Prefix"] == "":
        return r'"MainProject\\" + "WebUI\\resources\\images\\"'

    module_name = ensure_module(gii_dict, component_dict)
    ams_path = component_dict["AmsPath"]
    if not component_dict.get("_gii_library_location_ready"):
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name="sp_libraryLocation", type="string parameter", parent=module_name, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier="sp_libraryLocation", attribute="Comment", value='"The root folder of the library"', file_hint=ams_path))

        proc_name = "pr_initGenerateInterfaceidentifiersLibrary"
        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=proc_name, type="procedure", parent=module_name, file_hint=ams_path))
        body = (
            "DirectoryOfLibraryProject(\n"
            f"\tlibraryname   :  \"{component_dict['DisplayName']}\", \n"
            "\tdirectoryname :  sp_libraryLocation);\n"
        )
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=proc_name, attribute="Body", value=body, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=proc_name, attribute="Comment",
            value='"initializes sp_libraryLocation, and should be called by LibraryInitialization."', file_hint=ams_path))

        gii_dict["_edit_queue"].append(afe.AppendToBody(identifier="LibraryInitialization", attribute="Body",
            statement=f"{get_prefix(component_dict)}::{proc_name}();", file_hint=ams_path))

        component_dict["_gii_library_location_ready"] = True

    return r'sp_libraryLocation + "WebUI\\resources\\images\\"'


def ensure_image_reference_parameter(gii_dict: dict, component_dict: dict, page_slug: str, stable_id: str, image_identifier_reference: str) -> str:
    """Ensures a StringParameter sp_genpar_image_<stable_id>, filed under page_slug's own Section
    (see ensure_page_section), whose Definition is supplied by a companion defining Procedure
    pr_def_genpar_image_<stable_id> (Property: UsedInDefinition, DefinesIdentifiers:
    sp_genpar_image_<stable_id>) - the only way to have a StringParameter's own Definition both
    call an AIMMS Function AND run a side-effecting statement (filecopy), which a plain
    expression-only Definition can't do. That procedure:
    1. Assigns giim::fcn_filenameFromPath(image_identifier_reference)'s result - just the
       filename part of whatever path image_identifier_reference evaluates to at runtime (see
       ensure_filename_from_path_function) - to the generated parameter.
    2. Copies the actual file at that path (filecopy) into this component's own
       WebUI/resources/images folder (see ensure_image_destination_folder_expr).
    Both run every time this component's model is (re)loaded, so a Picture bound to a
    dynamically-selected image (e.g. toggled by a button) always has whatever
    image_identifier_reference currently evaluates to already copied into place, and the
    generated parameter already holding just that image's own filename - unlike a literal
    Picture, whose image file is instead copied once, at CONVERSION time, by win_picture.py
    itself (see win_picture.winpage_picture).

    stable_id already uniquely identifies the one Picture object this is generated for, so unlike
    e.g. ensure_not_parameter this pairing is never reused across widgets - memoized per
    (component, stable_id) purely as a defensive no-op guard against being asked twice for the
    same widget.

    :param image_identifier_reference: The (already namespace-qualified) StringParameter
        reference the WinUI Picture's <FileName> names - must be reachable bare, or via its own
        qualification, from inside this component's own GeneratedInterfaceIdentifiers module.
    :type image_identifier_reference: str
    :return: The qualified reference to sp_genpar_image_<stable_id> - use this as the image
        widget's own "contents.aimms.contents" binding.
    :rtype: str
    """
    ams_path = component_dict["AmsPath"]
    cache = gii_dict.setdefault("_image_reference_param_cache", {})
    cache_key = (id(component_dict), stable_id)
    if cache_key not in cache:
        parent = ensure_page_section(gii_dict, component_dict, page_slug)
        param_name = f"sp_genpar_image_{stable_id}"
        proc_name = f"pr_def_genpar_image_{stable_id}"

        fcn_name = ensure_filename_from_path_function(gii_dict, gii_dict["_main_model_component_dict"])
        destination_expr = ensure_image_destination_folder_expr(gii_dict, component_dict)

        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=param_name, type="string parameter", parent=parent, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=param_name, attribute="Definition", value=f"{proc_name}();\n", file_hint=ams_path))

        gii_dict["_edit_queue"].append(afe.AddIdentifier(name=proc_name, type="procedure", parent=parent, file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=proc_name, attribute="Property", value="UsedInDefinition", file_hint=ams_path))
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=proc_name, attribute="DefinesIdentifiers", value=param_name, file_hint=ams_path))
        body = (
            f"{param_name} := {MAIN_PREFIX}::{fcn_name}({image_identifier_reference});\n"
            f"filecopy( {image_identifier_reference}, {destination_expr} );\n"
        )
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=proc_name, attribute="Body", value=body, file_hint=ams_path))

        cache[cache_key] = param_name

    lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""
    return f"{lib_prefix}{get_prefix(component_dict)}::{cache[cache_key]}"
