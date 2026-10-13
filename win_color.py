"""Generates w2w-color.css - one CSS rule block per color in the merged giim::s_AllColors
registry (see gii_module.ensure_all_colors_values) - from the w2w-colors.template.css template
bundled alongside this tool, and writes it into the main model's own WebUI/resources/css folder
once, if anything in the project actually used AIMMS data coloring (a table identifier's
Colors/Background_Color, or a line/bar chart identifier's Color - see
win_object_tools.investigate_contents).

The template defines the CSS rule(s) for ONE placeholder color. This module auto-detects which
standard color name is used as the placeholder, then repeats the template's literal text once
per color in the merged registry, substituting that color in each copy - so it keeps working
even if the template's selectors/properties/comments change later. Reading the template
(read_template) and expanding it (expand_css) are separate steps: the template must be read
while the cwd is still the tool's own directory, but the merged registry it's expanded against
isn't known until the whole per-component loop has finished scanning every component's pages and
Settings/UserColors.xml.
"""

import pathlib
from collections import Counter
from typing import Dict, Tuple
import re

# The 147 standard CSS/HTML named colors.
COLORS = [
    "aliceblue", "antiquewhite", "aqua", "aquamarine", "azure", "beige", "bisque",
    "black", "blanchedalmond", "blue", "blueviolet", "brown", "burlywood",
    "cadetblue", "chartreuse", "chocolate", "coral", "cornflowerblue", "cornsilk",
    "crimson", "cyan", "darkblue", "darkcyan", "darkgoldenrod", "darkgray",
    "darkgreen", "darkgrey", "darkkhaki", "darkmagenta", "darkolivegreen",
    "darkorange", "darkorchid", "darkred", "darksalmon", "darkseagreen",
    "darkslateblue", "darkslategray", "darkslategrey", "darkturquoise",
    "darkviolet", "deeppink", "deepskyblue", "dimgray", "dimgrey", "dodgerblue",
    "firebrick", "floralwhite", "forestgreen", "fuchsia", "gainsboro",
    "ghostwhite", "gold", "goldenrod", "gray", "grey", "green", "greenyellow",
    "honeydew", "hotpink", "indianred", "indigo", "ivory", "khaki", "lavender",
    "lavenderblush", "lawngreen", "lemonchiffon", "lightblue", "lightcoral",
    "lightcyan", "lightgoldenrodyellow", "lightgray", "lightgreen", "lightgrey",
    "lightpink", "lightsalmon", "lightseagreen", "lightskyblue",
    "lightslategray", "lightslategrey", "lightsteelblue", "lightyellow", "lime",
    "limegreen", "linen", "magenta", "maroon", "mediumaquamarine", "mediumblue",
    "mediumorchid", "mediumpurple", "mediumseagreen", "mediumslateblue",
    "mediumspringgreen", "mediumturquoise", "mediumvioletred", "midnightblue",
    "mintcream", "mistyrose", "moccasin", "navajowhite", "navy", "oldlace",
    "olive", "olivedrab", "orange", "orangered", "orchid", "palegoldenrod",
    "palegreen", "paleturquoise", "palevioletred", "papayawhip", "peachpuff",
    "peru", "pink", "plum", "powderblue", "purple", "red", "rosybrown",
    "royalblue", "saddlebrown", "salmon", "sandybrown", "seagreen", "seashell",
    "sienna", "silver", "skyblue", "slateblue", "slategray", "slategrey",
    "snow", "springgreen", "steelblue", "tan", "teal", "thistle", "tomato",
    "turquoise", "violet", "wheat", "white", "whitesmoke", "yellow",
    "yellowgreen",
]
assert len(COLORS) == 147, len(COLORS)

