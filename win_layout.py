# Detect a small integer/fractional CSS grid layout from a WinUI page's <Location> rects, for
# use as a WebUI custom Grid layout (layouts/custom_<uuid> - see documentation/layout heuristic.md
# for the schema, confirmed via hand-built reference examples since it isn't publicly documented).
#
# Ported from an exploratory scratch script, validated against 391 real WinUI pages across 3
# production AIMMS apps before being wired into the converter. The clustering/fitting/caption
# logic itself is unchanged from that validation; only the input (already-parsed lxml elements
# instead of re-parsed XML files) and the output (a LayoutPlan consumed by win_object_tools.py)
# are new.

from typing import List, Dict, Tuple, Any, Optional, Set
import lxml.etree as ET

GAP_THRESHOLD = 15          # px: gap below this merges into the same row/col band
MAX_BANDS = 20               # reject the page if more than this many row or col bands
MAX_WEIGHT = 20              # fr weights must fit in 1..MAX_WEIGHT for the clean-integer fit
SPAN_TOLERANCE = 15          # px: an object's far edge must clear a band's start by more than
                             # this to count as genuinely spanning into that band - hand-placed
                             # WinUI coordinates routinely overshoot a boundary by a few px
                             # without that being a deliberate multi-row/col span.
CLEAN_FIT_MAX_ERROR = 0.05   # accept a small-integer fr fit this close before falling back to a
                             # decimal fr value (CSS grid-template accepts arbitrary fr fractions,
                             # so the decimal fallback is always available and always near-exact -
                             # there is no "not representable" case).
CAPTION_MAX_GAP = 30         # px: caption's bottom may sit up to this far above the widget's top
CAPTION_LEFT_TOL = 12        # px: edges must align within this for the above/left-of cases
CAPTION_MAX_WIDTH_RATIO = 1.35  # caption may be at most this much wider/taller than its target
CAPTION_CONTAINMENT = 0.6    # fraction of the text's own area that must lie inside the target,
                             # for the embedded/overlapping case (e.g. a title drawn inside a
                             # Pivot Table's own frame)
CAPTION_MAX_HEIGHT = 40      # px: taller than this reads as multi-line body text, not a caption
BUTTON_GROUP_GAP = 15        # px: vertical gap below this merges two vertically-stacked Buttons
                             # into one shared grid area (see _group_nearby_buttons) - a separate
                             # constant from GAP_THRESHOLD since "buttons stacked in one column"
                             # and "two independent rows of content merging into one band" are
                             # different judgment calls that may need independent tuning.
BUTTON_GROUP_MIN_OVERLAP = 0.5  # a stacked pair's horizontal overlap must be at least this
                                # fraction of the narrower button's width - same column, not
                                # just a coincidental sliver overlap.
IGNORED_TYPES = {"Line", "Rectangle", "Navigation Object"}   # never converted to a widget at all -
                                                              # see win_object.py's type dispatch.
                                                              # A Navigation Object is commonly laid
                                                              # out overlapping other template
                                                              # objects (e.g. a background banner
                                                              # Picture) - since it never becomes a
                                                              # real widget, it must not contest grid
                                                              # space or cause a false overlap
                                                              # rejection, same as Line/Rectangle.


class LayoutPlan:
    """
    Result of a successful compute_page_layout() call: a CSS grid derived from one page's
    PageObjects, plus per-object placement/caption-folding decisions keyed by XML element
    identity. Only valid for the lifetime of the win_page.process_page() call that produced it -
    identity keys are Python id()s of the same in-memory lxml elements the dispatch loop walks.
    """

    def __init__(self, grid_template_columns: str, grid_template_rows: str, grid_template_areas: str,
                 area_names: List[str], slots: Dict[int, Tuple[str, Optional[str]]], absorbed_ids: Set[int],
                 rows: int, cols: int, conditional_siblings: Optional[Dict[int, List[Tuple[ET.Element, str]]]] = None):
        self.grid_template_columns = grid_template_columns
        self.grid_template_rows = grid_template_rows
        self.grid_template_areas = grid_template_areas
        self.area_names = area_names  # every area name, in row-major discovery order (incl. empty cells)
        self._slots = slots
        self._absorbed = absorbed_ids
        self.rows = rows
        self.cols = cols
        self._conditional_siblings = conditional_siblings or {}

    def slot_for(self, element: ET.Element) -> Tuple[Optional[str], Optional[str]]:
        """Return (area, title) for a WinUI PageObject placed by the heuristic, or (None, None)
        if this element wasn't placed (page-level rejection already handled by the None return
        from compute_page_layout(); this covers the smaller per-object exclusion case, e.g. a
        non-Text object overlapping a Button)."""
        return self._slots.get(id(element), (None, None))

    def is_absorbed(self, element: ET.Element) -> bool:
        """True for a Text object folded into another widget's title instead of becoming its
        own widget - must not be dispatched at all."""
        return id(element) in self._absorbed

    def conditional_sibling_exprs(self, element: ET.Element) -> List[str]:
        """The <Hidden> conditions of this element's other mutually-exclusive alternates - the
        other conditionally-hidden widgets merged into this element's own shared grid area (see
        _merge_conditional_overlaps) - for win_object_tools.resolve_widget_visibility() to check
        as a candidate "opposite" visibility parameter. Empty when this element wasn't merged
        with any other conditionally-hidden widget."""
        return [expr for other, expr in self._conditional_siblings.get(id(element), []) if other is not element]


