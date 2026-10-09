from typing import List, Dict, Tuple, Any, Union, Optional # Add Tuple and any other types you use
import lxml.etree as ET
import win_expression
import tools
from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import modeledit_aimmspy2
import identifier_element_text
import win_pivot_state
import re
import ams_file_editor as afe
import gii_module
import win_color_scan
import win_layout

def compute_stable_id(xml_element: ET.Element, ancestor_info: dict) -> str:
    """
    Compute a stable, run-independent identity for a WinUI PageObject, used to name its
    WebUI widget and any AIMMS identifiers generated for it.

    Derived from that page's slug (set on `ancestor_info['page_slug']` by
    win_page.process_page, already collision-safe - see aimms_slug.aimms_slug()) combined
    with the object's position among that page's objects (tracked via the mutable counter
    at `ancestor_info['object_counter']`) - so the result only depends on the object's own
    page, not on anything happening elsewhere in the project, and stays stable across runs
    and across unrelated changes. Every object type uses this same scheme, Pivot Table
    included - its real `<ObjectUUID>` is still read directly where needed (see
    win_pivot_state.py), just no longer baked into the generated name itself.

    :param xml_element: XML element for the WinUI PageObject (or similar) being converted.
    :type xml_element: ET.Element
    :param ancestor_info: Per-page conversion context; must carry 'page_slug' and 'object_counter'.
    :type ancestor_info: dict
    :return: Stable identifier string, safe to embed in AIMMS identifier/widget names (underscores only).
    :rtype: str
    """
    counter = ancestor_info.setdefault('object_counter', {'n': 0})
    counter['n'] += 1

    page_slug = ancestor_info.get('page_slug', '')
    return f"{page_slug}_{counter['n']}"


def page_slug_from_stable_id(stable_id: str) -> str:
    """Recovers the page_slug a stable_id was built from (see compute_stable_id's own
    `f"{page_slug}_{counter['n']}"` format) - for a caller (win_expression.py, win_procedure.py)
    that already receives stable_id but not the ancestor_info dict page_slug itself lives on,
    used to file a generated identifier into gii_module.ensure_page_section's Section for the
    page that actually needs it, rather than threading a whole extra parameter down through
    every widget file just to carry the same slug already implicit in stable_id.

    Safe despite page_slug itself possibly containing underscores/digits (aimms_slug.aimms_slug's
    own collision-suffixing, e.g. "p1_2"): the counter is always the LAST component and always
    purely numeric, so splitting off only the trailing "_<n>" recovers the original slug intact
    regardless of what precedes it."""
    return stable_id.rsplit('_', 1)[0]


_BARE_IDENTIFIER_RE = re.compile(r'^[A-Za-z_][A-Za-z0-9_]*(?:::[A-Za-z_][A-Za-z0-9_]*)*$')

# A <Hidden> condition written with WinUI's "VALUE := <body>" dynamic-substitution form (as also
# handled by win_expression.potentially_substitute_expression for other attributes) - never
# indexed here, since a <Hidden> condition belongs to one specific PageObject instance, not a
# domain of them - see resolve_widget_visibility.
_HIDDEN_VALUE_SUBST_RE = re.compile(r'^VALUE\s*:=\s*(.*)$', re.DOTALL)


def _is_negation_of(definition_text: str, other_name: str) -> bool:
    """True when `definition_text` (an identifier's own Definition attribute, as read via
    modeledit_aimmspy2.getAttribute) is exactly the logical negation of `other_name` - either
    AIMMS's `not X` operator or the equivalent `1 - X` arithmetic form, both common ways an
    AIMMS modeler writes "the opposite of X" for a binary parameter (e.g.
    "Definition: 1 - FlowAccuracyIsRelative;" for FlowAccuracyIsAbsolute).

    :param definition_text: The candidate identifier's own Definition attribute text.
    :type definition_text: str
    :param other_name: The (bare) identifier name being tested as the thing being negated.
    :type other_name: str
    :return: True if definition_text reads as exactly "not other_name" or "1 - other_name".
    :rtype: bool
    """
    if not definition_text:
        return False
    pattern = rf'^\s*(?:not\s*\(?\s*{re.escape(other_name)}\s*\)?|1\s*-\s*\(?\s*{re.escape(other_name)}\s*\)?)\s*$'
    return re.match(pattern, definition_text.strip(), re.IGNORECASE) is not None


def ensure_binary_range(aimms_model: Model, gii_dict: dict, component_dict: dict, identifier_name: str) -> None:
    """
    Backfill Range: binary onto identifier_name if it doesn't have one yet. Shared by
    resolve_widget_visibility (reusing an existing "opposite" visibility parameter) and
    win_elemselec.py (a checkbox-style Selection Object bound directly to a scalar Parameter) -
    both are a boolean toggle that should be range-restricted to 0/1, not left unrestricted.

    :param aimms_model: AIMMS model handle used to check the identifier's current Range.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary; any SetAttribute command is queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the identifier's own component (its AmsPath is
        used as the edit's file_hint).
    :type component_dict: dict
    :param identifier_name: The (already namespace-qualified) identifier name.
    :type identifier_name: str
    :return: None.
    :rtype: None
    """
    if modeledit_aimmspy2.getAttribute(aimms_model, identifier_name, "range") == "":
        gii_dict["_edit_queue"].append(afe.SetAttribute(identifier=identifier_name, attribute="Range", value="binary", file_hint=component_dict["AmsPath"]))


def resolve_widget_visibility(aimms_model: Model, gii_dict: dict, component_dict: dict, page_slug: str,
                               hidden_expr: str, sibling_hidden_exprs: List[str]) -> str:
    """
    Turn a WinUI PageObject's <Hidden> condition into the AIMMS boolean expression a WebUI
    widget's "widget.visible" binding should use. WinUI's Hidden and WebUI's visible are OPPOSITE
    in polarity - a WinUI object is HIDDEN when its condition is true, while a WebUI widget is
    SHOWN when its "widget.visible" expression is true - so this is never the raw Hidden text
    unchanged.

    Preference order:
    0. A condition written with WinUI's "VALUE := <body>" dynamic-substitution form (see
       win_expression.potentially_substitute_expression, which handles the same form for other
       attributes) is never usable as-is: unlike a plain boolean expression, "VALUE := ..." is
       WinUI-only pseudo-syntax, not valid inside an AIMMS Definition. <body> alone becomes a new
       (or reused, memoized per expression - see gii_module.ensure_hidden_condition_parameter)
       Parameter's Definition, and that Parameter is in turn wrapped in its own
       ensure_not_parameter negation Parameter - "widget.visible" is read directly by the WebUI
       frontend as a bare identifier reference, not evaluated as an AIMMS expression, so a raw
       "not <ref>" string there fails at runtime with "Unknown identifier: not <ref>".
    1. Among the other conditionally-hidden widgets sharing this one's grid area (mutually
       exclusive alternates merged by win_layout._merge_conditional_overlaps, e.g. an absolute-
       vs-relative error table pair), reuse whichever sibling's own condition is already declared
       in the AIMMS model as this one's logical opposite (Definition "not X" or "1 - X", checked
       in both directions) - e.g. reusing an existing FlowAccuracyIsAbsolute parameter for a
       FlowAccuracyIsRelative condition, rather than minting a redundant new one. That parameter's
       Range is set to "binary" if it doesn't have one yet.
    2. Otherwise, mint a new binary Parameter (in this component's own
       GeneratedInterfaceIdentifiers module, memoized per expression - see
       gii_module.ensure_not_parameter) with Definition: not <hidden_expr>.

    Step 1 only fires when both the condition and the candidate sibling are bare identifier
    references, not some more general boolean expression - "does this identifier's Definition
    negate that one" only makes sense for an actual identifier.

    :param aimms_model: AIMMS model handle used to inspect/verify candidate opposite parameters.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary; any new-parameter commands are queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param page_slug: Slug of the WebUI page this widget belongs to - any generated Parameter is
        filed into that page's own Section (see gii_module.ensure_page_section).
    :type page_slug: str
    :param hidden_expr: The raw WinUI <Hidden> condition text (see win_layout.conditional_visibility_expr).
    :type hidden_expr: str
    :param sibling_hidden_exprs: <Hidden> conditions of other widgets sharing this one's grid area
        (see win_layout.LayoutPlan.conditional_sibling_exprs).
    :type sibling_hidden_exprs: List[str]
    :return: The AIMMS boolean expression to embed in "widget.visible".
    :rtype: str
    """
    qualified_hidden_expr = namespace_qualification(aimms_model, hidden_expr, component_dict['Prefix'])

    # "widget.visible" is evaluated from outside the widget's own component, so a generated
    # parameter's reference needs the component's own prefix too, not just giim/giil's -
    # "giil::x" alone only resolves from *inside* that library; from anywhere else (including a
    # webui.json binding) it's "<library prefix>::giil::x", e.g. "ke::giil::p_Not...". A
    # library's own GeneratedInterfaceIdentifiersLibrary module is unique to it (unlike giim,
    # which is reachable from anywhere unqualified - see gii_module.py's module docstring), so
    # this qualification is library-specific and skipped entirely for the main model
    # (component_dict['Prefix'] == '').
    prefix_parts = [p for p in (component_dict['Prefix'], gii_module.get_prefix(component_dict)) if p]

    value_subst_match = _HIDDEN_VALUE_SUBST_RE.match(qualified_hidden_expr.strip())
    if value_subst_match:
        body_expr = value_subst_match.group(1).strip()
        hidden_param_name = gii_module.ensure_hidden_condition_parameter(gii_dict, component_dict, page_slug, body_expr)
        qualified_hidden_param = "::".join(prefix_parts + [hidden_param_name])
        not_param_name = gii_module.ensure_not_parameter(gii_dict, component_dict, page_slug, qualified_hidden_param)
        return "::".join(prefix_parts + [not_param_name])

    hidden_name, hidden_args = tools.parse_aimms_string(qualified_hidden_expr)

    if not hidden_args and _BARE_IDENTIFIER_RE.match(hidden_name):
        hidden_definition = modeledit_aimmspy2.getAttribute(aimms_model, hidden_name, "definition")
        for sibling_expr in sibling_hidden_exprs:
            sibling_qualified = namespace_qualification(aimms_model, sibling_expr, component_dict['Prefix'])
            sibling_name, sibling_args = tools.parse_aimms_string(sibling_qualified)
            if sibling_args or not _BARE_IDENTIFIER_RE.match(sibling_name):
                continue
            sibling_definition = modeledit_aimmspy2.getAttribute(aimms_model, sibling_name, "definition")
            if _is_negation_of(hidden_definition, sibling_name) or _is_negation_of(sibling_definition, hidden_name):
                ensure_binary_range(aimms_model, gii_dict, component_dict, sibling_name)
                return sibling_name

    not_param_name = gii_module.ensure_not_parameter(gii_dict, component_dict, page_slug, qualified_hidden_expr)
    return "::".join(prefix_parts + [not_param_name])