# Each of the 147 names' (r, g, b) channel values (0-255), sourced from
# https://www.w3schools.com/Tags/ref_colornames.asp - used as the highest-priority tier when
# merging in project-specific colors discovered from WinUI page styling and Settings/UserColors.xml
# (see win_color_scan.py) into gii_module.ensure_all_colors_values()'s giim::p_Red/p_Green/p_Blue(i_color).
COLOR_RGB: Dict[str, Tuple[int, int, int]] = {
    "aliceblue": (240, 248, 255),
    "antiquewhite": (250, 235, 215),
    "aqua": (0, 255, 255),
    "aquamarine": (127, 255, 212),
    "azure": (240, 255, 255),
    "beige": (245, 245, 220),
    "bisque": (255, 228, 196),
    "black": (0, 0, 0),
    "blanchedalmond": (255, 235, 205),
    "blue": (0, 0, 255),
    "blueviolet": (138, 43, 226),
    "brown": (165, 42, 42),
    "burlywood": (222, 184, 135),
    "cadetblue": (95, 158, 160),
    "chartreuse": (127, 255, 0),
    "chocolate": (210, 105, 30),
    "coral": (255, 127, 80),
    "cornflowerblue": (100, 149, 237),
    "cornsilk": (255, 248, 220),
    "crimson": (220, 20, 60),
    "cyan": (0, 255, 255),
    "darkblue": (0, 0, 139),
    "darkcyan": (0, 139, 139),
    "darkgoldenrod": (184, 134, 11),
    "darkgray": (169, 169, 169),
    "darkgreen": (0, 100, 0),
    "darkgrey": (169, 169, 169),
    "darkkhaki": (189, 183, 107),
    "darkmagenta": (139, 0, 139),
    "darkolivegreen": (85, 107, 47),
    "darkorange": (255, 140, 0),
    "darkorchid": (153, 50, 204),
    "darkred": (139, 0, 0),
    "darksalmon": (233, 150, 122),
    "darkseagreen": (143, 188, 143),
    "darkslateblue": (72, 61, 139),
    "darkslategray": (47, 79, 79),
    "darkslategrey": (47, 79, 79),
    "darkturquoise": (0, 206, 209),
    "darkviolet": (148, 0, 211),
    "deeppink": (255, 20, 147),
    "deepskyblue": (0, 191, 255),
    "dimgray": (105, 105, 105),
    "dimgrey": (105, 105, 105),
    "dodgerblue": (30, 144, 255),
    "firebrick": (178, 34, 34),
    "floralwhite": (255, 250, 240),
    "forestgreen": (34, 139, 34),
    "fuchsia": (255, 0, 255),
    "gainsboro": (220, 220, 220),
    "ghostwhite": (248, 248, 255),
    "gold": (255, 215, 0),
    "goldenrod": (218, 165, 32),
    "gray": (128, 128, 128),
    "grey": (128, 128, 128),
    "green": (0, 128, 0),
    "greenyellow": (173, 255, 47),
    "honeydew": (240, 255, 240),
    "hotpink": (255, 105, 180),
    "indianred": (205, 92, 92),
    "indigo": (75, 0, 130),
    "ivory": (255, 255, 240),
    "khaki": (240, 230, 140),
    "lavender": (230, 230, 250),
    "lavenderblush": (255, 240, 245),
    "lawngreen": (124, 252, 0),
    "lemonchiffon": (255, 250, 205),
    "lightblue": (173, 216, 230),
    "lightcoral": (240, 128, 128),
    "lightcyan": (224, 255, 255),
    "lightgoldenrodyellow": (250, 250, 210),
    "lightgray": (211, 211, 211),
    "lightgreen": (144, 238, 144),
    "lightgrey": (211, 211, 211),
    "lightpink": (255, 182, 193),
    "lightsalmon": (255, 160, 122),
    "lightseagreen": (32, 178, 170),
    "lightskyblue": (135, 206, 250),
    "lightslategray": (119, 136, 153),
    "lightslategrey": (119, 136, 153),
    "lightsteelblue": (176, 196, 222),
    "lightyellow": (255, 255, 224),
    "lime": (0, 255, 0),
    "limegreen": (50, 205, 50),
    "linen": (250, 240, 230),
    "magenta": (255, 0, 255),
    "maroon": (128, 0, 0),
    "mediumaquamarine": (102, 205, 170),
    "mediumblue": (0, 0, 205),
    "mediumorchid": (186, 85, 211),
    "mediumpurple": (147, 112, 219),
    "mediumseagreen": (60, 179, 113),
    "mediumslateblue": (123, 104, 238),
    "mediumspringgreen": (0, 250, 154),
    "mediumturquoise": (72, 209, 204),
    "mediumvioletred": (199, 21, 133),
    "midnightblue": (25, 25, 112),
    "mintcream": (245, 255, 250),
    "mistyrose": (255, 228, 225),
    "moccasin": (255, 228, 181),
    "navajowhite": (255, 222, 173),
    "navy": (0, 0, 128),
    "oldlace": (253, 245, 230),
    "olive": (128, 128, 0),
    "olivedrab": (107, 142, 35),
    "orange": (255, 165, 0),
    "orangered": (255, 69, 0),
    "orchid": (218, 112, 214),
    "palegoldenrod": (238, 232, 170),
    "palegreen": (152, 251, 152),
    "paleturquoise": (175, 238, 238),
    "palevioletred": (219, 112, 147),
    "papayawhip": (255, 239, 213),
    "peachpuff": (255, 218, 185),
    "peru": (205, 133, 63),
    "pink": (255, 192, 203),
    "plum": (221, 160, 221),
    "powderblue": (176, 224, 230),
    "purple": (128, 0, 128),
    "red": (255, 0, 0),
    "rosybrown": (188, 143, 143),
    "royalblue": (65, 105, 225),
    "saddlebrown": (139, 69, 19),
    "salmon": (250, 128, 114),
    "sandybrown": (244, 164, 96),
    "seagreen": (46, 139, 87),
    "seashell": (255, 245, 238),
    "sienna": (160, 82, 45),
    "silver": (192, 192, 192),
    "skyblue": (135, 206, 235),
    "slateblue": (106, 90, 205),
    "slategray": (112, 128, 144),
    "slategrey": (112, 128, 144),
    "snow": (255, 250, 250),
    "springgreen": (0, 255, 127),
    "steelblue": (70, 130, 180),
    "tan": (210, 180, 140),
    "teal": (0, 128, 128),
    "thistle": (216, 191, 216),
    "tomato": (255, 99, 71),
    "turquoise": (64, 224, 208),
    "violet": (238, 130, 238),
    "wheat": (245, 222, 179),
    "white": (255, 255, 255),
    "whitesmoke": (245, 245, 245),
    "yellow": (255, 255, 0),
    "yellowgreen": (154, 205, 50),
}
assert set(COLOR_RGB.keys()) == set(COLORS)