def cluster_1d(values: List[float], threshold: float = GAP_THRESHOLD) -> List[List[float]]:
    """Sort+merge 1-D clustering. Returns list of bands, each a sorted list of the original
    values belonging to that band, in band order."""
    if not values:
        return []
    order = sorted(values)
    bands = [[order[0]]]
    for v in order[1:]:
        if v - bands[-1][-1] <= threshold:
            bands[-1].append(v)
        else:
            bands.append([v])
    return bands


def band_reps(bands: List[List[float]]) -> List[float]:
    """Representative (start) value per band - the min of the band's members."""
    return [min(b) for b in bands]


def assign_span(start_value: float, end_value: float, band_starts: List[float],
                 tolerance: float = SPAN_TOLERANCE) -> Tuple[int, int]:
    """Given an object's [start_value, end_value) extent on one axis, and the sorted list of
    band start-coordinates, return (start_index, span)."""
    start_idx = max(i for i, s in enumerate(band_starts) if s <= start_value + 1e-6)
    end_idx = start_idx
    for i, s in enumerate(band_starts):
        if s + tolerance < end_value:
            end_idx = max(end_idx, i)
    return start_idx, end_idx - start_idx + 1


def round_sig(x: float, sig: int = 3) -> float:
    """Round x to `sig` significant figures. Unlike round(x, N) (fixed decimal places), this
    keeps relative rounding error small and bounded regardless of x's magnitude."""
    if x == 0:
        return 0.0
    from math import floor, log10
    digits = sig - int(floor(log10(abs(x)))) - 1
    return round(x, digits)


def fit_weights(sizes: List[float], has_own_widget: List[bool]) -> Optional[Tuple[List[float], float]]:
    """Turn a list of positive raw sizes into CSS grid-template fr weights.
    Returns (weights, max_relative_error).

    A band with has_own_widget[i] False has no non-spanning object of its own (only other
    objects' spans pass through it) - a legitimate "block with no widget", not content of
    unknown size. It always gets weight 1 and is excluded from the error check, rather than
    guessing at its "size" or letting its absence distort the fit for the bands that do have
    their own content."""
    if not sizes:
        return None

    content_sizes = [s for s, has in zip(sizes, has_own_widget) if has]
    if not content_sizes:
        return [1] * len(sizes), 0.0

    m = min(content_sizes)
    if m <= 0:
        return None
    ratios = [s / m for s in content_sizes]

    # Tier 1: try a clean small-integer fit (search candidate scale factors, keep whichever
    # rounds cleanest - e.g. sizes 147/210 (ratio 1.43) scaled by 7 round to [7, 10] exactly,
    # rather than rounding in place to [1, 1], a 30% error).
    best = None
    max_scale = MAX_WEIGHT / max(ratios)
    steps = 200
    for i in range(1, steps + 1):
        scale = max_scale * i / steps
        weights = [max(1, round(r * scale)) for r in ratios]
        if max(weights) > MAX_WEIGHT:
            continue
        errs = [abs(w - r * scale) / (r * scale) for w, r in zip(weights, ratios)]
        err = max(errs)
        if best is None or err < best[1]:
            best = (weights, err)

    if best is not None and best[1] <= CLEAN_FIT_MAX_ERROR:
        content_weights, err = best
    else:
        # Tier 2: decimal fallback - always available, always near-exact.
        content_weights = [round_sig(r, 3) for r in ratios]
        err = max(abs(w - r) / r for w, r in zip(content_weights, ratios))

    result = []
    ci = 0
    for has in has_own_widget:
        if not has:
            result.append(1)
        else:
            result.append(content_weights[ci])
            ci += 1
    return result, err


def overlap_area(a: dict, b: dict) -> float:
    dx = min(a["right"], b["right"]) - max(a["left"], b["left"])
    dy = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
    return max(0.0, dx) * max(0.0, dy)


def rect_area(a: dict) -> float:
    return max(0.0, a["right"] - a["left"]) * max(0.0, a["bottom"] - a["top"])


def rects_overlap(a: dict, b: dict) -> bool:
    return a["left"] < b["right"] and b["left"] < a["right"] and a["top"] < b["bottom"] and b["top"] < a["bottom"]


def is_caption_match(t: dict, w: dict) -> bool:
    """Does object t (a Text) look like a caption for object w? Three geometric cases: sits
    directly above with matching left edge, sits directly to the left with matching top edge
    (the "label:  value" horizontal form-row convention), or is (mostly) embedded within w at
    any overlap depth (e.g. a title drawn inside a Pivot Table's own frame)."""
    if t["bottom"] - t["top"] > CAPTION_MAX_HEIGHT:
        return False
    gap_above = w["top"] - t["bottom"]
    if -CAPTION_LEFT_TOL <= gap_above <= CAPTION_MAX_GAP and abs(t["left"] - w["left"]) <= CAPTION_LEFT_TOL:
        w_width = w["right"] - w["left"]
        t_width = t["right"] - t["left"]
        if w_width > 0 and t_width <= w_width * CAPTION_MAX_WIDTH_RATIO:
            return True
    gap_left = w["left"] - t["right"]
    if -CAPTION_LEFT_TOL <= gap_left <= CAPTION_MAX_GAP and abs(t["top"] - w["top"]) <= CAPTION_LEFT_TOL:
        w_height = w["bottom"] - w["top"]
        t_height = t["bottom"] - t["top"]
        if w_height > 0 and t_height <= w_height * CAPTION_MAX_WIDTH_RATIO:
            return True
    t_area = rect_area(t)
    if t_area > 0 and overlap_area(t, w) / t_area >= CAPTION_CONTAINMENT:
        return True
    return False


