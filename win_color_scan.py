"""Discovers project-specific colors beyond the 147 standard w3c/CSS names (see win_color.py):
literal RGB values and named colors used for WinUI widget styling (any XML element whose tag
contains "Color" - BackgroundColor, TextColor, InputColor, Background_Color inside a table's
Row_Area/Headers/Grid_Focus_Indicator, etc.) and every entry in a component's own
Settings/UserColors.xml. Feeds gii_module.ensure_all_colors_values()'s merged giim::s_AllColors
set and giim::p_Red/p_Green/p_Blue(i_color) parameters.

A color found via a literal RGB value that isn't otherwise named (an RGB="#rrggbb" attribute, an
element text of "RGB<r,g,b>", or WinUI's other literal element-text form "RGB rrggbb") is named
"R<red>_G<green>_B<blue>". A quoted color name (e.g. "default selection") or a nested
<UserColor GUID="..">Name</UserColor> reference names a color that must come from
scan_user_colors() instead - resolving those isn't this module's job, see win_object_tools.py's
merge of the two. Names are kept exactly as WinUI (or AIMMS's own built-in AllColors system set -
see gii_module.ensure_all_colors_values) spells them, spaces and all: an existing identifier
already ranged over AllColors can have a Definition that quotes a multi-word built-in member
(e.g. 'light grey') verbatim, and repointing its Range to s_AllColors (see
win_object_tools.investigate_contents) without also rewriting that pre-existing formula would
break if the name didn't match exactly. CSS-safety for names with spaces is handled separately,
purely on the CSS-generation side - see gii_module's p_ColorSlug parameter and
win_color.css_class_slug.

rgb_from_literal_text() and rgb_name() are also used directly by win_object_tools.py's existing
Colors/Color data-coloring handling: a table/chart's color source can itself be one of these
literal RGB forms instead of an AllColors-element identifier reference, and must be turned into
a quoted reference to the same synthesized element name this module registers it under (e.g.
formatString("color-%e", 'R0_G128_B0')) rather than embedding the raw WinUI literal text, which
isn't valid AIMMS syntax on its own.
"""

import pathlib
import re
from typing import Dict, Tuple

import lxml.etree as ET

import win_color

_RGB_HEX_ATTR_RE = re.compile(r"^#?([0-9a-fA-F]{6})$")
_RGB_ANGLE_RE = re.compile(r"^RGB\s*<\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*>$", re.IGNORECASE)
_RGB_HEXWORD_RE = re.compile(r"^RGB\s+([0-9a-fA-F]{6})$", re.IGNORECASE)

# WinUI's other reference form for a project-defined Settings/UserColors.xml entry: instead of
# the nested "<UserColor GUID="..">Name</UserColor>" child element, a Color/Background_Color/
# Text_Color element's own text is sometimes just "<GUID> <Name>" flattened together (both forms
# were seen referencing the exact same UserColors.xml entry in one real project). The GUID itself
# is redundant here - Name alone is what must end up quoted as the AllColors element reference,
# same as any other named color - so it's simply discarded once recognized.
_USER_COLOR_GUID_NAME_RE = re.compile(
    r"^[0-9A-Fa-f]{8}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{4}-[0-9A-Fa-f]{12}\s+(.+)$"
)

# A literal RGB finding that happens to exactly match one of the 147 known w3c colors (e.g. a
# widget's default "RGB="#ffffff" background, which is really just white) adds nothing new -
# skip synthesizing a redundant "R255_G255_B255" alongside the "white" that's already always
# included. Without this, an incidental default color on practically every page would count as
# "a project-specific color was found" and trigger the whole feature on every project.
_KNOWN_W3C_RGB = set(win_color.COLOR_RGB.values())

# Reverse lookup for color_name_for_rgb(). A handful of w3c RGB values have more than one name
# (gray/grey, cyan/aqua, ...) - whichever name wins here is arbitrary but deterministic, and
# either is equally valid (both are real s_AllColors members for that RGB).
_W3C_NAME_BY_RGB = {rgb: name for name, rgb in win_color.COLOR_RGB.items()}


def rgb_name(r: int, g: int, b: int) -> str:
    """Synthesizes a name for a color that isn't otherwise named."""
    return f"R{r}_G{g}_B{b}"