_COLOR_PATTERN = re.compile(r"\b(" + "|".join(re.escape(c) for c in COLORS) + r")\b")

DEFAULT_TEMPLATE_PATH = "w2w-colors.template.css"

_CSS_UNSAFE_CHARS_RE = re.compile(r"[^A-Za-z0-9_-]+")


def css_class_slug(color_name: str) -> str:
    """Turns an s_AllColors element name into a single safe CSS class-name token. Names are kept
    exactly as discovered elsewhere (see win_color_scan.py) - some (a WinUI UserColor like "old
    text font", or a multi-word member of AIMMS's own built-in AllColors system set like "light
    grey") aren't already safe on their own, since a raw embedded space would otherwise split
    "annotation-color-old text font" into three separate space-separated class tokens instead of
    one. gii_module's p_ColorSlug parameter maps every s_AllColors member to the same slug this
    produces, so the "color-%s" annotation formula (see win_object_tools.py) and the CSS classes
    generated here (see expand_css) always agree."""
    slug = _CSS_UNSAFE_CHARS_RE.sub("_", color_name.strip())
    if not slug or slug[0].isdigit():
        slug = f"_{slug}"
    return slug


def _detect_placeholder(template_text: str) -> str | None:
    """Finds which of the 147 standard color names the template uses as its placeholder (the
    one it repeats for every rule), by taking the most frequent match. None if none appear."""
    matches = _COLOR_PATTERN.findall(template_text)
    if not matches:
        return None
    return Counter(matches).most_common(1)[0][0]


def read_template(template_path: str = DEFAULT_TEMPLATE_PATH) -> str:
    """Reads the raw w2w-colors.template.css text. Call this while the current working
    directory is still the tool's own directory (that's where the bundled template lives - see
    w2w.spec `datas`), before winui_to_webui.process_aimms_app changes into the project folder.

    Expansion itself (see expand_css) happens later, once the merged giim::s_AllColors registry
    is known - only complete after the whole per-component loop has run."""
    with open(template_path, "r", newline="", encoding="utf-8") as f:
        return f.read()


def expand_css(template_text: str, color_rgb: Dict[str, Tuple[int, int, int]]) -> str:
    """Expands `template_text` (see read_template) into the full w2w-color.css content, one
    block per (name, rgb) entry in color_rgb - normally the same merged registry backing
    giim::s_AllColors (see gii_module.ensure_all_colors_values), so every color that can appear
    as a data-coloring source has a matching CSS rule, not just the 147 standard CSS/HTML names
    the template itself happens to be written in terms of.

    The placeholder's own name only doubles as a valid CSS color value by coincidence (it's one
    of the 147 standard keywords) - most merged project colors (RGB literals, multi-word
    UserColors) aren't, so occurrences used as a CSS property VALUE (between ": " and ";") are
    substituted with an rgb(r, g, b) literal instead of the bare name; every other occurrence
    (the annotation-color-<name> class and the comment) uses css_class_slug(name) instead of the
    plain name, since the name itself isn't always a safe single CSS token (see css_class_slug) -
    this must produce the exact same slug gii_module's p_ColorSlug parameter maps that name to,
    since that's what the "color-%s" annotation formula (win_object_tools.py) actually emits."""
    placeholder = _detect_placeholder(template_text)
    if placeholder is None:
        raise ValueError("No standard CSS color name found in the template to use as the placeholder.")

    value_pattern = re.compile(r"(?<=:\s)" + re.escape(placeholder) + r"(?=\s*;)")
    other_pattern = re.compile(r"\b" + re.escape(placeholder) + r"\b")

    blocks = []
    for name, (r, g, b) in color_rgb.items():
        slug = css_class_slug(name)
        block = value_pattern.sub(lambda m, r=r, g=g, b=b: f"rgb({r}, {g}, {b})", template_text)
        block = other_pattern.sub(lambda m, slug=slug: slug, block)
        blocks.append(block)
    return "".join(blocks)


def write_color_css(component_dict: dict, css_content: str) -> None:
    """Writes w2w-color.css into this component's own WebUI/resources/css folder."""
    dest_dir = pathlib.Path(component_dict["Path"]) / "WebUI" / "resources" / "css"
    dest_dir.mkdir(parents=True, exist_ok=True)
    (dest_dir / "w2w-color.css").write_text(css_content, encoding="utf-8", newline="")


def remove_color_css(component_dict: dict) -> None:
    """Deletes a previously generated w2w-color.css from this component, if present."""
    css_path = pathlib.Path(component_dict["Path"]) / "WebUI" / "resources" / "css" / "w2w-color.css"
    if css_path.exists():
        css_path.unlink()