def is_loose_caption_match(t: dict, w: dict) -> bool:
    """A looser fallback for is_caption_match's "above" case: text sitting directly above w with
    substantial horizontal overlap (same style of test as _buttons_stacked), even without
    is_caption_match's precise left-edge alignment (CAPTION_LEFT_TOL) - e.g. a caption whose own
    left margin doesn't happen to match its target's. Only ever tried as a SECOND pass, for a
    widget that is_caption_match's own (stricter) pass left without a title - see
    compute_page_layout - so this never overrides an ordinary caption match, only adds coverage
    for widgets that would otherwise have none."""
    if t["bottom"] - t["top"] > CAPTION_MAX_HEIGHT:
        return False
    gap_above = w["top"] - t["bottom"]
    if not (-CAPTION_LEFT_TOL <= gap_above <= CAPTION_MAX_GAP):
        return False
    h_overlap = min(t["right"], w["right"]) - max(t["left"], w["left"])
    min_width = min(t["right"] - t["left"], w["right"] - w["left"])
    if min_width <= 0 or h_overlap < min_width * BUTTON_GROUP_MIN_OVERLAP:
        return False
    w_width = w["right"] - w["left"]
    t_width = t["right"] - t["left"]
    return w_width > 0 and t_width <= w_width * CAPTION_MAX_WIDTH_RATIO


def _is_overlap_recoverable_as_caption(t: dict, w: dict) -> bool:
    """
    Third and LAST-resort caption check, tried only when t (a Text) and w (some other object)
    have already collided in the same grid cell - never as part of the ordinary captioning pass
    every Text on the page gets first (is_caption_match, then is_loose_caption_match), both of
    which already had their chance against every candidate target and missed this specific pair.

    That collision is often a false positive from row/column BANDING (GAP_THRESHOLD-based
    clustering merges two objects whose raw pixel positions barely overlap, or don't overlap at
    all, into the same cell - e.g. a caption sitting directly above its target, touching with
    zero gap but with a left edge far enough off that is_caption_match's own CAPTION_LEFT_TOL
    already rejected it), not a real "these two are stacked on top of each other" design.

    Recovering by treating t as w's title - instead of discarding this page's entire hand-built
    layout for the generic fallback - is worth it even when the guess is imperfect: the only
    condition checked is that t isn't already SUBSTANTIALLY embedded within w (that shape is
    is_caption_match's own "embedded title" case, tried already, further up the very same
    collision) - i.e. a meaningful part of t is genuinely visible outside w, the same test a
    human skimming the page would use to tell "this text labels that widget" from "these two
    objects are unrelated and truly stacked on each other".

    :param t: The Text object of the colliding pair.
    :type t: dict
    :param w: The other, non-Text object of the colliding pair.
    :type w: dict
    :return: True when t is plausibly w's caption/title despite failing both earlier passes.
    :rtype: bool
    """
    if t["bottom"] - t["top"] > CAPTION_MAX_HEIGHT:
        return False
    t_area = rect_area(t)
    if t_area <= 0:
        return False
    return (overlap_area(t, w) / t_area) < CAPTION_CONTAINMENT


def _buttons_stacked(a: dict, b: dict, gap: float = BUTTON_GROUP_GAP) -> bool:
    """Do a and b look like two Buttons stacked in the same vertical column - substantial
    horizontal overlap (same column, not a coincidental sliver), and touching or within `gap` of
    each other vertically (in either order; already-overlapping counts too)?"""
    h_overlap = min(a["right"], b["right"]) - max(a["left"], b["left"])
    min_width = min(a["right"] - a["left"], b["right"] - b["left"])
    if min_width <= 0 or h_overlap < min_width * BUTTON_GROUP_MIN_OVERLAP:
        return False
    v_gap = max(a["top"] - b["bottom"], b["top"] - a["bottom"])
    return v_gap <= gap