def compute_layout_slot(aimms_model: Model, gii_dict: dict, component_dict: dict, xml_element: ET.Element, ancestor_info: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Determine the WebUI grid area (and any caption folded into the title), plus any runtime
    visibility condition, for a WinUI PageObject, per the layout heuristic in win_layout.py.

    A PageObject with no <Location> at all, or one that's unconditionally hidden (<Hidden>
    a literal always-true, i.e. design-time-disabled content - see win_layout.is_unconditionally_hidden),
    is routed unconditionally to the "Unassigned widgets" WebUI bucket (confirmed via a real
    hand-built reference to be a valid gridArea sentinel, independent of whatever layoutId the
    page has) - neither ever had a real on-page position, so neither should fall into the old
    type-based default area either, regardless of whether the rest of the page's layout was
    accepted by the heuristic.

    Otherwise, defers to ancestor_info['layout_plan'] (a win_layout.LayoutPlan set by
    win_page.process_page, or None if the page's layout was rejected or not yet computed).

    The visibility condition (third element) is independent of placement: a conditionally-hidden
    PageObject (<Hidden> a boolean expression, e.g. two mutually exclusive alternates sharing one
    grid area via win_layout._merge_conditional_overlaps) keeps its own runtime visibility
    regardless of whether the layout heuristic placed it, merged it with another widget, or
    rejected the page outright. It is resolved via resolve_widget_visibility() - never the raw
    <Hidden> text, since WinUI's Hidden and WebUI's widget.visible have opposite polarity.

    :param aimms_model: AIMMS model handle, used to resolve a conditionally-hidden object's
        visibility expression (see resolve_widget_visibility).
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary; any new-parameter commands are queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param xml_element: XML element for the WinUI PageObject being converted.
    :type xml_element: ET.Element
    :param ancestor_info: Per-page conversion context; may carry 'layout_plan'.
    :type ancestor_info: dict
    :return: (area, title, visible_expr) - any may be None, meaning "use the caller's own
        default" (area/title) or "always visible" (visible_expr).
    :rtype: Tuple[Optional[str], Optional[str], Optional[str]]
    """
    hidden_expr = win_layout.conditional_visibility_expr(xml_element)
    layout_plan = None

    if xml_element.find('Location') is None:
        area, title = "Unassigned widgets", None
    elif win_layout.is_unconditionally_hidden(xml_element):
        area, title = "Unassigned widgets", None
    else:
        layout_plan = ancestor_info.get('layout_plan')
        area, title = (None, None) if layout_plan is None else layout_plan.slot_for(xml_element)

    if hidden_expr is None:
        return area, title, None

    sibling_exprs = layout_plan.conditional_sibling_exprs(xml_element) if layout_plan is not None else []
    page_slug = ancestor_info.get('page_slug', '')
    visible_expr = resolve_widget_visibility(aimms_model, gii_dict, component_dict, page_slug, hidden_expr, sibling_exprs)
    return area, title, visible_expr


def determine_no_identifiers(winui_table_xml:ET.Element) -> int:
    """
    Determine how many identifier entries exist in a WinUI table XML element.

    :param winui_table_xml: XML element containing the WinUI table definition.
    :type winui_table_xml: ET.Element
    :return: Number of explicit identifier declarations found.
    :rtype: int
    """
    no_identifiers = 0
    for table_child in winui_table_xml:
        if table_child.tag == 'ExplicitIdentifier' or table_child.tag == 'Explicit_Identifier':
            no_identifiers += 1

    return no_identifiers


# The keywords WinUI uses to mark a content item as a computed expression - "<KEYWORD>[(indices)]
# := expr" - rather than a bare identifier reference (see win_expression.potentially_substitute_
# expression, and resolve_sole_identifier_title below, which both need to recognize the same
# convention). Defined here rather than in win_expression.py so both modules can share it without
# a circular import (win_expression.py already imports win_object_tools.py, not the other way).
EXPRESSION_KEYWORDS = ('ELEMENT', 'STRING', 'VALUE')


def resolve_sole_identifier_title(aimms_model: Model, component_dict: dict, winui_table_xml: ET.Element) -> str:
    """
    A table widget with no title of its own, but exactly one real identifier reference as its
    content, reads better with that identifier's own name as its title than with none at all -
    see win_page.process_page's own call site, run once a page's widgets are all converted and
    every title-resolution source (a caption Text object folded in by win_layout.py; a Pivot
    Table's own Header_Title) has already had its chance.

    Checked directly against the WinUI XML rather than the widget's own already-built contents
    list: by the time a content item reaches investigate_contents' own contents_list, an
    expression-based item ("<KEYWORD>[(indices)] := expr", or a literal string) has already been
    replaced with a generated parameter reference indistinguishable from a genuine identifier
    (see win_expression.potentially_substitute_expression) - only the raw source still shows
    whether this was a plain reference to begin with.

    :param aimms_model: AIMMS model handle used to resolve the identifier's own declared Text.
    :type aimms_model: Model
    :param component_dict: Metadata describing the current component being converted - used to
        qualify the identifier's own name the same way investigate_contents does.
    :type component_dict: dict
    :param winui_table_xml: XML element representing the WinUI table/pivot table definition.
    :type winui_table_xml: ET.Element
    :return: A title - the identifier's own declared <Text> attribute in the AIMMS model
        (modeledit_aimmspy2.getText, the same "identifier element text" investigate_contents
        already uses for a content item's own header caption) when it has one, else the bare
        identifier name itself - or '' when this widget doesn't qualify (not exactly one
        identifier, or that one identifier is itself an expression/literal, not a plain reference).
    :rtype: str
    """
    contents_xml = winui_table_xml
    if winui_table_xml.get('Type') == 'Pivot Table':
        contents_elem = winui_table_xml.find('Contents')
        if contents_elem is not None:
            contents_xml = contents_elem

    identifier_children = [c for c in contents_xml if c.tag in ('ExplicitIdentifier', 'Explicit_Identifier')]
    if len(identifier_children) != 1:
        return ''

    identifier_el = identifier_children[0].find('Identifier')
    if identifier_el is None or not identifier_el.text:
        return ''
    identifier_text = identifier_el.text.strip()
    if not identifier_text or identifier_text == '""' or identifier_text[0] == '"':
        return ''
    if any(identifier_text.startswith(keyword) for keyword in EXPRESSION_KEYWORDS):
        return ''

    identifier_text = namespace_qualification(aimms_model, identifier_text, component_dict['Prefix'])
    identifier_name, _args = tools.parse_aimms_string(identifier_text)

    declared_text = modeledit_aimmspy2.getText(aimms_model, identifier_name)
    if len(declared_text) > 1 and declared_text[0] == '"' and declared_text[-1] == '"':
        declared_text = declared_text[1:-1]

    return declared_text if declared_text else identifier_name

def find_identifiers(expr:str) -> list[str]:
    """
    Finds all valid identifiers in a given string expression.

    An identifier must:
    1. Start with a letter (a-z, A-Z) or underscore (_).
    2. Be followed by any combination of letters, digits (0-9), or underscores.
    3. Optionally contain a double colon (::) followed by more valid identifier characters.

    :param expr: the expression to be modified.
    :type expr: str
  
    :return: list of identifiers
    :rtype: list[str]
    """
    # The pattern explained:
    # r'...' makes it a raw string.
    # 1. [a-zA-Z_] : Start with a letter or an underscore.
    # 2. (?: [a-zA-Z0-9_] | :: )* : This is the main body, allowing zero or more 
    #    occurrences of:
    #    - a letter, digit, or underscore ( [a-zA-Z0-9_] ) 
    #    - OR a double colon ( :: )
    pattern = r"[a-zA-Z_](?:[a-zA-Z0-9_]|::)*"

    # re.findall returns a list of all non-overlapping matches
    return re.findall(pattern, expr)

def find_scoped_identifiers(expr):
    """
    Finds identifiers that consist of one or more name segments joined by '::'.

    Name segments start with [a-zA-Z_] and are followed by [a-zA-Z0-9_]*.

    :param expr: the expression to be modified.
    :type expr: str
  
    :return: list of identifiers
    :rtype: list[str]
    """
    
    # Pattern for a single name segment (e.g., "MyClass" or "_var1")
    name_segment = r"[a-zA-Z_][a-zA-Z0-9_]*"
    
    # Pattern for the full identifier: 
    # Matches one name_segment, optionally followed by (:: and another name_segment) zero or more times.
    pattern = rf"{name_segment}(?::{name_segment})*"

    # re.findall returns a list of all non-overlapping matches
    return re.findall(pattern, expr)


def remove_duplicates(input_list:list[str]) -> list[str]:
    """
    Removes duplicates from a list by converting it to a set and back to a list.

    :param input_list: a list of strings, potentially containing duplicates.
    :type input_list: list[str]
    
    :return: list of unique strings
    :rtype: list[str]
    """
    # 1. Convert the list to a set to remove duplicates
    unique_set = set(input_list)
    
    # 2. Convert the set back to a list
    unique_list = list(unique_set)
    
    return unique_list

def namespace_qualification(aimms_model: Model, expr:str, prefix:str)->str:
    """
    namespace_qualification - ensure identifiers have the correct prefix.

    Add prefix to those identifiers in expr that are declared inside namespace with prefix str,
    but do not have that prefix in the expr.

    :param aimms_model: AIMMS model handle used to inspect identifiers and their domains.
    :type aimms_model: Model
    :param expr: the expression to be modified.
    :type expr: str
    :param prefix: the prefix to be used.
    :type prefix: str
    :return: adapted expr, where str is added when needed.
    :rtype: str
    """
    #inp_expr = expr
    #if expr.find('gui::gui::') >= 0:
    #    dummy = 1
    if prefix != '':
        ids = find_identifiers(expr)
        unique_ids = remove_duplicates(ids)
        for id in unique_ids:
            if id.find("::") <0:
                dim_main = modeledit_aimmspy2.getDim(aimms_model, id)
                dim_lib  = modeledit_aimmspy2.getDim(aimms_model, prefix + "::" + id)
                if ( dim_main < 0 ) and ( dim_lib >= 0 ):
                    # A plain expr.replace(id, ...) corrupts any OTHER identifier in expr that
                    # merely happens to CONTAIN id as a substring - confirmed against a real
                    # project: qualifying a genuine index "hly" inside "FlowsMonthly( hly, h1 )"
                    # turned "FlowsMonthly" itself (which just happens to end in "...hly", nothing
                    # to do with the index) into "FlowsMontnn::hly", an identifier that doesn't
                    # exist. Word-boundary-anchored (AIMMS identifier characters are letters,
                    # digits, underscore, and "::" continuations - a preceding/following one of
                    # those means id is part of a LARGER name, not id itself) so only a genuine,
                    # standalone occurrence of id gets qualified.
                    expr = re.sub(r'(?<![A-Za-z0-9_:])' + re.escape(id) + r'(?![A-Za-z0-9_:])',
                                  prefix + "::" + id, expr)

    expr = expr.replace(prefix + "::" + prefix + "::", prefix + "::")

    return expr


def resolve_identifier_owner_component(gii_dict: dict, component_dict: dict, qualified_name: str) -> dict:
    """
    The component_dict that actually DECLARES qualified_name, which is not always
    component_dict itself: a library's own WinUI page can reference an identifier declared in
    the main model (AIMMS's own namespace rules make every main-model identifier visible bare,
    with no prefix, from anywhere) or, less commonly, another already-qualified component. Looks
    up gii_dict["_component_dict_by_prefix"] (populated for every component, upfront, by
    winui_to_webui.py's own pre-pass, before any page is converted - so this is never a forward
    reference to a not-yet-discovered component) by qualified_name's own prefix, or '' (the main
    model) when it's bare - after namespace_qualification has already run (see above - it only
    ever adds component_dict's OWN prefix, never any other), a bare qualified_name that isn't
    component_dict's own identifier can only be the main model's, per AIMMS's namespace rules.
    Falls back to component_dict itself if the prefix isn't a component w2w is converting at all
    (e.g. a third-party library).

    Needed wherever a generated identifier is meant to support an EXISTING identifier via an
    AIMMS annotation (e.g. webui::AnnotationsIdentifier/webui::flagsIdentifier - see
    win_expression.make_webui_reference's call sites in investigate_contents' Color/Readonly
    handling) rather than being consumed only by the widget doing the generating: such a
    generated identifier must live in the SAME component as the identifier the annotation is
    attached to, not wherever the referencing page happens to live - otherwise two different
    library pages referencing the same main-model identifier's Color would each mint their own
    generated parameter in their own, DIFFERENT component, and since the annotation is a single
    slot on the shared identifier, only the last one processed would actually take effect for
    every page displaying it, the others silently overwritten.

    :param gii_dict: Runtime library dictionary; the per-prefix component registry lives here.
    :type gii_dict: dict
    :param component_dict: Metadata for the component whose page is currently being converted.
    :type component_dict: dict
    :param qualified_name: The (already namespace_qualification'd) identifier reference text -
        may itself carry index arguments (e.g. "lecc::heatrate( i_a )"); only the leading name up
        to its first "(" is inspected.
    :type qualified_name: str
    :return: The component_dict qualified_name is actually declared in.
    :rtype: dict
    """
    bare_name = qualified_name.split('(', 1)[0].strip()
    sep_pos = bare_name.rfind('::')
    owner_prefix = bare_name[:sep_pos] if sep_pos >= 0 else ''
    return gii_dict.get("_component_dict_by_prefix", {}).get(owner_prefix, component_dict)


def filter_index_args(aimms_model: Model, args: List[str]) -> List[str]:
    """
    Filters a parsed reference's arguments (e.g. from tools.parse_aimms_string) down to just the
    free indices that actually form its IndexDomain - for building an identifier that mirrors or
    wraps the reference (e.g. a readonly/color substitution). An argument can also be a literal
    element (single-quoted, e.g. 'a') or a scalar element parameter (e.g. FlowEl in
    "FlowErrorColor( FlowEl )") - either of those SELECTS one specific slice of the reference
    rather than indexing it, and must be left out of the IndexDomain.

    :param aimms_model: AIMMS model handle used to check whether an argument is an element parameter.
    :type aimms_model: Model
    :param args: Parenthesized arguments as parsed from a reference, e.g. ["i_let"] or ["FlowEl"].
    :type args: List[str]
    :return: Just the entries of `args` that are actual free indices.
    :rtype: List[str]
    """
    indices = []
    for arg in args:
        if arg.startswith("'") and arg.endswith("'"):
            continue
        if modeledit_aimmspy2.isScalarElementParameter(aimms_model, arg):
            continue
        indices.append(arg)
    return indices


def resolve_effective_index_name(aimms_model: Model, arg: str, domain_index_name: str) -> str:
    """
    AIMMS lets a content reference index an identifier with ANY range-compatible Index, not just
    the identifier's own declared one - e.g. a real RSC model declares "Parameter PeriodMustRun {
    IndexDomain: (u,fh); }" but a WinUI page references "PeriodMustRun( u, h )", substituting its
    own "h" (a differently-named Index, ranging over a subset of fh's own range) for the declared
    "fh". Every caller that NAMES this position - the WebUI content slice's own "index" key, a
    Pivot Table's .DeveloperState row/column lookup (win_pivot_state.py tracks the arrangement by
    the name actually WRITTEN in the WinUI reference, "h", never the declared "fh"), the
    row/column/header partition lists, the webui::IdentifierElementText fallback - needs "h", the
    name it's actually known by at this reference site; "fh" is meaningless outside this one
    Parameter's own declaration and won't be found in any of those.

    This is a DIFFERENT question from whether the arg counts as "free" vs "subset" for the
    content slice's own "type" field (that's still decided by comparing `arg` against
    domain_index_name's own canonical name, unaffected by this function - "h" ranging over a
    subset of "fh"'s range is still legitimately a "subset" selection there, just one that also
    happens to need a real Index's own name rather than a literal Set/ElementParameter reference).
    Callers must keep domain_index_name itself around, unresolved, for that separate check - see
    the two call sites, both of which compute this into its own `effective_index_name` rather
    than overwriting domain_index_name in place.

    :param aimms_model: AIMMS model handle used to check the argument's own declared type.
    :type aimms_model: Model
    :param arg: The parsed reference argument at this position, e.g. "h" or "fh".
    :type arg: str
    :param domain_index_name: The identifier's own declared domain index at this position (see
        modeledit_aimmspy2.getDomainIndex/gii_module.synthetic_domain_indices) - returned
        unchanged when arg isn't itself a real Index (a Set, element parameter, or other
        expression - those genuinely aren't "this Index, just under another name").
    :type domain_index_name: str
    :return: `arg` when it's itself a declared Index, else domain_index_name unchanged.
    :rtype: str
    """
    if modeledit_aimmspy2.getType(aimms_model, arg) == 'index':
        return arg
    return domain_index_name


def _own_domain_index_mapping(aimms_model: Model, gii_dict: dict, component_dict: dict, identifier_text: str) -> Dict[str, str]:
    """
    Maps each free-index argument as WRITTEN in a content item's own main reference (e.g. "usbx" in
    "delta_chk( usbx, usbx1 )") back to the identifier's own DECLARED domain index name at that
    position (e.g. "reg") - the opposite preference from resolve_effective_index_name, which is used
    for ordinary content slicing/display and prefers the written name.

    An annotation-support parameter (webui::AnnotationsIdentifier for Color, webui::flagsIdentifier
    for indexed Readonly) needs the declared name instead: AIMMS validates the annotation's value as
    though it were evaluated inside the annotated identifier's OWN domain, so a generated parameter
    whose IndexDomain uses an alternate, even if range-compatible, index name fails validation
    ("X is not bound by the domain of the containing identifier Y") - real case: a real project
    declares "Parameter delta_chk { IndexDomain: (reg,reg1); }" but its WinUI Color reference (and
    two OTHER content items sharing that same Color expression) is written "delta_chk( usbx, usbx1
    )" - AIMMS accepts that for ordinary display, but rejects a Color-support parameter generated
    with IndexDomain "usbx, usbx1" once installed as delta_chk's own annotation value.

    Only positions where the written arg is itself a real Index (never a literal element or scalar
    element parameter - those select one slice, nothing to rename) are included.

    :param identifier_text: The content item's own main reference, already namespace-qualified/
        substituted (e.g. "delta_chk( usbx, usbx1 )") - this can itself already be a reference to a
        freshly-generated, not-yet-live substitution parameter (see below) rather than a real
        pre-existing model identifier.
    :type identifier_text: str
    :return: {written_name: declared_name} for positions where they differ, else {}.
    :rtype: Dict[str, str]
    """
    bare_name, written_args = tools.parse_aimms_string(identifier_text)
    synthetic_indices = gii_module.synthetic_domain_indices(gii_dict, component_dict, bare_name)
    if synthetic_indices is None and modeledit_aimmspy2.getDim(aimms_model, bare_name) < 0:
        # bare_name only exists as a queued AddIdentifier/SetAttribute edit, not yet applied to the
        # live session - e.g. investigate_contents' own "<Type>_content" substitution
        # (win_expression.potentially_substitute_expression) already replaced the widget's raw
        # WinUI expression with a reference to a brand-new parameter before Color/Readonly handling
        # even runs. getDomainIndex's behavior on an undeclared identifier is unreliable - confirmed
        # empirically to return the SAME (wrong) index name for every position queried, which then
        # collapsed two distinct written args into one, producing an invalid "IndexDomain: ccg,
        # ccg;" (AIMMS: "the index ccg is repeated"). There's also nothing meaningful to rename TO
        # here: this identifier's own queued IndexDomain (whatever was written) is already
        # authoritative, since nothing else declares it independently.
        return {}
    mapping: Dict[str, str] = {}
    for pos, arg in enumerate(written_args):
        if modeledit_aimmspy2.getType(aimms_model, arg) != 'index':
            continue
        if synthetic_indices is not None and pos < len(synthetic_indices):
            domain_index_name = synthetic_indices[pos]
        else:
            domain_index_name = modeledit_aimmspy2.getDomainIndex(aimms_model, bare_name, pos + 1)
        if domain_index_name and arg != domain_index_name:
            mapping[arg] = domain_index_name
    return mapping


def _rename_to_own_domain_indices(expr: str, args: List[str], written_to_declared: Dict[str, str]) -> Tuple[str, List[str]]:
    """
    Applies an {written: declared} mapping (see _own_domain_index_mapping) to an annotation-support
    expression and its already-parsed argument list, so both the generated parameter's own
    IndexDomain and its Definition's free indices use the annotated identifier's own declared
    names - a no-op when the mapping is empty (e.g. the written names already matched, or none of
    them were real Indexes).

    :param expr: The (already substituted) Color/Readonly expression text to rewrite.
    :type expr: str
    :param args: That same expression's own parsed arguments (tools.parse_aimms_string).
    :type args: List[str]
    :param written_to_declared: Mapping from _own_domain_index_mapping.
    :type written_to_declared: Dict[str, str]
    :return: (rewritten expr, rewritten args).
    :rtype: Tuple[str, List[str]]
    """
    if not written_to_declared:
        return expr, args
    renamed_expr = expr
    for written, declared in written_to_declared.items():
        if written != declared:
            renamed_expr = re.sub(r'(?<![A-Za-z0-9_:])' + re.escape(written) + r'(?![A-Za-z0-9_:])', declared, renamed_expr)
    renamed_args = [written_to_declared.get(a, a) for a in args]
    return renamed_expr, renamed_args


def _substitute_suffix_reference(aimms_model: Model, gii_dict: dict, component_dict: dict, page_slug: str, identifier_text: str) -> str:
    """
    AIMMS lets a Variable/Constraint content reference carry a suffix - "v_x.Lower( i_a )",
    "v_x.Marginal( i_a )", etc. - to pick which of its several values is meant. WinUI can
    display any of them directly, but WebUI's content "identifier" binding only ever resolves a
    bare identifier reference, never a "name.Suffix" one - left as-is, "v_x.Lower" round-trips
    through modeledit_aimmspy2.getDim/getDomainIndex (further down in investigate_contents) as
    an unrecognized identifier, silently losing its slicing (dimension reported as -1/unknown).

    ".Level" is the one suffix that needs no rewriting at all: a bare Variable/Constraint
    reference already means its Level, so the suffix is simply dropped. Every other suffix
    instead gets its own ordinary Parameter - reused for every widget referencing the same
    (component, name, suffix) - whose Definition is the original suffixed reference (see
    gii_module.ensure_suffix_parameter) - and identifier_text is rewritten to reference that
    Parameter instead, from this point on an entirely ordinary indexed Parameter reference (same
    approach as _substitute_set_indicator_reference above).

    A "." only ever separates a suffix from a Variable/Constraint reference - checked via
    modeledit_aimmspy2.getType(bare_name), not just "does the text contain a dot", since either
    of two other things can also produce one:
    1. An Index has no suffixes at all (only a Variable/Constraint does) - e.g. a table content
       reference literally naming an Index before the dot is never a suffix reference, whatever
       word follows the dot.
    2. WinUI's "VALUE(...) := <expr>" dynamic-substitution form (handled by win_expression.
       potentially_substitute_expression, which runs AFTER this) has no trailing "(...)" of its
       own for tools.parse_aimms_string to find, so its ENTIRE text - "VALUE(...) := <expr>" -
       becomes `name` here; if <expr> itself contains a "." anywhere (e.g. a member reference
       unrelated to any suffix, as in a real RSC model case that motivated this check), naively
       splitting on it produced a nonsense bare_name spanning from "VALUE" up to that dot,
       silently corrupting the substitution instead of leaving it for
       potentially_substitute_expression to handle correctly.
    A plain, unsuffixed reference (no ".", the common case) is returned unchanged, same as either
    of the two cases above once the type check rules them out.

    :param aimms_model: AIMMS model handle used to inspect the referenced identifier's domain.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary; any new-identifier commands are queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param page_slug: Slug of the WebUI page this reference belongs to - any generated Parameter
        is filed into that page's own Section (see gii_module.ensure_page_section).
    :type page_slug: str
    :param identifier_text: The (already namespace-qualified) content reference text.
    :type identifier_text: str
    :return: The rewritten reference, or identifier_text unchanged when it carries no suffix.
    :rtype: str
    """
    name, args = tools.parse_aimms_string(identifier_text)
    dot_pos = name.find('.')
    if dot_pos < 0:
        return identifier_text

    bare_name = name[:dot_pos]
    suffix = name[dot_pos + 1:]

    if modeledit_aimmspy2.getType(aimms_model, bare_name) not in ('variable', 'constraint'):
        return identifier_text

    args_text = f"({', '.join(args)})" if args else ""

    if suffix.lower() == "level":
        return f"{bare_name}{args_text}"

    identifier_dim = max(modeledit_aimmspy2.getDim(aimms_model, bare_name), 0)
    index_names = [modeledit_aimmspy2.getDomainIndex(aimms_model, bare_name, pos + 1) for pos in range(identifier_dim)]

    param_name = gii_module.ensure_suffix_parameter(gii_dict, component_dict, page_slug, bare_name, suffix, index_names, f"{bare_name}.{suffix}{args_text}")
    lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""
    qualified_param_name = f"{lib_prefix}{gii_module.get_prefix(component_dict)}::{param_name}"
    # The generated Parameter's own name (e.g. "p_v_x_lower") means nothing to a WebUI user -
    # register the original suffixed reference as its webui::IdentifierElementText fallback text
    # (e.g. "v_x.lower"), the same mechanism used for a widget's row/column index headers above.
    identifier_element_text.add_element_safely(aimms_model, qualified_param_name, f"{bare_name}.{suffix.lower()}")
    return f"{qualified_param_name}{args_text}"


def _substitute_set_indicator_reference(aimms_model: Model, gii_dict: dict, component_dict: dict, page_slug: str, identifier_text: str) -> str:
    """
    WinUI can display a Set directly in a Table or Selection Object - either its own membership
    against a named domain set ("SubsetName( DomainSet )"), or, for a Table, a bare set name
    with no domain argument at all ("SetName" alone - shorthand for "against itself"). A Set can
    also be a "relation" over several other sets at once - declared with a tuple SubsetOf (e.g.
    "Set s_uvw { SubsetOf: (s_u,s_v,s_w); }") - and WinUI displays THAT membership the same way,
    with one domain argument per dimension ("s_uvw( s_u, s_v, s_w )"). WebUI has no widget that
    can bind to a raw Set, only to an ordinary Parameter, so any of these is rewritten here into
    a reference to an auto-generated binary "indicator" Parameter (1 exactly where the domain
    tuple is a member) over one auto-generated Index per domain set - see gii_module.
    ensure_indicator_index/ensure_indicator_parameter. From this point on the rewritten reference
    ("giim::bp_indicator_X(i_indicator_Y, ...)") is an entirely ordinary indexed Parameter
    reference, so every caller of investigate_contents() needs no further changes (including its
    per-argument row/column placement, which already handles any number of domain indices) -
    win_elemselec.py separately decides the WebUI widget type ("multiselect" instead of
    "selectionbox-v2") for the Selection Object case.

    The Parameter itself is fully qualified (component prefix, if any, plus giim/giil) - unlike
    the Index arguments inside the parens (left bare), a WebUI widget's content binding is
    evaluated from outside the widget's own component, so a bare reference to something nested
    inside this component's own GeneratedInterfaceIdentifiers module doesn't resolve (same
    lesson as win_object_tools.resolve_widget_visibility's negation-parameter reference).

    The indicator Parameter's own IndexDomain is name's own declared canonical domain - its
    "Subset Of" tuple (e.g. "Set s_gh { SubsetOf: (s_g,s_h); }" - one index per dimension, each
    that dimension's own declared "Index:" if it has one, else an auto-generated
    ensure_indicator_index one) - NOT whatever a particular reference happens to write per
    dimension. A reference can narrow a dimension down to a further subset via an Index that
    ranges over it - e.g. "s_gh( s_g, i_hd )", where i_hd is s_hd's own declared Index and s_hd is
    a further subset of s_gh's second SubsetOf dimension s_h - the same "written with a different,
    range-compatible Index than the identifier's own declared one" pattern
    resolve_effective_index_name already handles for an ordinary Parameter reference. Building the
    Parameter once with its FULL canonical domain (confirmed with the user after an initial,
    wrong attempt at this that instead built the IndexDomain from whatever a single reference
    happened to write, e.g. "(i_g, i_hd)" - underselling the indicator's own domain to just the
    first reference's own restriction) lets it be reused unchanged by every widget referencing
    this Set, however each one slices it - exactly like any ordinary, already-declared Parameter's
    own fixed IndexDomain; each reference's own per-dimension restriction (a plain Set, or an
    Index over a subset of the canonical dimension) still flows through untouched into the
    returned reference, so investigate_contents' existing per-argument free/subset detection
    handles it exactly as it would for any other Parameter.

    Each argument (if any) must be either a Set (the display domain, one per dimension - a plain,
    unindexed Set reused directly, an indexed set family's own single-index reference like
    "SetFamily(i)" is out of scope since i is an Index, not a Set) or an Index ranging over a
    domain-compatible (sub)set. modeledit_aimmspy2.getDim() reports 1 even for a plain, unindexed
    Set (not 0 as might be expected), so it can't distinguish a bare Set from an indexed set
    family reference; checking each argument's own type instead sidesteps that ambiguity, and
    generalizes unchanged to a relation's several arguments. Same narrow scope as win_elemselec.
    _resolve_scalar_parameter_identifier's for the scalar case. Anything not matching (an argument
    that's neither a Set nor an Index, or one whose count doesn't match name's own declared
    dimension) leaves the whole reference unrewritten.

    :param aimms_model: AIMMS model handle used to inspect the referenced identifier's type.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary; any new-identifier commands are queued here.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param page_slug: Slug of the WebUI page this reference belongs to - any generated Index/
        Parameter is filed into that page's own Section (see gii_module.ensure_page_section).
    :type page_slug: str
    :param identifier_text: The (already namespace-qualified) content reference text.
    :type identifier_text: str
    :return: The rewritten reference when identifier_text is a Set reference, else identifier_text unchanged.
    :rtype: str
    """
    name, args = tools.parse_aimms_string(identifier_text)
    if modeledit_aimmspy2.getType(aimms_model, name) != 'set':
        return identifier_text
    written_args = args if args else [name]
    if any(modeledit_aimmspy2.getType(aimms_model, arg) not in ('set', 'index') for arg in written_args):
        return identifier_text

    # name's own declared domain - the "Subset Of" tuple ("(s_g,s_h)"), a single set ("s_abc",
    # for a plain 1-D subset), or, for a Set with no declared superset of its own (a root Set),
    # itself - the same "against itself" shorthand as a bare reference with no domain argument.
    # AIMMS's own meta-API can report "Subset Of" as the literal text "<Error>" instead of an
    # empty string, even for an ordinary, successfully-declared identifier (confirmed against a
    # real project - modeledit_aimmspy2.getAttribute(..., "index") on the very same identifier
    # succeeds where "Subset Of" doesn't, so this isn't identifier-resolution failure in general,
    # just this one attribute) - never trust it blindly, or "<Error>" itself gets treated as a
    # (bogus) domain set name and baked straight into the generated Parameter's own IndexDomain.
    # When it can't be determined (or its dimension count doesn't match this reference's own
    # argument count - shouldn't normally happen, but fail safe), fall back to resolving each
    # dimension from what THIS reference itself wrote instead - the same behavior as before this
    # canonical-domain refinement (every dimension ends up "free", same as a plain Parameter
    # reference that names its own full declared domain).
    subset_of_text = modeledit_aimmspy2.getAttribute(aimms_model, name, "Subset Of").strip()
    if subset_of_text in ("", "<Error>"):
        canonical_domain_sets = written_args
    elif subset_of_text.startswith('(') and subset_of_text.endswith(')'):
        canonical_domain_sets = [s.strip() for s in subset_of_text[1:-1].split(',')]
    else:
        canonical_domain_sets = [subset_of_text]
    if len(canonical_domain_sets) != len(written_args):
        canonical_domain_sets = written_args

    index_names = []
    for domain_set in canonical_domain_sets:
        if modeledit_aimmspy2.getType(aimms_model, domain_set) == 'index':
            index_names.append(domain_set)
            continue
        # A Set can declare several alternative Index names for the very same dimension (e.g.
        # "Set Plants { Index: pl, pl1; }") - getAttribute returns all of them, comma-joined;
        # only the first (the set's own primary index) is a single valid index reference here -
        # treating the whole joined string as one index name silently doubles the dimension count
        # once it's re-split downstream (investigate_contents re-parsing the returned reference),
        # desynchronizing it from _synthetic_dims' own (correct, singular) count and crashing.
        own_index = modeledit_aimmspy2.getAttribute(aimms_model, domain_set, "index").split(',')[0].strip()
        index_names.append(own_index if own_index not in ("", "<Error>") else
                            gii_module.ensure_indicator_index(gii_dict, component_dict, page_slug, domain_set))

    param_name = gii_module.ensure_indicator_parameter(gii_dict, component_dict, page_slug, name, index_names)
    lib_prefix = f"{component_dict['Prefix']}::" if component_dict['Prefix'] != "" else ""
    qualified_param_name = f"{lib_prefix}{gii_module.get_prefix(component_dict)}::{param_name}"
    # The generated indicator Parameter's own name (e.g. "bp_indicator_s_uvw") means nothing to
    # a WebUI user either - same reasoning as the indicator Index's own webui::
    # IdentifierElementText fallback (see investigate_contents' per-argument loop) - register the
    # Set it actually displays (e.g. "s_uvw") as its fallback text instead.
    identifier_element_text.add_element_safely(aimms_model, qualified_param_name, name)

    # Per dimension: the reference's own written arg when it's a genuine restriction (an Index
    # that isn't exactly this dimension's own canonical index - e.g. "i_hd" narrowing s_h down to
    # s_hd), else the canonical index itself (a written arg that already names the canonical
    # dimension in full, or the bare "no domain argument at all" case) - investigate_contents'
    # existing per-argument free/subset detection (comparing each returned arg against the
    # Parameter's own now-canonical IndexDomain) sorts out which is which from here on, the same
    # as it already does for p_phg( i_hd, i_g ) on the very same page.
    returned_args = [
        written if (modeledit_aimmspy2.getType(aimms_model, written) == 'index' and written != canonical)
        else canonical
        for written, canonical in zip(written_args, index_names)
    ]
    return f"{qualified_param_name}({', '.join(returned_args)})"


def investigate_contents(aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_data_xml:ET.Element, content_lists_expected:dict, stable_id:str) -> dict:
    """
    Inspect WinUI data content and translate identifiers, slicing, and headers into WebUI-compatible structures.

    :param aimms_model: AIMMS model handle used to inspect identifiers and their domains.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary used for context during expression substitution.
    :type webui_page_dict: dict
    :param page_name: Name of the page being processed.
    :type page_name: str
    :param winui_data_xml: XML element representing the WinUI data definition.
    :type winui_data_xml: ET.Element
    :param content_lists_expected: Flags describing which content partitions should be constructed.
    :type content_lists_expected: dict
    :param stable_id: Stable identity of the widget being converted (see compute_stable_id), used to
        name any AIMMS identifiers generated for it.
    :type stable_id: str
    :return: Dictionary describing contents, partitions, and optional focus information for WebUI widgets.
    :rtype: dict
    """

    page_slug = page_slug_from_stable_id(stable_id)
    store_focus_in = {} # to store info from reverse links in Pivot tables, and 'link to parameters' in contents of WinUI data objects.
    contents_xml = winui_data_xml
    pivot_arrangement = None
    header_title = '' # a Pivot Table's own <Indices><Identifier_Index><Header_Title> - see below.
    if winui_data_xml.get('Type') == 'Pivot Table':
        pivot_uuid_element = winui_data_xml.find('ObjectUUID')
        if pivot_uuid_element is not None and pivot_uuid_element.text:
            pivot_uuid = pivot_uuid_element.text.strip().upper()
            pivot_arrangement = component_dict.get("PivotState", {}).get(pivot_uuid)
            if pivot_arrangement is not None:
                win_pivot_state.log_folded_indices(component_dict, page_name, stable_id, pivot_arrangement["folded"])
        for table_cat in winui_data_xml:
            if table_cat.tag == 'Contents':
                contents_xml = table_cat
        for content_child in winui_data_xml:
            if content_child.tag == 'Indices':
                # pivot tables also provide an alternative way for specifying reverse links, namely via the explicit indices.
                for content_grandchild in content_child:
                    if content_grandchild.tag == 'Explicit_Index':
                        index_elem_name = ''
                        index_elem_link_to_param = ''
                        for index_elem in content_grandchild:
                            if index_elem.tag == 'Index':
                                index_elem_name = str(index_elem.text)
                            if index_elem.tag == 'Link_to_Element_Parameter':
                                index_elem_link_to_param = str(index_elem.text)
                        if index_elem_name != '' and index_elem_link_to_param != '':
                            store_focus_in[index_elem_name] = index_elem_link_to_param
                    if content_grandchild.tag == 'Identifier_Index':
                        # The Symbols-axis header's own title, set interactively in the WinUI IDE
                        # (Table Contents > right-click the identifier header > Properties) - used
                        # as a fallback widget title (see win_pivot_table.winpage_pivot_table) when
                        # nothing else (a caption Text object, win_layout.py) supplies one.
                        for identifier_index_child in content_grandchild:
                            if identifier_index_child.tag == 'Header_Title' and type(identifier_index_child.text) is str:
                                header_title = identifier_index_child.text
                                if len(header_title) > 1 and header_title[0] == '"' and header_title[-1] == '"':
                                    header_title = header_title[1:-1]

    # behavior differs for scalar/selectionbox versus indexed data.
    if content_lists_expected['objecttype'] == 'scalar' or content_lists_expected['objecttype'] == 'selectionbox-v2':
        is_scalar = 1
    else:
        is_scalar = 0

    no_identifiers = determine_no_identifiers(contents_xml)
    if no_identifiers == 0:
        # A Composite Table/Sparse List can specify a <Domain> (which identifier/index drives
        # its rows) without a single <ExplicitIdentifier> column of its own - e.g. a table meant
        # only to browse/select the domain's own members. WinUI still renders that domain as one
        # column, so mint a real ExplicitIdentifier for it (same Identifier text as <Domain>'s
        # own) and let every existing per-identifier code path below (decimals/readonly/header
        # text, row/column placement, contents_list, ...) handle it exactly like any other
        # column - rather than duplicating that logic here.
        domain_id_elem = contents_xml.find('Domain/Identifier') if contents_xml.get('Type', '') in {'Composite Table', 'Sparse List'} else None
        if domain_id_elem is not None and domain_id_elem.text:
            synthetic_identifier = ET.SubElement(contents_xml, 'ExplicitIdentifier')
            ET.SubElement(synthetic_identifier, 'Identifier').text = domain_id_elem.text
            no_identifiers = 1
        else:
            print(f"Warning: no identifiers found in contents of page {page_name}?")
            return_dict: dict[str, Any] = {}
            return return_dict

    identifier_text:str

    domain_identifier = ''
    domain_identifier_args: List[str] = []
    domain_slices: List[dict] = []

    for table_child in contents_xml:
        if table_child.tag == 'Domain':
            for table_grandchild in table_child:
                if table_grandchild.tag == 'Identifier':
                    if type(table_grandchild.text) is str:
                        domain_identifier_text = table_grandchild.text
                        purpose = str(contents_xml.get('Type',"surprise") ).replace(' ','_') + "_domain"
                        domain_identifier_text = namespace_qualification( aimms_model, domain_identifier_text, component_dict['Prefix'] )
                        # A <Domain> reference can itself need the same rewriting as an
                        # ExplicitIdentifier's own content reference (see the identical sequence
                        # further down) - most commonly a raw Set (a relation like "s_uvw( s_u,
                        # s_v, s_w )" - see _substitute_set_indicator_reference), which WebUI's
                        # displaydomain binding can't resolve any more than its content binding
                        # can. Same order as below: suffix, then set-indicator, then the general
                        # VALUE(...):=... substitution.
                        domain_identifier_text = _substitute_suffix_reference(aimms_model, gii_dict, component_dict, page_slug, domain_identifier_text)
                        domain_identifier_text = _substitute_set_indicator_reference(aimms_model, gii_dict, component_dict, page_slug, domain_identifier_text)
                        domain_identifier_text = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict, purpose, domain_identifier_text, stable_id, 0)
                        identifier_text_name, identifier_text_args = tools.parse_aimms_string(domain_identifier_text)
                        domain_identifier = identifier_text_name
                        domain_identifier_args = identifier_text_args
                        # Not yet live in the AIMMS session when domain_identifier is a freshly
                        # generated synthetic Parameter (see _substitute_set_indicator_reference/
                        # gii_module.ensure_indicator_parameter) - consult its known domain
                        # instead of modeledit_aimmspy2.getDomainIndex, same fallback as the
                        # ExplicitIdentifier loop further down.
                        domain_synthetic_indices = gii_module.synthetic_domain_indices(gii_dict, component_dict, domain_identifier)
                        for argpos, arg in enumerate(domain_identifier_args):
                            if domain_synthetic_indices is not None:
                                domain_index_name = domain_synthetic_indices[argpos]
                            else:
                                domain_index_name = modeledit_aimmspy2.getDomainIndex(aimms_model, domain_identifier, argpos + 1)
                            is_scalar_element_parameter = modeledit_aimmspy2.isScalarElementParameter( aimms_model, arg )
                            if is_scalar_element_parameter == 0:
                                arg_type = "free" if arg == domain_index_name else "subset"
                            else:
                                arg_type = "element-parameter"
                            qualified_domain_index_name = gii_module.qualify_synthetic_index(gii_dict, component_dict, domain_index_name)
                            domain_slices.append({
                                "index": qualified_domain_index_name,
                                "type": arg_type,
                                "value": qualified_domain_index_name if arg_type == "free" else arg
                            })

    default_first_column = 31 if contents_xml.get('Type','') in { 'Composite Table', 'Sparse List' } else -1
    first_column = default_first_column
    return_dict = {}
    contents_list = []
    # One entry per ExplicitIdentifier that needs a non-trivial slice (only_free == 0 for that
    # identifier - see the per-identifier loop below) - a widget with several content items (a
    # multi-curve chart, a multi-column table, ...) needs one slices_entry PER item that has one,
    # not just the last one processed (web_page.add_data_widget's own lookup already tolerates a
    # missing entry for a fully-free identifier, falling back to "free" for every one of its
    # args, so a fully-free identifier is deliberately left out here rather than padded in).
    all_slices_entries: List[dict] = []
    rowheader_list = []
    colheader_list = []
    # A Pivot Table's own .DeveloperState arrangement (pivot_arrangement["row"]/["col"]) already
    # carries the real display order for its axis (win_pivot_state.py preserves the order
    # interpreter records were written in) - appending to rowheader_list/colheader_list as each
    # identifier's own arg happens to be encountered (their DECLARATION order, e.g. "P4c(j,k,l,m)")
    # ignores that entirely. Track each placed entry's own pivot_state_key here so it can be
    # re-sorted into .DeveloperState's own order once every identifier's args are in (see the
    # in-order rebuild after the per-identifier loop) - confirmed the hard way against real WinUI
    # (w2w0027 pagetwo/area-e, pagethree/area-f: e.g. DeveloperState's own col order is [m,l,k],
    # not [k,l,m], the order P4c's own declared args happen to appear in).
    row_pivot_state_keys: Dict[str, str] = {}
    col_pivot_state_keys: Dict[str, str] = {}
    aggregate_list = []
    header_list = []
    grouped_list = []
    stacked_list: list[str] = []
    overlay_list = []

    # For each explicit identifier idn, whereby decimals, readonly, (in)visible is specified, 
    # there will be an entry of the form: identifier_name : { "literal" : 0/1, "value" : number or name }
    decimals_dict = {}
    visible_dict  = {}
    readonly_dict = {}
    item_index = 0
    for table_child in contents_xml:

        if table_child.tag == 'ExplicitIdentifier' or table_child.tag == 'Explicit_Identifier':

            item_index += 1

            no_decimals = 2
            literal_num_decimals = 0
            literal_name_decimals = 0
            ro_val = 0

            hid_seen = 0
            ro_seen = 0
            color_seen = 0

            header_text = ""
            header_from_text_attrib = 0

            # <FirstColumn> is per-ExplicitIdentifier - reset for each one instead of leaking a
            # prior identifier's value into a sibling that doesn't specify its own (and track
            # whether THIS identifier actually set it, vs. just inheriting default_first_column).
            first_column = default_first_column
            first_column_explicit = False

            # Determine Identifier text, and some other attributes.
            for table_grandchild in table_child:

                if table_grandchild.tag in { 'HeaderText', 'TitleText', 'Title', 'Description' }:
                    if type(table_grandchild.text) is str:
                        header_text = table_grandchild.text
                    
                if table_grandchild.tag == 'IdentifierTextInTitle':
                    header_from_text_attrib = 1  

                if table_grandchild.tag == 'Identifier':
                    identifier_text = ""
                    if type(table_grandchild.text) is str:
                        identifier_text = table_grandchild.text
                     
                if table_grandchild.tag == 'NumberFormat':
                    if 'Decimals' in table_grandchild.attrib:
                        no_decimals = int( table_grandchild.attrib['Decimals'] )
                        literal_num_decimals = 1

                if table_grandchild.tag == 'NrDecimals':
                    if type(table_grandchild.text) is str:
                        name_decimals = str(table_grandchild.text)
                        literal_name_decimals = 1

                if table_grandchild.tag == 'Readonly':
                    if type(table_grandchild.text) is str:
                        ro_txt = str(table_grandchild.text)
                        ro_seen = 1
                        if ro_txt == '1' or ro_txt == '"Yes"':
                            ro_literal = 1
                            ro_val = 'true'
                        elif ro_txt == '0' or ro_txt == '"No"':
                            ro_literal = 1
                            ro_val = 'false'
                        else:
                            ro_literal = 0
                            ro_val = ro_txt

                if table_grandchild.tag == 'Hidden':
                    if type(table_grandchild.text) is str:
                        hid_txt = str(table_grandchild.text)
                        hid_seen = 1
                        if hid_txt == '1' or hid_txt == '"Yes"':
                            hid_literal = 1
                            hid_val = 1
                        elif hid_txt == '0' or hid_txt == '"No"':
                            hid_literal = 1
                            hid_val = 0
                        else:
                            hid_literal = 0
                            hid_val = hid_txt

                if table_grandchild.tag == 'FirstColumn':
                    if type(table_grandchild.text) is str:
                        first_column = int( table_grandchild.text )
                        first_column_explicit = True

                if table_grandchild.tag == 'Colors':
                    # Table content: <Colors><Background_Color>expr</Background_Color></Colors>.
                    for color_grandchild in table_grandchild:
                        if color_grandchild.tag == 'Background_Color':
                            if type(color_grandchild.text) is str:
                                color_txt = str(color_grandchild.text)
                                color_seen = 1

                if table_grandchild.tag == 'Color':
                    # Line/bar chart content: <Color>expr</Color> directly.
                    if type(table_grandchild.text) is str:
                        color_txt = str(table_grandchild.text)
                        color_seen = 1

            # Substitute the content Identifier text now (it may be a "VALUE[(indices)] := expr"
            # / "STRING := expr" / "ELEMENT(...) -> set := expr" expression - possibly spanning
            # multiple source lines - rather than a bare identifier reference), so every use
            # below (the readonly/color annotation targets, and the content processing further
            # down) shares one correctly-resolved, single-line identifier reference instead of
            # raw source text. tools.parse_aimms_string can't make sense of the raw form: it
            # isn't "name(args)" shaped, and its regex doesn't span embedded newlines.
            if identifier_text != '' and identifier_text != '""':
                purpose = str(contents_xml.get('Type', "surprise")).replace(' ', '_') + "_content"
                identifier_text = namespace_qualification(aimms_model, identifier_text, component_dict['Prefix'])
                identifier_text = _substitute_suffix_reference(aimms_model, gii_dict, component_dict, page_slug, identifier_text)
                identifier_text = _substitute_set_indicator_reference(aimms_model, gii_dict, component_dict, page_slug, identifier_text)
                identifier_text = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict, purpose, identifier_text, stable_id, item_index)

            # decimals handling.
            if literal_name_decimals == 1:
                decimals_entry = {
                    "literal" : 0,
                    "value" : name_decimals
                }
            elif literal_num_decimals == 1:
                decimals_entry = {
                    "literal" : 1,
                    "value" : no_decimals
                }
            else:
                decimals_entry = {}

            # visibility handling
            if hid_seen:
                if hid_literal:
                    if hid_val == 1:
                        vis_val = 'Never Show'
                    else:
                        vis_val = 'Always Show'
                    visible_entry = {
                        "literal": 1,
                        "value": vis_val
                    }
                else:
                    hid_txt = hid_val
                    if hid_txt.startswith('VALUE'):
                        vis_expr = "1 - ( " + hid_txt[8:] + " )"
                    else:
                        vis_expr = f"1 - {hid_txt}"
                    vis_expr = namespace_qualification(aimms_model, vis_expr, component_dict['Prefix'])
                    index_domain = ""
                    vis_num_id  = win_expression.make_webui_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "visibility", vis_expr, index_domain, "numeric", "", stable_id, item_index)
                    # 'Never Show', 'Always Show'
                    visibility_values_set = gii_module.ensure_visibility_values(gii_dict, component_dict, page_slug)
                    vis_elem_id = win_expression.make_webui_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "visibility", f"if {vis_num_id} then 'Always Show' else 'Never Show' endif",
                                                                             index_domain, "element", f"{gii_module.get_prefix(component_dict)}::{visibility_values_set}", stable_id, item_index)
                    visible_entry = {
                        "literal": 0,
                        "value": vis_elem_id
                    }
            else:
                visible_entry = {}

            # readonly handling
            if ro_seen:
                if ro_literal:
                    ro_entry = {
                        "literal": 1,
                        "value": ro_val
                    }
                else:
                    # here the ro control is not a literal.
                    # Two steps:
                    # 1. Substitute the WinUI readonly text (a bare identifier, or a
                    #    "VALUE[(indices)] := expr" expression) into a numeric identifier reference,
                    #    indexed if the source was (e.g. "VALUE( i_a ) := ..." per w2w0014).
                    # 2. a. scalar result -> reduce to a 'True'/'False' element, like Visibility above.
                    #    b. indexed result -> can't be reduced to one value for the whole widget, so
                    #       drive it through the 'webui::flagsIdentifier' annotation instead.
                    ro_txt = ro_val
                    ro_num_id = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict,
                                                                                  "readonly", ro_txt, stable_id, item_index)

                    index_domain = ""
                    _, ro_num_args = tools.parse_aimms_string(ro_num_id)
                    ro_index_args = filter_index_args(aimms_model, ro_num_args)
                    if ro_index_args:
                        # Indexed: can't reduce to a single scalar value, so drive it via the
                        # 'webui::flagsIdentifier' annotation instead of s_readonly_values.
                        # identifier_text may still carry its own index arguments (e.g. "p_b( i_let )")
                        # at this point - the annotation target must be the bare identifier name.
                        ro_annotation_name, _ = tools.parse_aimms_string(identifier_text)
                        # The generated support parameter's own IndexDomain (and the free indices in
                        # its own Definition below) must match ro_annotation_name's OWN declared
                        # domain names exactly, not whatever range-compatible alternate was written
                        # here - see _own_domain_index_mapping.
                        own_domain_mapping = _own_domain_index_mapping(aimms_model, gii_dict, component_dict, identifier_text)
                        ro_num_id, ro_index_args = _rename_to_own_domain_indices(ro_num_id, ro_index_args, own_domain_mapping)
                        index_domain = ", ".join(ro_index_args)
                        # The generated support parameter must live in whichever component
                        # DECLARES ro_annotation_name, not wherever this page lives - see
                        # resolve_identifier_owner_component. Otherwise a library page displaying
                        # a main-model identifier's Readonly would mint its own generated
                        # parameter in the library's own module, and since the annotation is a
                        # single slot on the shared identifier, a second, different library page
                        # referencing the same identifier would silently overwrite the first.
                        owner_component_dict = resolve_identifier_owner_component(gii_dict, component_dict, ro_annotation_name)
                        ro_elem_id = win_expression.make_webui_reference(aimms_model, gii_dict, owner_component_dict, webui_page_dict, "readonly",
                                                                                 f"\"readonly\" $ {ro_num_id}",
                                                                                 index_domain, "string", "", stable_id, item_index)
                        gii_dict["_edit_queue"].append(afe.SetAnnotation(identifier=ro_annotation_name, annotation='webui::flagsIdentifier', value=ro_elem_id,
                                                                          file_hint=owner_component_dict["AmsPath"]))
                    else:
                        readonly_values_set = gii_module.ensure_readonly_values(gii_dict, component_dict, page_slug)
                        ro_elem_id = win_expression.make_webui_reference(aimms_model, gii_dict, component_dict, webui_page_dict, "readonly",
                                        f"if {ro_num_id} then 'True' else 'False' endif", index_domain, "element", f"{gii_module.get_prefix(component_dict)}::{readonly_values_set}", stable_id, item_index)

                    ro_entry = {
                        "literal": 0,
                        "value": ro_elem_id
                    }
            else:
                ro_entry = {}

            # color handling: a table's Colors/Background_Color, or a line/bar chart's Color,
            # names a (possibly indexed) AllColors element - e.g. ep_color(i_let) : 'green' - or,
            # instead, a literal RGB value (e.g. "RGB<0,128,0>" or "RGB 008000") rather than an
            # identifier reference. WebUI turns a webui::AnnotationsIdentifier value of
            # "color-<name>" into the CSS class annotation-color-<name> on the corresponding
            # cell/point/bar; win_color.py supplies the stylesheet (w2w-color.css) that defines
            # those classes. Only with --colors (gii_dict["_colors"]) - see winui_to_webui.process_aimms_app.
            if color_seen and gii_dict.get("_colors", False):
                color_literal_rgb = win_color_scan.rgb_from_literal_text(color_txt.strip())
                # WinUI's flattened "<GUID> <Name>" reference to a Settings/UserColors.xml entry
                # (the same project color a nested "<UserColor GUID="..">Name</UserColor>" child
                # element would reference - see win_color_scan.user_color_name_from_literal_text)
                # - only checked when it isn't a literal RGB value, since neither form's text can
                # also be the other's.
                user_color_name = None if color_literal_rgb is not None else win_color_scan.user_color_name_from_literal_text(color_txt.strip())
                if color_literal_rgb is not None or user_color_name is not None:
                    # A literal RGB value or named UserColors.xml reference, not an AIMMS
                    # identifier/expression reference - win_color_scan's project-wide scan (see
                    # winui_to_webui.py) already registers the RGB case under a synthesized
                    # element name in giim::s_AllColors, and scan_user_colors() already registers
                    # every UserColors.xml entry regardless of how (or whether) a page references
                    # it. A bare quoted element literal embedded directly in formatString(...)
                    # doesn't type-check in AIMMS ("the range set can not be determined"), so give
                    # it a proper, first-class ElementParameter instead (see
                    # gii_module.register_color_literal).
                    literal_color_name = win_color_scan.color_name_for_rgb(color_literal_rgb) if color_literal_rgb is not None else user_color_name
                    color_reference_expr = gii_module.register_color_literal(gii_dict, literal_color_name)
                    index_domain = ""
                else:
                    color_num_id = namespace_qualification(aimms_model, color_txt, component_dict['Prefix'])
                    color_num_id = win_expression.potentially_substitute_expression(aimms_model, gii_dict, component_dict, webui_page_dict,
                                                                                      "color", color_num_id, stable_id, item_index)
                    color_bare_name, color_num_args = tools.parse_aimms_string(color_num_id)
                    # An argument here can be a free index (makes the result indexed), a literal
                    # element, or a scalar element parameter (e.g. FlowEl in "FlowErrorColor( FlowEl
                    # )") - the latter two SELECT one specific slice rather than indexing the result,
                    # so only the actual indices belong in the new identifier's IndexDomain.
                    #
                    # The generated support parameter's own IndexDomain (and the free indices in its
                    # own Definition, color_num_id itself below) must match the annotated identifier's
                    # (identifier_text's) OWN declared domain names exactly, not whatever
                    # range-compatible alternate was written in this Color expression - see
                    # _own_domain_index_mapping. color_bare_name (the Color expression's OWN bare
                    # name, e.g. "FlowColor2") is unaffected - only its ARGUMENTS get renamed.
                    own_domain_mapping = _own_domain_index_mapping(aimms_model, gii_dict, component_dict, identifier_text)
                    color_num_id, color_num_args = _rename_to_own_domain_indices(color_num_id, color_num_args, own_domain_mapping)
                    index_domain = ", ".join(filter_index_args(aimms_model, color_num_args))

                    # WebUI can't use AIMMS's built-in AllColors system set as-is: any identifier
                    # ranged over it gets repointed to gii::s_AllColors, a local copy created once
                    # in the main model (see gii_module.ensure_all_colors_values, called after the
                    # per-component loop once every such identifier has been collected). Record a
                    # file_hint too - component_dict here is whichever component's *page* references
                    # the color identifier, which isn't necessarily the component the identifier is
                    # itself declared in (a library page can display a main-model identifier), so
                    # this can be wrong; AmsProject._resolve() falls back to a project-wide search
                    # when the hint doesn't match, so a wrong hint here is harmless, just unhelpful.
                    # modeledit_aimmspy2.getAttribute's attr argument is looked up against
                    # AllAttributeNames by its internal (lowercase) spelling, not the
                    # capitalized label AIMMS's own UI shows - "range", not "Range".
                    if modeledit_aimmspy2.getAttribute(aimms_model, color_bare_name, "range") == "AllColors":
                        gii_dict.setdefault("_all_colors_identifiers", {})[color_bare_name] = component_dict["AmsPath"]
                    color_reference_expr = color_num_id

                # Routed through giim::p_ColorSlug rather than embedding {color_reference_expr}'s
                # own element text directly (%e) - a raw s_AllColors name isn't always a safe
                # single CSS class-name token (e.g. a multi-word UserColor or built-in AllColors
                # member like 'light grey' - see gii_module.ensure_all_colors_values), and
                # p_ColorSlug's own Definition is what win_color.py's generated CSS classes
                # actually match against.
                color_annotation_name, _ = tools.parse_aimms_string(identifier_text)
                # The generated support parameter must live in whichever component DECLARES
                # color_annotation_name, not wherever this page lives - see
                # resolve_identifier_owner_component. Otherwise a library page displaying a
                # main-model identifier's Color would mint its own generated parameter in the
                # library's own module, and since the annotation is a single slot on the shared
                # identifier, a second, different library page referencing the same identifier's
                # Color would silently overwrite the first (only the last one processed would
                # actually take effect for every page displaying it).
                owner_component_dict = resolve_identifier_owner_component(gii_dict, component_dict, color_annotation_name)
                color_annot_id = win_expression.make_webui_reference(aimms_model, gii_dict, owner_component_dict, webui_page_dict, "color",
                                                                       f'formatString("color-%s", {gii_module.MAIN_PREFIX}::{gii_module.COLOR_SLUG_PARAM_NAME}({color_reference_expr}))',
                                                                       index_domain, "string", "", stable_id, item_index)
                gii_dict["_edit_queue"].append(afe.SetAnnotation(identifier=color_annotation_name, annotation='webui::AnnotationsIdentifier', value=color_annot_id,
                                                                  file_hint=owner_component_dict["AmsPath"]))
                # w2w-color.css itself isn't written until the whole per-component loop is done
                # and the full color registry is known (see winui_to_webui.py, after
                # gii_module.ensure_all_colors_values) - just flag that it's needed at all.
                gii_dict["_color_css_needed"] = True

            # Process Identifier text, and place in appropriate lists.
            # (already namespace-qualified and substituted above, before the readonly/color
            # annotation-target handling that also needs it.)
            if identifier_text != '' and identifier_text != '""':
                identifier_text_name, identifier_text_args = tools.parse_aimms_string(identifier_text)
                suffix_list_start_pos = identifier_text_name.find('.[')
                if suffix_list_start_pos >= 0:

                    pure_name = identifier_text_name[:suffix_list_start_pos]
                    suffix_text = identifier_text_name[suffix_list_start_pos+2:]
                    komma_pos = suffix_text.find(',')
                    bracket_close_pos = suffix_text.find(']')

                    while komma_pos >= 0 and komma_pos < bracket_close_pos:

                        # Store
                        temp_text_name = pure_name + '.' + suffix_text[:komma_pos]
                        contents_list.append( temp_text_name )

                        # Shift Suffix text
                        suffix_text = suffix_text[komma_pos+1:]
                        komma_pos = suffix_text.find(',')

                    # Store last id.suffix
                    bracket_close_pos = suffix_text.find(']')
                    temp_text_name = pure_name + '.' + suffix_text[:bracket_close_pos]
                    contents_list.append( temp_text_name )

                    identifier_text_name = pure_name
                else:
                    contents_list.append( identifier_text_name )
                    dot_pos = identifier_text_name.find('.')
                    if dot_pos >=0:
                        identifier_text_name= identifier_text_name[:dot_pos]

                # Determine full identifier text name, including prefix.
                # if component_dict["Prefix"] == "":
                #     full_identifier_text_name = identifier_text_name 
                # else:
                #     full_identifier_text_name = component_dict["Prefix"] + "::" + identifier_text_name
                full_identifier_text_name = identifier_text_name

                # Determine header text, if it comes from the identifier declaration in the AIMMS model.
                if header_text == "":
                    if header_from_text_attrib:
                        header_text = modeledit_aimmspy2.getText(aimms_model, full_identifier_text_name)

                # Remove surrounding quotes from header text, if any.   
                if len(header_text) > 2 and header_text[0] == '"' and header_text[-1] == '"':
                    header_text = header_text[1:-1]

                if header_text != "":
                    identifier_element_text.add_element_safely( aimms_model, full_identifier_text_name, header_text)

                identifier_text_no_args = len( identifier_text_args )
                # A freshly generated synthetic indicator Parameter (see
                # win_object_tools._substitute_set_indicator_reference /
                # gii_module.ensure_indicator_parameter) only exists as a queued text edit at
                # this point, not yet in the live AIMMS session - modeledit_aimmspy2.getDim/
                # getDomainIndex would report it as undeclared, so consult the known dimension
                # recorded when it was created first.
                synthetic_indices = gii_module.synthetic_domain_indices(gii_dict, component_dict, identifier_text_name)
                if synthetic_indices is not None:
                    identifier_dim = len(synthetic_indices)
                else:
                    identifier_dim = modeledit_aimmspy2.getDim(aimms_model, identifier_text_name)
                if (identifier_dim >= 0) and ( identifier_dim != identifier_text_no_args):
                    print(f"Warning: identifier '{identifier_text_name}' has dimension {identifier_dim} but {identifier_text_no_args} arguments in WinUI.")
                identifier_text_indices = []
                for indexPos in range(1, identifier_text_no_args + 1):
                    if synthetic_indices is not None:
                        domain_index_name = synthetic_indices[indexPos - 1]
                    else:
                        domain_index_name = modeledit_aimmspy2.getDomainIndex(aimms_model, identifier_text_name, indexPos)
                    identifier_text_indices.append( domain_index_name )

                # Free/subset args only - an element-parameter arg fixes one slice, it isn't an axis.
                free_subset_arg_count = sum(1 for a in identifier_text_args
                                            if not modeledit_aimmspy2.isScalarElementParameter(aimms_model, a.split('->')[0]))
                chart_index_split = content_lists_expected.get("chart_index_split", False) and free_subset_arg_count == 2

                only_free = 1
                slices = []
                arg_free_pos = 0
                for argpos in range(identifier_text_no_args):
                    arg = identifier_text_args[argpos]
                    domain_index_name = identifier_text_indices[argpos]
                    # A content reference can free/subset-slice an identifier with a different,
                    # range-compatible Index than its own declared one (e.g. a real RSC model
                    # declares "Parameter PeriodMustRun { IndexDomain: (u,fh); }" but WinUI
                    # references "PeriodMustRun( u, h )"). Two DIFFERENT things WebUI needs, both
                    # confirmed against the real rendered page, not just JSON structure:
                    # - A content slice's own "index" key always stays the identifier's own
                    #   DECLARED name ("fh") - WebUI matches a content item's "index" against every
                    #   OTHER content item's "index" for the SAME table to decide how many distinct
                    #   axes to render, so using the reference's own name there instead rendered 3
                    #   columns instead of 2 (w2w0007, startpage, area D).
                    # - A row/column/header PARTITION entry - and the slice's own "value" (for
                    #   "free"/"subset" - trivially identical to "index" for "free") - instead uses
                    #   the reference's own name ("h") - using the declared name there instead
                    #   rendered an extra ROW level instead of a column (a real RSC page,
                    #   "Must Run"). resolve_effective_index_name only overrides this for an arg
                    #   that's itself a real Index (the "subset" case) - an "element-parameter" arg
                    #   (not itself an Index) is unaffected, still the declared name either way.
                    effective_index_name = resolve_effective_index_name(aimms_model, arg, domain_index_name)
                    # The qualified form (giim::/giil:: when synthetic - see
                    # gii_module.qualify_synthetic_index) is what every place below that writes
                    # one of these two names into the returned dict actually needs - unlike the
                    # internal lookups just below (arg comparison, is_synthetic_index itself, the
                    # .DeveloperState pivot arrangement check), which all key off the bare name.
                    qualified_domain_index_name = gii_module.qualify_synthetic_index(gii_dict, component_dict, domain_index_name)
                    qualified_partition_name = gii_module.qualify_synthetic_index(gii_dict, component_dict, effective_index_name)

                    # An index shown as a row/column header falls back to WebUI displaying its
                    # underlying set's name unless webui::IdentifierElementText has an entry for
                    # it - register that fallback text whenever nothing better has been registered
                    # already (add_element_safely is a no-op if this exact key/value pair is
                    # already present). The KEY must match whatever actually ends up in the
                    # row/column/header partition (qualified_partition_name, not
                    # qualified_domain_index_name - see its own comment above) - it's also an
                    # actual member of webui::IdentifierElementText's IndexIdentifiers running
                    # index, so needs the same qualification a synthetic indicator index (see
                    # gii_module.ensure_indicator_index) needs everywhere else (e.g.
                    # "giim::i_indicator_s_abc", not the bare "i_indicator_s_abc" - AIMMS would
                    # otherwise reject it at runtime as "not in the range set of the running index
                    # IndexIdentifiers"; a library's own "giil::x" alone isn't enough either, since
                    # pr_adaptNamesForPresentationInWebUI always lives in the MAIN model - same
                    # qualification as resolve_widget_visibility's not_param_name reference).
                    #
                    # The VALUE, for an ordinary index, is its own bare name (nothing better to
                    # show); but for one of THIS tool's own indicator indices (see
                    # gii_module.ensure_indicator_index/indicator_index_domain_set), showing the
                    # generated "i_indicator_s_u" itself would be meaningless to a WebUI end user
                    # - show the domain Set it actually ranges over ("s_u") instead, per explicit
                    # user request.
                    element_text_value = gii_module.indicator_index_domain_set(gii_dict, component_dict, domain_index_name) or effective_index_name
                    identifier_element_text.add_element_safely( aimms_model, qualified_partition_name, element_text_value )

                    # extract "link index entry to" type of reverse links.
                    # syntax in the contents is a(i->ep)
                    p_revLinkarrow = arg.find('->')
                    if p_revLinkarrow >= 0:
                        store_focus_in[qualified_domain_index_name] = arg[p_revLinkarrow+2:]
                        arg = arg[0:p_revLinkarrow]

                    # Construct the slicing
                    is_scalar_element_parameter = modeledit_aimmspy2.isScalarElementParameter( aimms_model, arg )
                    if is_scalar_element_parameter == 0:
                        if arg == domain_index_name:
                            arg_type = "free"
                        else:
                            arg_type = "subset"
                            only_free = 0
                    else:
                        arg_type = "element-parameter"
                        only_free = 0
                    slicing_arg_dict = {
                        "index" : qualified_domain_index_name,
                        "type"  : arg_type,
                        "value" : qualified_partition_name if arg_type == "free" else arg
                    }
                    slices.append(slicing_arg_dict)

                    # Construct the partition. For a Pivot Table whose real row/column/outer
                    # arrangement was recovered from .DeveloperState (win_pivot_state.py - that
                    # arrangement is set interactively in the WinUI IDE and is never written to
                    # the WinUI XML itself), use it directly; otherwise (not a pivot table, no
                    # .DeveloperState data, or this specific index was never cached there) fall
                    # back to the existing default heuristic below, unchanged. Every entry placed
                    # anywhere below uses qualified_partition_name (the reference's own name, not
                    # the identifier's declared one - see its own comment above), consistently for
                    # every placement branch, not just the .DeveloperState-driven one.
                    #
                    # .DeveloperState records a relation Set's own participating domain sets by
                    # their own name (e.g. "s_u"), never by the synthetic Index this tool mints
                    # for them (e.g. "i_indicator_s_u" - see gii_module.ensure_indicator_index) -
                    # check under that original name too when domain_index_name is one of those.
                    pivot_state_key = gii_module.indicator_index_domain_set(gii_dict, component_dict, domain_index_name) or effective_index_name
                    # .DeveloperState names indices as written inside the library itself, without
                    # the library's own prefix that namespace_qualification added above.
                    own_prefix = component_dict['Prefix'] + "::"
                    if component_dict['Prefix'] != "" and pivot_state_key.startswith(own_prefix):
                        pivot_state_key = pivot_state_key[len(own_prefix):]
                    placed_by_pivot_state = False
                    if pivot_arrangement is not None:
                        if pivot_state_key in pivot_arrangement["row"]:
                            # Several identifiers in the same multi-identifier widget commonly
                            # share a domain index (e.g. MustRunUnit(u) and PeriodMustRun(u,fh)
                            # both taking u) - dedup like every other placement branch does.
                            if not qualified_partition_name in rowheader_list:
                                rowheader_list.append( qualified_partition_name )
                            row_pivot_state_keys[qualified_partition_name] = pivot_state_key
                            placed_by_pivot_state = True
                        elif pivot_state_key in pivot_arrangement["col"]:
                            if not qualified_partition_name in colheader_list:
                                colheader_list.append( qualified_partition_name )
                            col_pivot_state_keys[qualified_partition_name] = pivot_state_key
                            placed_by_pivot_state = True

                    if placed_by_pivot_state:
                        pass
                    elif chart_index_split and not is_scalar_element_parameter:
                        to_x_axis = (arg_free_pos == 0) != content_lists_expected.get("chart_swapped_axes", False)
                        second_axis_list = stacked_list if content_lists_expected.get("chart_second_axis") == "stacked" else grouped_list
                        target_list = header_list if to_x_axis else second_axis_list
                        if not qualified_partition_name in target_list:
                            target_list.append( qualified_partition_name )
                    elif default_first_column == 31:
                        # A genuine WinUI Composite Table/Sparse List (the only types
                        # default_first_column is 31 for) has no column region at all - every
                        # domain index always renders as a row, regardless of any <FirstColumn>
                        # tag (never a deliberate row/column split for these types, unlike a
                        # classic "Table" object, which does support one - see
                        # first_column_explicit below).
                        if not qualified_partition_name in rowheader_list:
                            rowheader_list.append( qualified_partition_name )
                    elif first_column_explicit and first_column < 31:
                        # This identifier's own <FirstColumn> splits its args between row and
                        # column - honor it even with several ExplicitIdentifiers in the same
                        # table (e.g. IndicatorFlowComponent(f,c) alongside MapCompositionTo(f):
                        # each identifier's own FirstColumn still says which of its own args stay
                        # row vs. go column, independent of how many identifiers the table has).
                        # Sibling identifiers commonly share a domain index (e.g. every column of
                        # a table keyed by the same row index) - dedup like the "else" below does.
                        if argpos < first_column:
                            if not qualified_partition_name in rowheader_list:
                                rowheader_list.append( qualified_partition_name )
                        else:
                            if not qualified_partition_name in colheader_list:
                                colheader_list.append( qualified_partition_name )
                    elif ( no_identifiers == 1 ) and ( first_column < 31 ):
                        if first_column >= 0:
                            if argpos < first_column:
                                rowheader_list.append( qualified_partition_name )
                            else:
                                colheader_list.append( qualified_partition_name )
                        else:
                            if content_lists_expected['header'] == 1:
                                header_list.append( qualified_partition_name )
                            else:
                                if identifier_text_no_args==1:
                                    rowheader_list.append( qualified_partition_name )
                                else:
                                    if argpos < identifier_text_no_args-1:
                                        rowheader_list.append( qualified_partition_name )
                                    else:
                                        colheader_list.append( qualified_partition_name )
                    else:
                        # Multiple identifiers, place all args in header or rowheader.
                        if content_lists_expected['header'] == 1:
                            if not qualified_partition_name in header_list:
                                header_list.append( qualified_partition_name )
                        elif content_lists_expected['rowHeader'] == 1:
                            if not qualified_partition_name in rowheader_list:
                                rowheader_list.append( qualified_partition_name )
                    if not is_scalar_element_parameter:
                        arg_free_pos += 1

                # This identifier's own slice (built fresh above, for THIS identifier only) -
                # record it now, before the next ExplicitIdentifier in this widget resets
                # only_free/slices for itself (see all_slices_entries' own declaration above).
                # Nested inside this same "identifier_text != ''" block, not a sibling of it -
                # only_free/slices/identifier_text_name only exist when it ran this iteration.
                if only_free == 0:
                    all_slices_entries.append({
                        "identifier": identifier_text_name,
                        "slice": slices
                    })

            if decimals_entry != {}:
                decimals_dict[identifier_text_name] = decimals_entry
            if visible_entry != {}:
                visible_dict[identifier_text_name] = visible_entry
            if ro_entry != {}:
                readonly_dict[identifier_text_name] = ro_entry

    # Re-sort into .DeveloperState's own display order now that every identifier's own args have
    # been placed (see row_pivot_state_keys/col_pivot_state_keys's own declaration above) - a
    # stable sort, so any entry NOT placed via pivot_arrangement (not currently possible in
    # practice - every placed_by_pivot_state entry is tracked - kept only as a safety net) simply
    # keeps its current relative position, sorted after every tracked entry.
    if row_pivot_state_keys:
        row_order = pivot_arrangement["row"]
        rowheader_list.sort(key=lambda name: row_order.index(row_pivot_state_keys[name]) if name in row_pivot_state_keys else len(row_order))
    if col_pivot_state_keys:
        col_order = pivot_arrangement["col"]
        colheader_list.sort(key=lambda name: col_order.index(col_pivot_state_keys[name]) if name in col_pivot_state_keys else len(col_order))

    def _place_chart_identifier_set() -> None:
        # Curve/Bar Chart: the identifier list goes to grouped - or stacked for a bar chart with
        # <Stacked>true (win_barchart.py's "chart_second_axis") - while the free index stays on the
        # X-axis; <SwappedAxes>true exchanges the two.
        second_axis_list = stacked_list if content_lists_expected.get("chart_second_axis") == "stacked" else grouped_list
        if content_lists_expected.get("chart_swapped_axes", False) and not second_axis_list:
            second_axis_list.extend( header_list )
            header_list[:] = [ "<IDENTIFIER-SET>" ]
        else:
            second_axis_list.append( "<IDENTIFIER-SET>" )

    # Place the identifier list in the appropriate partition list.
    if is_scalar == 0:
        if no_identifiers > 1:
            # A Pivot Table's own explicit-identifier list gets its own row/col placement in the
            # IDE (the "Symbols" pseudo-axis - see win_pivot_state.SYMBOLS_ID_FIRST), independent
            # of where any real domain index sits - honor it here the same way the per-index
            # placement above does, instead of always defaulting <IDENTIFIER-SET> to colHeader.
            #
            # Symbols is the OUTERMOST grouping level on whichever axis it lands on - "which of my
            # several displayed identifiers" is chosen before "which element of the free index
            # within it", not after - so it goes at the FRONT of that axis's own list, not the
            # end: confirmed the hard way (w2w0027, pagefive) against real WinUI, whose actual
            # column order is "<IDENTIFIER-SET>, i", not "i, <IDENTIFIER-SET>" (what appending
            # produced). This only applies when .DeveloperState actually placed Symbols on this
            # axis - the plain colHeader fallback just below (no pivot_arrangement, or it never
            # recorded a Symbols placement) is unaffected, unchanged from before.
            #
            # Not always the front, though: .DeveloperState also records where Symbols nests among
            # that axis's own indices (pivot_arrangement["symbols_pos"]) - e.g. a real 50NGMM table
            # shows "lngexp" outer, Identifier inner on its columns. Insert in front of the first
            # placed entry whose own recorded position is at or after symbols_pos.
            def _symbols_insert_at(header_list_: list, keys_: dict, order_: list) -> int:
                symbols_pos = pivot_arrangement.get("symbols_pos")
                if symbols_pos is None:
                    return 0
                return sum(1 for name in header_list_ if name in keys_ and order_.index(keys_[name]) < symbols_pos)

            if pivot_arrangement is not None and pivot_arrangement.get("symbols") == "row" and content_lists_expected['rowHeader'] == 1:
                rowheader_list.insert( _symbols_insert_at(rowheader_list, row_pivot_state_keys, pivot_arrangement["row"]), "<IDENTIFIER-SET>" )
            elif pivot_arrangement is not None and pivot_arrangement.get("symbols") == "col" and content_lists_expected['colHeader'] == 1:
                colheader_list.insert( _symbols_insert_at(colheader_list, col_pivot_state_keys, pivot_arrangement["col"]), "<IDENTIFIER-SET>" )
            elif content_lists_expected['colHeader'] == 1:
                colheader_list.append( "<IDENTIFIER-SET>" )
            elif content_lists_expected['overlays'] == 1:
                overlay_list.append( "<IDENTIFIER-SET>" )
            elif content_lists_expected['grouped'] == 1:
                _place_chart_identifier_set()
            else:
                print("Warning: multiple identifiers but no header, overlays, or grouped expected?")
        else:
            if content_lists_expected.get("chart_index_split", False) and identifier_text_no_args == 1:
                # A single one-dimensional curve/bar series: same placement as several of them.
                _place_chart_identifier_set()
            elif identifier_text_no_args==1:
                colheader_list.append( "<IDENTIFIER-SET>" )
            else:
                aggregate_list.append( "<IDENTIFIER-SET>" )

    loc_contents_dict: dict[str, Any] = {}
    if not all_slices_entries:
        loc_contents_dict = {
            "contents": contents_list
        }
    else:
        loc_contents_dict = {
            "contents": contents_list,
            "prefix" : "aimms",
            "slices" : all_slices_entries
        }

    # Insert domain spec if any - the same display domain applies to every content item.
    domain_literal_dict = {}
    if domain_identifier != '':
        domain_literal_dict = {
            "identifier": domain_identifier,
            "slice": domain_slices
        }

    return_dict = {
        "contents": {
            "aimms" : loc_contents_dict
        },
        "contents.partition": {
            "rowHeader": rowheader_list,
            "colHeader": colheader_list,
            "header": header_list,
            "aggregated": aggregate_list,
            "stacked": stacked_list,
            "overlays": overlay_list,
            "grouped": grouped_list
        }
    }
    if domain_literal_dict != {}:
        return_dict['contents.displaydomain'] = domain_literal_dict
    if store_focus_in != {}:
        return_dict['store.focus.in'] = store_focus_in

    return_dict['decimals'] = decimals_dict
    return_dict['visible']  = visible_dict
    return_dict['readonly'] = readonly_dict
    if header_title != '':
        return_dict['header_title'] = header_title

    return return_dict

def substitute_reference(imms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, reference: str) -> str:
    """
    substitute_reference : 
        in webui a reference is just a scalar parameter, 
        in winui it can also be an indexed parameter, whereby element parameters are used to point to the relevant element.
    
    :param imms_model: AIMMS model handle used to inspect identifiers and their domains.
    :type imms_model: Model
    :param gii_dict: DescRuntime library dictionary produced during conversion.ription
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: DescrWebUI page dictionary used for context during expression substitution.iption
    :type webui_page_dict: dict
    :param page_name: ame of the page being processed.
    :type page_name: str
    :param reference: scalar reference that may contain element parameters to point to the element of the string parameter
    :type reference: str

    :return: reference that is a scalar parameter.
    :rtype: str
    """