def color_name_for_rgb(rgb: Tuple[int, int, int]) -> str:
    """Returns the name `rgb` is actually registered under in s_AllColors: an existing w3c name
    if it matches one exactly, otherwise the synthesized "R<r>_G<g>_B<b>" name. Use this (not the
    unconditional rgb_name()) wherever a literal RGB value must resolve to a name guaranteed to be
    an s_AllColors member - scan_page_colors() suppresses the synthesized name in favor of the
    w3c one when they'd be redundant, so a caller that always used rgb_name() could end up
    referencing a name that was never actually added to the set."""
    return _W3C_NAME_BY_RGB.get(rgb) or rgb_name(*rgb)


def _rgb_from_hex(hex_digits: str) -> Tuple[int, int, int]:
    return (int(hex_digits[0:2], 16), int(hex_digits[2:4], 16), int(hex_digits[4:6], 16))


def rgb_from_literal_text(text: str):
    """Parses a color element's literal text - either "RGB<r,g,b>" or WinUI's other literal
    form "RGB rrggbb" - into an (r, g, b) tuple, or None if `text` isn't a literal RGB value at
    all (a quoted color name, or an AIMMS identifier/expression reference)."""
    m = _RGB_ANGLE_RE.match(text)
    if m:
        return tuple(int(x) for x in m.groups())
    m = _RGB_HEXWORD_RE.match(text)
    if m:
        return _rgb_from_hex(m.group(1))
    return None


def user_color_name_from_literal_text(text: str):
    """Parses a color element's literal text in WinUI's flattened "<GUID> <Name>" UserColors.xml
    reference form (see _USER_COLOR_GUID_NAME_RE) into just `Name`, or None if `text` isn't that
    form at all (a literal RGB value, a bare quoted color name, or an AIMMS identifier/expression
    reference)."""
    m = _USER_COLOR_GUID_NAME_RE.match(text)
    return m.group(1).strip() if m else None


def scan_user_colors(component_path: str) -> Dict[str, Tuple[int, int, int]]:
    """Returns {name: (r, g, b)} for every <UserColor Name=".." RGB="#rrggbb" .../> declared in
    this component's own Settings/UserColors.xml - every entry, whether or not anything on a
    page actually references it."""
    colors: Dict[str, Tuple[int, int, int]] = {}
    settings_path = pathlib.Path(component_path) / "Settings" / "UserColors.xml"
    if not settings_path.exists():
        return colors
    try:
        tree = ET.parse(str(settings_path))
    except ET.XMLSyntaxError:
        return colors
    for user_color in tree.getroot().iter("UserColor"):
        name = user_color.get("Name")
        rgb = user_color.get("RGB")
        if not name or not rgb:
            continue
        m = _RGB_HEX_ATTR_RE.match(rgb.strip())
        if m:
            colors.setdefault(name, _rgb_from_hex(m.group(1)))
    return colors


def scan_page_colors(component_path: str) -> Dict[str, Tuple[int, int, int]]:
    """Returns {name: (r, g, b)} for every literal RGB value found directly in this component's
    own Pages/*.xml, on any element whose tag contains "Color" (case/underscore-insensitive)."""
    colors: Dict[str, Tuple[int, int, int]] = {}
    pages_dir = pathlib.Path(component_path) / "Pages"
    if not pages_dir.is_dir():
        return colors
    for page_file in pages_dir.glob("*.xml"):
        try:
            tree = ET.parse(str(page_file))
        except ET.XMLSyntaxError:
            continue
        for elem in tree.getroot().iter():
            tag = elem.tag
            if not isinstance(tag, str) or "color" not in tag.lower() or tag == "UserColor":
                continue
            rgb_attr = elem.get("RGB")
            if rgb_attr:
                m = _RGB_HEX_ATTR_RE.match(rgb_attr.strip())
                if m:
                    rgb = _rgb_from_hex(m.group(1))
                    if rgb not in _KNOWN_W3C_RGB:
                        colors.setdefault(rgb_name(*rgb), rgb)
                continue
            text = (elem.text or "").strip()
            if not text:
                continue
            rgb = rgb_from_literal_text(text)
            if rgb is not None and rgb not in _KNOWN_W3C_RGB:
                colors.setdefault(rgb_name(*rgb), rgb)
    return colors