def _group_nearby_buttons(grid_pool: List[dict]) -> List[dict]:
    """Merge chains of 2+ Button objects stacked in a single column (per _buttons_stacked) into
    one combined pool entry - bounding box = the union of the members' rects, `group_elements`
    carrying every member's real xml element - so they occupy one shared grid area instead of
    each getting their own row. A button with no vertically-stacked neighbor (including one only
    sitting beside it in a row) is left untouched; buttons in a row are explicitly out of scope."""
    buttons = [o for o in grid_pool if o["type"] == "Button"]
    if len(buttons) < 2:
        return grid_pool

    # Union-find over stacked-pairs, so a whole column of N buttons chains together correctly,
    # not just adjacent pairs.
    parent = list(range(len(buttons)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(len(buttons)):
        for j in range(i + 1, len(buttons)):
            if _buttons_stacked(buttons[i], buttons[j]):
                union(i, j)

    clusters: Dict[int, List[dict]] = {}
    for i, b in enumerate(buttons):
        clusters.setdefault(find(i), []).append(b)

    button_ids = {id(b["element"]) for b in buttons}
    result = [o for o in grid_pool if id(o["element"]) not in button_ids]

    for members in clusters.values():
        if len(members) == 1:
            result.append(members[0])
            continue
        result.append({
            "type": "Button",
            "top": min(m["top"] for m in members),
            "left": min(m["left"] for m in members),
            "bottom": max(m["bottom"] for m in members),
            "right": max(m["right"] for m in members),
            "text": "",
            "element": members[0]["element"],
            # A member may itself already carry a group (unlikely here, but kept consistent with
            # _merge_conditional_overlaps' own flattening) - flatten rather than collapsing it
            # back down to just its representative element.
            "group_elements": [e for m in members for e in m.get("group_elements", [m["element"]])],
            "hidden_kind": None,
        })

    return result


def _merge_pool_members(members: List[dict]) -> dict:
    """
    Combine 2+ grid_pool entries (raw _parse_objects results, or themselves already-merged
    entries - e.g. a _group_nearby_buttons button column) into one shared-area entry: bounding
    box = the union of the members' rects, `group_elements` carrying every member's own real xml
    element(s) so each one still resolves its own slot/title/visibility once placed (see the
    "Assign area names" loop in compute_page_layout, and LayoutPlan.conditional_sibling_exprs()).
    Shared by _merge_conditional_overlaps (mutually exclusive conditionally-hidden alternates)
    and compute_page_layout's own collision-retry loop (two widgets that genuinely, unconditionally
    overlap on the page).

    :param members: 2 or more grid_pool entries to combine.
    :type members: List[dict]
    :return: One merged grid_pool entry.
    :rtype: dict
    """
    # A Button representative keeps the merged entry eligible for the (later) button-stacking
    # pass; otherwise prefer any non-Text member (a real widget) over Text.
    rep = next((m for m in members if m["type"] == "Button"), None) \
        or next((m for m in members if m["type"] != "Text"), members[0])

    return {
        "type": rep["type"],
        "top": min(m["top"] for m in members),
        "left": min(m["left"] for m in members),
        "bottom": max(m["bottom"] for m in members),
        "right": max(m["right"] for m in members),
        "text": rep.get("text", ""),
        "element": rep["element"],
        "group_elements": [e for m in members for e in m.get("group_elements", [m["element"]])],
        "hidden_kind": None,
        "hidden_expr": None,
        # Every conditionally-hidden member's own (element, hidden_expr) - carried through so
        # compute_page_layout can tell each one which of its mutually-exclusive alternates
        # (if any) is a candidate "opposite" visibility parameter - see
        # LayoutPlan.conditional_sibling_exprs() and win_object_tools.resolve_widget_visibility().
        "conditional_hidden_members": [(m["element"], m["hidden_expr"]) for m in members if m.get("hidden_kind") == "conditional"],
    }


def _merge_conditional_overlaps(grid_pool: List[dict]) -> List[dict]:
    """Merge objects that geometrically overlap where at least one is conditionally hidden into
    one shared grid_pool entry - same union-find/group_elements mechanism as
    _group_nearby_buttons, generalized from "stacked Buttons" to "any overlapping objects
    involving a conditional alternate". Handles WinUI's common pattern of two or more mutually
    exclusive alternates (e.g. an absolute-vs-relative error table, each hidden on the other's
    condition) occupying the identical rect: rather than each contesting its own grid cell -
    tripping compute_page_layout's overlap rejection - they share one area, each still
    dispatching as its own widget (keeping whatever caption it already absorbed)."""
    n = len(grid_pool)
    if n < 2:
        return grid_pool

    parent = list(range(n))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj:
            parent[ri] = rj

    for i in range(n):
        for j in range(i + 1, n):
            a, b = grid_pool[i], grid_pool[j]
            if (a["hidden_kind"] == "conditional" or b["hidden_kind"] == "conditional") and rects_overlap(a, b):
                union(i, j)

    clusters: Dict[int, List[dict]] = {}
    for i, o in enumerate(grid_pool):
        clusters.setdefault(find(i), []).append(o)

    result = []
    for members in clusters.values():
        if len(members) == 1:
            result.append(members[0])
            continue
        result.append(_merge_pool_members(members))

    return result


def _hidden_kind(pobj: ET.Element) -> Tuple[Optional[str], Optional[str]]:
    """Classify a PageObject's <Hidden> element, per the same literal-vs-expression convention
    used for column-level Hidden in win_object_tools.py: '1'/'"Yes"' is unconditionally hidden,
    '0'/'"No"' is unconditionally not hidden (None), anything else is a conditional expression
    (typically a boolean identifier toggled at runtime, e.g. two mutually exclusive alternates -
    an absolute-vs-relative error table - occupying the identical rect).

    :param pobj: A WinUI PageObject element.
    :type pobj: ET.Element
    :return: (kind, expr) - kind is "unconditional", "conditional", or None (not hidden); expr
        is the raw condition text for "conditional", else None.
    :rtype: Tuple[Optional[str], Optional[str]]
    """
    hid_el = pobj.find('Hidden')
    if hid_el is None or not isinstance(hid_el.text, str):
        return None, None
    hid_txt = hid_el.text.strip()
    if hid_txt in ('1', '"Yes"'):
        return "unconditional", None
    if hid_txt in ('0', '"No"') or not hid_txt:
        return None, None
    return "conditional", hid_txt


def is_empty_text_object(pobj: ET.Element) -> bool:
    """
    True for a WinUI Text PageObject with no actual text content - an empty/self-closing
    <StaticText/> (parses as text is None) or one containing only whitespace, and no
    <StringParameter> with real content either. Such an object renders nothing in WinUI and has
    nothing to display in WebUI, so it's treated as if it didn't exist at all: win_text.
    winpage_text skips creating a widget for it, and _parse_objects below excludes it from the
    layout heuristic entirely (same treatment as IGNORED_TYPES) so it can never contest grid
    space or need recovering as another object's caption (see _is_overlap_recoverable_as_caption).

    :param pobj: A WinUI PageObject element.
    :type pobj: ET.Element
    :return: True if this is a Text object with no meaningful text.
    :rtype: bool
    """
    if pobj.get('Type') != 'Text':
        return False
    for child in pobj:
        if child.tag in ('StaticText', 'StringParameter') and child.text and child.text.strip():
            return False
    # <SourceType>File</SourceType>: the text comes from the file named in <FileName>.
    file_name = pobj.findtext('FileName')
    if pobj.findtext('SourceType') == 'File' and file_name and file_name.strip() not in ('', '""'):
        return False
    return True


def is_empty_picture_object(pobj: ET.Element) -> bool:
    """
    True for a WinUI Picture PageObject with no actual image reference - a missing, or
    empty/self-closing/blank, <FileName>. Same "treat as if it didn't exist" rationale as
    is_empty_text_object: win_picture.winpage_picture skips creating a widget for it, and
    _parse_objects below excludes it from the layout heuristic entirely.

    :param pobj: A WinUI PageObject element.
    :type pobj: ET.Element
    :return: True if this is a Picture object with no meaningful image reference.
    :rtype: bool
    """
    if pobj.get('Type') != 'Picture':
        return False
    filename_el = pobj.find('FileName')
    if filename_el is None or not filename_el.text:
        return True
    text = filename_el.text.strip()
    if len(text) >= 2 and text[0] == '"' and text[-1] == '"':
        text = text[1:-1]
    return text == ''


DATA_OBJECT_EMPTY_CHECK_TYPES = {"Scalar", "Table", "Curve", "Bar Chart"}  # WinUI Types this
                                                                            # module's caller
                                                                            # dispatch functions
                                                                            # (win_scalar,
                                                                            # win_classic_table,
                                                                            # win_linechart,
                                                                            # win_barchart) check
                                                                            # is_empty_data_object
                                                                            # for - see there.


def is_empty_data_object(pobj: ET.Element) -> bool:
    """
    True for a WinUI Scalar/Table/Curve/Bar Chart PageObject with no real content - every
    <ExplicitIdentifier>/<Explicit_Identifier> it has (including zero of them) carries no actual
    identifier or expression reference in its own <Identifier> text.

    This is a step beyond win_object_tools.determine_no_identifiers' own child-tag scan, which
    only counts ExplicitIdentifier ELEMENTS: a widget placed in the WinUI IDE but never actually
    filled in - whose ExplicitIdentifier stub has no <Identifier> text, or an empty '""' literal,
    at all - still counts there as "having an identifier" and produces a widget with empty
    contents (see win_object_tools.investigate_contents' own "identifier_text != '' and
    identifier_text != '\"\"'" guards). Same "treat as if it didn't exist" rationale as
    is_empty_text_object/is_empty_picture_object: win_scalar.winpage_scalar, win_classic_table.
    winpage_classic_table, win_linechart.winpage_linechart, and win_barchart.winpage_barchart all
    skip creating a widget for it, and _parse_objects below excludes it from the layout heuristic
    entirely.

    :param pobj: A WinUI PageObject element.
    :type pobj: ET.Element
    :return: True if this is a Scalar/Table/Curve/Bar Chart with no meaningful identifier or
        expression content.
    :rtype: bool
    """
    if pobj.get('Type') not in DATA_OBJECT_EMPTY_CHECK_TYPES:
        return False
    for child in pobj:
        if child.tag not in ('ExplicitIdentifier', 'Explicit_Identifier'):
            continue
        identifier_el = child.find('Identifier')
        if identifier_el is None or not identifier_el.text:
            continue
        identifier_text = identifier_el.text.strip()
        if identifier_text and identifier_text != '""':
            return False
    return True


def is_unconditionally_hidden(pobj: ET.Element) -> bool:
    """True for a PageObject whose <Hidden> is a literal always-true (design-time-disabled
    content) - it must never occupy a grid cell, and always resolves to the "Unassigned
    widgets" WebUI bucket regardless of the rest of the page's layout - see
    win_object_tools.compute_layout_slot()."""
    kind, _ = _hidden_kind(pobj)
    return kind == "unconditional"


def conditional_visibility_expr(pobj: ET.Element) -> Optional[str]:
    """The raw AIMMS boolean expression driving a PageObject's <Hidden> visibility, or None if
    it isn't conditionally hidden. Independent of grid placement - a widget keeps its own
    visibility condition whether or not the layout heuristic accepted the page (and whether or
    not it ended up merged into a shared grid block via _merge_conditional_overlaps) - see
    win_object_tools.compute_layout_slot(), which wires this into each widget's
    "widget.visible" WebUI binding."""
    kind, expr = _hidden_kind(pobj)
    return expr if kind == "conditional" else None


def _parse_objects(page_objects: List[ET.Element], ignore_buttons: bool = False) -> List[dict]:
    """Extract rect/type/text info from a page's PageObject elements, each result carrying a
    reference back to its source xml element (used as the identity key elsewhere). Skips
    ignored types (Line/Rectangle - never converted to a widget at all), any object with no
    <Location> (handled unconditionally elsewhere, in win_object_tools.compute_layout_slot -
    never part of the grid), any unconditionally-hidden object (same "Unassigned widgets"
    treatment as no-Location, via is_unconditionally_hidden() - see compute_layout_slot()), and
    any empty Text/Picture object (see is_empty_text_object/is_empty_picture_object - never
    converted to a widget either, so must not contest grid space), and any empty Scalar/Table/
    Curve/Bar Chart object (see is_empty_data_object, same rationale).

    :param ignore_buttons: Also skip every Button, the same as an IGNORED_TYPES member - used
        for a WinUI Data Page, whose own Close/Undo/navigation buttons (see win_page.process_page)
        have no WebUI equivalent and must not reserve grid space either.
    :type ignore_buttons: bool
    """
    objects = []
    for pobj in page_objects:
        if pobj.tag != 'PageObject':
            continue
        otype = pobj.get('Type', '?')
        if otype in IGNORED_TYPES or (ignore_buttons and otype == 'Button'):
            continue
        if is_empty_text_object(pobj) or is_empty_picture_object(pobj) or is_empty_data_object(pobj):
            continue
        loc = pobj.find('Location')
        if loc is None:
            continue
        hidden_kind, hidden_expr = _hidden_kind(pobj)
        if hidden_kind == "unconditional":
            continue
        top = float(loc.get('top'))
        left = float(loc.get('left'))
        bottom = float(loc.get('bottom'))
        right = float(loc.get('right'))
        text_el = pobj.find('StaticText')
        text = text_el.text.strip() if text_el is not None and text_el.text else ""
        objects.append({"type": otype, "top": top, "left": left, "bottom": bottom, "right": right,
                         "text": text, "element": pobj, "hidden_kind": hidden_kind, "hidden_expr": hidden_expr})
    return objects


def _area_name(index: int) -> str:
    """Spreadsheet-column-style area name: area-a, area-b, ..., area-z, area-aa, ..."""
    letters = ""
    n = index + 1
    while n > 0:
        n, rem = divmod(n - 1, 26)
        letters = chr(ord('a') + rem) + letters
    return f"area-{letters}"


def _format_fr(w) -> str:
    if float(w).is_integer():
        return f"{int(w)}fr"
    return f"{w}fr"


def page_has_layoutable_objects(page_objects: List[ET.Element], ignore_buttons: bool = False) -> bool:
    """
    True when compute_page_layout has anything at all to work with for this page.

    False for a page with no PageObjects at all, or whose only PageObjects are always-ignored
    decoration/navigation (IGNORED_TYPES - e.g. a page that's just a Navigation Object tree) or
    (when ignore_buttons) Data Page chrome buttons - lets a caller tell compute_page_layout's
    "genuinely couldn't fit a grid to real content" None apart from its "there was nothing to lay
    out in the first place" None, which needs no manual review at all (see
    win_page.process_page's own layout-fallback logging).

    :param page_objects: Same as compute_page_layout's own parameter.
    :type page_objects: List[ET.Element]
    :param ignore_buttons: Same as compute_page_layout's own parameter.
    :type ignore_buttons: bool
    :return: True when there's at least one real, layoutable object.
    :rtype: bool
    """
    return bool(_parse_objects(page_objects, ignore_buttons))


def compute_page_layout(page_objects: List[ET.Element], ignore_buttons: bool = False) -> Optional[LayoutPlan]:
    """
    Try to detect a small integer/fractional CSS grid layout from a page's WinUI PageObjects.

    :param page_objects: The page's own top-level children plus any inherited template's -
        exactly the combined set win_page.process_page's two dispatch loops walk, in the same
        order, gathered before either loop dispatches (so element identity stays valid for a
        LayoutPlan's id()-keyed lookups across the whole process_page() call).
    :type page_objects: List[ET.Element]
    :param ignore_buttons: Passed through to _parse_objects - True for a WinUI Data Page, whose
        own Close/Undo/navigation buttons are dropped instead of converted (see
        win_object.winpage_object) and so must not shape the grid either.
    :type ignore_buttons: bool
    :return: A LayoutPlan if the page fits the heuristic's expectations, else None - callers must
        treat None as "fall back to today's type-based default placement, unchanged".
    :rtype: Optional[LayoutPlan]
    """

    objects = _parse_objects(page_objects, ignore_buttons)
    if not objects:
        return None

    buttons = [o for o in objects if o["type"] == "Button"]

    # Text overlapping a Button folds into that Button's title - looser than is_caption_match's
    # alignment rules (any bbox overlap is enough), since such text is essentially always the
    # button's own decorative label rather than an independently laid-out object.
    absorbed_captions: Dict[int, List[str]] = {}
    absorbed_ids: Set[int] = set()
    remaining = []
    for o in objects:
        if o["type"] == "Text" and buttons and any(rects_overlap(o, b) for b in buttons):
            hit = next(b for b in buttons if rects_overlap(o, b))
            absorbed_captions.setdefault(id(hit["element"]), []).append(o["text"] or "Text")
            absorbed_ids.add(id(o["element"]))
            continue
        remaining.append(o)

    # Any other (non-Button) object overlapping a Button is excluded from the grid pool - not
    # absorbed, just placed via the old per-type default area for that one widget - to avoid a
    # false grid-overlap rejection from what's usually decorative overlap around the button.
    grid_pool = []
    for o in remaining:
        if o["type"] != "Button" and buttons and any(rects_overlap(o, b) for b in buttons):
            continue
        grid_pool.append(o)

    # Caption folding: Text sitting above/left-of/embedded-within a non-Text object in the
    # surviving pool. Restricted to grid_pool (not the original objects list) so a caption's
    # target is always something that will actually receive a slot.
    texts = [o for o in grid_pool if o["type"] == "Text"]
    targets = [o for o in grid_pool if o["type"] != "Text"]
    for t in texts:
        matches = [w for w in targets if is_caption_match(t, w)]
        if not matches:
            continue
        # Prefer a target hidden on the exact same condition as this caption (the common
        # "matched header+content pair" case - e.g. an "Absolute ..." header captioning the
        # absolute-error table, not the geometrically-identical relative-error table hidden on
        # the complementary condition) before falling back to the smallest-area tie-break.
        def caption_key(w, _t=t):
            same_condition = (_t["hidden_kind"] == "conditional" and w["hidden_kind"] == "conditional"
                               and _t["hidden_expr"] == w["hidden_expr"])
            return (0 if same_condition else 1, rect_area(w))
        best = min(matches, key=caption_key)
        absorbed_captions.setdefault(id(best["element"]), []).append(t["text"] or "Text")
        absorbed_ids.add(id(t["element"]))

    # Second, looser pass: a widget the strict pass above left with no caption at all gets one
    # more chance, against a Text that strict pass also left unmatched - see is_loose_caption_match.
    # Never runs for a widget/text already claimed above, so an ordinary caption match always wins.
    for t in texts:
        if id(t["element"]) in absorbed_ids:
            continue
        unclaimed_targets = [w for w in targets if id(w["element"]) not in absorbed_captions]
        matches = [w for w in unclaimed_targets if is_loose_caption_match(t, w)]
        if not matches:
            continue
        best = min(matches, key=rect_area)
        absorbed_captions.setdefault(id(best["element"]), []).append(t["text"] or "Text")
        absorbed_ids.add(id(t["element"]))

    pool_before_grouping = [o for o in grid_pool if id(o["element"]) not in absorbed_ids]

    if not pool_before_grouping:
        return None

    # A grid-cell collision is sometimes a false positive from row/column BANDING (GAP_THRESHOLD-
    # based clustering), not a real pixel overlap between the two objects themselves - e.g. a
    # caption sitting directly above its target, touching (zero gap) but with its own left edge
    # far enough off that is_caption_match's/is_loose_caption_match's stricter tolerances already
    # missed it, then banded into the SAME row as its target anyway because some other object's
    # position bridges the two. Recovering by absorbing the Text as the OTHER object's title -
    # instead of discarding this page's ENTIRE hand-built layout for the generic fallback - is
    # worth it even when imperfect; see _is_overlap_recoverable_as_caption.
    #
    # When that doesn't apply either - two real widgets that either genuinely overlap in raw pixel
    # space (e.g. two Curves plotted on the identical rect) or are merely close enough to have
    # banded into the same cell (e.g. two objects that touch edge-to-edge) - merge them into one
    # shared grid area (their combined bounding box) instead of discarding the whole page's
    # hand-built layout: WebUI renders several widgets sharing one area next to each other, which
    # is a fair rendering of either case - same mechanism as _merge_conditional_overlaps, just
    # triggered by a collision instead of a shared <Hidden> condition.
    #
    # Bounded retry: each successful recovery strictly shrinks the pool by at least one entry (the
    # caption case removes one; the bounding-box merge replaces two with one), so this always
    # terminates - the cap is just a safety net against a surprising future edge case.
    for _ in range(len(pool_before_grouping)):
        # A column of 2+ Buttons stacked on top of each other shares one grid area rather than
        # each fragmenting the grid with its own row - see _group_nearby_buttons. Redone from
        # pool_before_grouping every retry (not incrementally on the previous grid_pool), since
        # it and _merge_conditional_overlaps below aren't safe to re-run on their own already-
        # grouped/merged output.
        grid_pool = _group_nearby_buttons(pool_before_grouping)

        # Mutually exclusive conditionally-hidden alternates (e.g. an absolute-vs-relative error
        # table, each hidden on the other's condition) collapse into one shared grid area rather
        # than tripping the overlap rejection below - see _merge_conditional_overlaps.
        grid_pool = _merge_conditional_overlaps(grid_pool)

        tops = [o["top"] for o in grid_pool]
        lefts = [o["left"] for o in grid_pool]
        row_bands = cluster_1d(tops)
        col_bands = cluster_1d(lefts)
        if len(row_bands) > MAX_BANDS or len(col_bands) > MAX_BANDS:
            return None
        row_starts = band_reps(row_bands)
        col_starts = band_reps(col_bands)

        for o in grid_pool:
            o["row"], o["rowspan"] = assign_span(o["top"], o["bottom"], row_starts)
            o["col"], o["colspan"] = assign_span(o["left"], o["right"], col_starts)

        rows, cols = len(row_bands), len(col_bands)
        grid: List[List[Optional[dict]]] = [[None for _ in range(cols)] for _ in range(rows)]
        collision: Optional[Tuple[dict, dict]] = None
        for o in grid_pool:
            for r in range(o["row"], o["row"] + o["rowspan"]):
                for c in range(o["col"], o["col"] + o["colspan"]):
                    if grid[r][c] is not None:
                        collision = (grid[r][c], o)
                        break
                    grid[r][c] = o
                if collision:
                    break
            if collision:
                break

        if collision is None:
            break

        first, second = collision
        text, target = (first, second) if first["type"] == "Text" else (second, first)
        if text["type"] == "Text" and target["type"] != "Text" and _is_overlap_recoverable_as_caption(text, target):
            absorbed_captions.setdefault(id(target["element"]), []).append(text["text"] or "Text")
            pool_before_grouping = [o for o in pool_before_grouping if id(o["element"]) != id(text["element"])]
            continue

        pool_before_grouping = [o for o in pool_before_grouping
                                 if id(o["element"]) not in (id(first["element"]), id(second["element"]))]
        pool_before_grouping.append(_merge_pool_members([first, second]))
        continue
    else:
        # The bounded retry above never broke out via `break` (collision-free) - practically
        # unreachable (see the loop's own comment), but fail safe rather than silently using a
        # possibly-still-colliding grid.
        return None

    def rep_sizes(axis_len, band_starts, key_start, key_span, key_lo, key_hi):
        sizes, has_own = [], []
        for i in range(axis_len):
            non_spanning = [o for o in grid_pool if o[key_start] == i and o[key_span] == 1]
            if non_spanning:
                sizes.append(max(o[key_hi] - o[key_lo] for o in non_spanning))
            else:
                # Only other objects' spans pass through this band: size it by its real extent (up
                # to the next band's start, or for the last band the furthest end of an object
                # covering it), not a flat 1fr - otherwise a wide spanning widget like 50NGMM's
                # "LNG Exports" price table gets squeezed into a sliver next to a narrower neighbour.
                if i + 1 < axis_len:
                    sizes.append(band_starts[i + 1] - band_starts[i])
                else:
                    covering = [o for o in grid_pool if o[key_start] <= i < o[key_start] + o[key_span]]
                    sizes.append(max(o[key_hi] for o in covering) - band_starts[i])
            has_own.append(True)
        return sizes, has_own

    row_sizes, row_has = rep_sizes(rows, row_starts, "row", "rowspan", "top", "bottom")
    col_sizes, col_has = rep_sizes(cols, col_starts, "col", "colspan", "left", "right")

    row_fit = fit_weights(row_sizes, row_has)
    col_fit = fit_weights(col_sizes, col_has)
    if row_fit is None or col_fit is None:
        return None
    row_weights, _ = row_fit
    col_weights, _ = col_fit

    # Assign area names in row-major scan order, including named-but-empty leftover cells -
    # matches the convention observed in the real hand-built reference example (an unused cell
    # gets its own named WidgetArea, not CSS's "." null placeholder).
    area_names: List[str] = []
    slots: Dict[int, Tuple[str, Optional[str]]] = {}
    element_area: Dict[int, str] = {}
    conditional_siblings: Dict[int, List[Tuple[ET.Element, str]]] = {}
    area_rows: List[List[str]] = []
    for r in range(rows):
        row_names = []
        for c in range(cols):
            o = grid[r][c]
            if o is not None:
                key = id(o["element"])
                if key not in element_area:
                    name = _area_name(len(area_names))
                    area_names.append(name)
                    # A merged button-column entry (see _group_nearby_buttons) shares this one
                    # area name across every member, but each member keeps its own caption/title
                    # (folded per-button before grouping ever ran) rather than the group sharing
                    # a single title.
                    for elem in o.get("group_elements", [o["element"]]):
                        element_area[id(elem)] = name
                        elem_captions = absorbed_captions.get(id(elem))
                        elem_title = " ".join(elem_captions) if elem_captions else None
                        slots[id(elem)] = (name, elem_title)
                    # Every mutually-exclusive alternate merged into this same area (see
                    # _merge_conditional_overlaps) is a candidate "opposite" visibility parameter
                    # for every other one - see LayoutPlan.conditional_sibling_exprs().
                    cond_members = o.get("conditional_hidden_members", [])
                    for elem, _expr in cond_members:
                        conditional_siblings[id(elem)] = cond_members
                row_names.append(element_area[key])
            else:
                name = _area_name(len(area_names))
                area_names.append(name)
                row_names.append(name)
        area_rows.append(row_names)

    grid_template_areas = " ".join('"' + " ".join(row) + '"' for row in area_rows)
    grid_template_columns = " ".join(_format_fr(w) for w in col_weights)
    grid_template_rows = " ".join(_format_fr(w) for w in row_weights)

    return LayoutPlan(grid_template_columns, grid_template_rows, grid_template_areas,
                       area_names, slots, absorbed_ids, rows, cols, conditional_siblings)
