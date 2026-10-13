from typing import List, Dict, Tuple, Any, Union, Optional # Add Tuple and any other types you use
from web_page_types import WebUIData  # type: ignore
import copy
import json
import pathlib
import re
import tools
from aimms_slug import aimms_slug
from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import modeledit_aimmspy2
import gii_module

"""
This module defines the WebUI class to manage AIMMS WebUI specifications.
It provides methods to create pages and widgets within the WebUI structure.
"""

# Switching to table v2
table_v2 = 1

# The WebUI app's built-in preset layouts (layouts/layout <N>.txt in the project root - plain
# JSON bodies in the same Grid/WidgetArea schema used for custom layouts). web_page.py already
# references "Layout9"/"Layout10" by name as fallback defaults with no layouts/* entry needed,
# confirming the app recognizes these reserved names natively - see _register_custom_layout(),
# which checks a heuristic-detected page's shape against these before minting a custom one.
#
# Layout9 is deliberately excluded: it's shape-identical to Layout11 (both columns="1fr",
# rows="1fr", areas='"area-a"'), but carries an extra item prop (runIntoGridGap: true,
# gridAutoFlow: "column" vs Layout11's "row") tied to its own existing, unrelated role as the
# has_tabbed_widget default in add_page_to_pages_list - not a match target for a heuristic-
# detected page, so it's left exactly as-is for that one purpose. Layout11 has no such
# conflict and is a perfectly good match for a genuinely single-widget page.
STANDARD_LAYOUTS = {
    "Layout1": ("1fr", "1fr 1fr", '"area-a" "area-b"'),
    "Layout2": ("1fr 1fr", "1fr 1fr", '"area-a area-a" "area-b area-c"'),
    "Layout3": ("1fr 1fr 1fr 1fr", "1fr 1fr", '"area-a area-a area-a area-a" "area-b area-c area-d area-e"'),
    "Layout4": ("1fr 3fr", "1fr 1fr", '"area-a area-a" "area-b area-c"'),
    "Layout5": ("1fr 1fr", "1fr 1fr", '"area-a area-b" "area-c area-d"'),
    "Layout6": ("1fr 1fr 1fr 1fr", "1fr 1fr", '"area-a area-b area-c area-c" "area-d area-d area-e area-e"'),
    "Layout7": ("1fr 1fr 1fr", "1fr 1fr", '"area-a area-b area-c" "area-d area-d area-d"'),
    "Layout8": ("1fr 1fr 1fr 1fr", "1fr 1fr", '"area-a area-a area-b area-c" "area-d area-d area-d area-d"'),
    "Layout10": ("3fr 1fr", "1fr 1fr 1fr", '"area-a area-b" "area-a area-c" "area-a area-d"'),
    "Layout11": ("1fr", "1fr", '"area-a"'),
}

# WinUI objects do not have names.
# WebUI widgets need unique names.
# These are built from a stable identity for the underlying WinUI object - its own
# ObjectUUID when WinUI provides one (Pivot Table today), otherwise a fallback derived
# from its page's slug plus its position among that page's objects - both computed by
# win_object_tools.compute_stable_id(). This keeps names stable across runs regardless of
# what happens elsewhere in the project (see documentation/status.md).

class WebUI:
    def __init__(self, webui_filename:str, component_dict:dict):
        """
        Initialize the WebUI helper, loading an existing file when present or creating a default structure.
        
        :param webui_filename: Path to the WebUI JSON file to load or create.
        :type webui_filename: str
        :param component_dict: Metadata describing the current component (prefix, display name, slug).
        :type component_dict: dict
        :return: None. Loads data into memory for further modification.
        :rtype: None
        """
        #Initializes the WebUI object.
        self.comp_dict = component_dict
        self.share_layouts = False  # see _register_custom_layout; set from --share-layouts
        # Annotate the runtime dict with the TypedDict for better static checking
        webui_path = pathlib.Path(webui_filename)
        if webui_path.exists():
            webui_file = webui_path.open("r")
            self.data = json.load(webui_file)
        else:
            if component_dict["Prefix"] == "":
                # The component is the Main Model.
                pages_dict = {
                        "literal": {
                            "name": "root",
                            "slug": "root",
                            "children": [
                                {
                                    "name": "Main Project",
                                    "slug": "main_project",
                                    "children": [
                                        {
                                            "name": "home",
                                            "slug": "home",
                                            "type": "pagev2-grid",
                                            "children": []
                                        }
                                    ]
                                }
                            ]
                        }
                    }
            else:
                # The component is a Library.
                pages_dict = {
                        "literal": {
                            "name": "root",
                            "slug": "root",
                            "children": [
                                {
                                    "name": component_dict["DisplayName"],
                                    "slug": component_dict["DisplaySlug"],
                                    "children": []
                                }
                            ]
                        }
                    }

            self.data = {
                "application": {
                    "aimms.widget.type": {
                        "literal": "application"
                    },
                    "browser.language": {
                        "aimms": {
                            "contents": [
                                "webui::ClientBrowserLanguage"
                            ]
                        }
                    },
                    "browser.name": {
                        "aimms": {
                            "contents": [
                                "webui::ClientBrowserName"
                            ]
                        }
                    },
                    "browser.timezone": {
                        "aimms": {
                            "contents": [
                                "webui::BrowserTimeZone"
                            ]
                        }
                    },
                    "ignoredst": {
                        "aimms": {
                            "contents": [
                                "webui::IgnoreDST"
                            ]
                        }
                    },
                    "pages": pages_dict,
                    "theme.classic": {
                        "literal": "NOT_ALLOWED"
                    },
                    "timezone": {
                        "aimms": {
                            "contents": [
                                "webui::DisplayTimeZone"
                            ]
                        }
                    }
                },
                "version": "4.67.0"
            }

            # Append page definition of home page, as an empty page:
            if component_dict["Prefix"] == "":
                self.data["pages/home"] = {
                    "aimms.widget.type": {
                        "literal": "pagev2-grid"
                    },
                    "bindings": {
                        "literal": []
                    },
                    "layoutId": {
                        "literal": "Layout9"
                    },
                    "widgets": {
                        "literal": []
                    }
                }

    def _mark_visibility_control_widgets_compact(self) -> None:
        """
        Switch every widget the end user actually toggles a "widget.visible" condition with (see
        _apply_widget_visibility) into compact display mode - e.g. the FlowAccuracyIsRelative
        checkbox widget that shows/hides an absolute-vs-relative error table pair, not the table
        widgets themselves. Runs once across this whole component's data (every page already
        converted), so it works regardless of whether the controlling widget was converted before
        or after the widget(s) whose visibility it drives.

        A "widget.visible" expression with no matching widget on any page (e.g. one of our own
        auto-generated negation parameters from win_object_tools.resolve_widget_visibility, which
        never gets its own widget) simply has nothing to mark - not an error.

        Only applies when the controlling identifier is a widget's *sole* content item - a
        multi-parameter scalar widget that happens to bundle a visibility-controlling identifier
        alongside other, unrelated ones is left at its normal (non-compact) display.

        :return: None. Mutates self.data in place.
        :rtype: None
        """
        controlling_identifiers = set()
        for widget in self.data.values():
            if not isinstance(widget, dict):
                continue
            visible_contents = widget.get("widget.visible", {}).get("aimms", {}).get("contents")
            if visible_contents:
                controlling_identifiers.update(visible_contents)

        if not controlling_identifiers:
            return

        for widget in self.data.values():
            if not isinstance(widget, dict):
                continue
            if widget.get("aimms.widget.type", {}).get("literal") not in ("scalar", "selectionbox-v2"):
                continue
            own_contents = widget.get("contents", {}).get("aimms", {}).get("contents")
            # Only a widget that displays nothing but the controlling identifier itself is a
            # bare toggle control (e.g. FlowAccuracyIsRelative) - a multi-parameter scalar
            # widget that merely happens to include one such identifier among several unrelated
            # ones must keep its normal (non-compact) display.
            if own_contents and len(own_contents) == 1 and controlling_identifiers.intersection(own_contents):
                widget["compact"] = { "literal": 1 }

    def get_data(self) -> dict:
        """
        Return the entire WebUI data dictionary managed by the helper.

        :return: WebUI data structure to be serialized to JSON.
        :rtype: dict
        """
        self._mark_visibility_control_widgets_compact()
        return self.data

    def get_root_page(self) -> dict:
        """
        Return a handle to the root page dictionary in the pages tree.
        
        :return: Root page dictionary from the WebUI pages tree.
        :rtype: dict
        """
        return self.data["application"]["pages"]["literal"]["children"][0]

    def restrict_to_page(self, snapshot: dict, page_name: str, component_dict: dict) -> bool:
        """
        Keep only the given page's conversion result, restoring everything else to `snapshot`.

        Called after a full conversion walk (needed so each component's own GeneratedInterfaceIdentifiers
        module stays complete for every page still referenced anywhere - it is rebuilt from scratch
        every run, but widget/identifier names are now stable-identity-based, see
        win_object_tools.compute_stable_id, so regenerating them reproduces the same names and
        doesn't disturb pages we're not touching).
        Used only in single-page (`--page`) mode, so that pages other than the requested one -
        including any manual WebUI-editor tweaks made to them - are left exactly as they were on
        disk before this run.

        :param snapshot: Deep copy of `self.data` taken before the conversion walk ran.
        :type snapshot: dict
        :param page_name: WinUI page Name (PageManager.xml "Name" attribute) to keep.
        :type page_name: str
        :param component_dict: Metadata describing the current component being converted.
        :type component_dict: dict
        :return: True if the page belongs to this component (and was kept), False otherwise
            (in which case `self.data` is restored to `snapshot` unchanged).
        :rtype: bool
        """

        target_key = "pages/" + aimms_slug(page_name)

        if target_key not in self.data:
            self.data = copy.deepcopy(snapshot)
            return False

        prefix = component_dict.get("Prefix", "")

        def widget_key(uri: str) -> str:
            if prefix != "" and uri.startswith(prefix + "::"):
                uri = uri[len(prefix) + 2:]
            return "widgets/" + uri

        # dict.fromkeys() rather than a set: preserves the widgets' original document order
        # (a plain set's iteration order depends on per-process hash randomization, which would
        # make the key order in the written webui.json - harmless to WebUI itself, but noisy to
        # review in a git diff - nondeterministic across runs even when nothing really changed).
        new_widget_keys = dict.fromkeys(
            widget_key(w["uri"])
            for w in self.data[target_key].get("widgets", {}).get("literal", [])
        )
        old_widget_keys = set()
        if target_key in snapshot:
            old_widget_keys = {
                widget_key(w["uri"])
                for w in snapshot[target_key].get("widgets", {}).get("literal", [])
            }

        # A detected custom grid layout (win_layout / web_page._register_custom_layout) lives in
        # its own top-level layouts/<layoutId> key, outside the widgets/* keys handled above -
        # needs the same new/old copy-and-clean-up treatment, or it silently dangles (layoutId
        # pointing at a layout definition that was never carried into `final`).
        def layout_key(page_dict: dict):
            layout_id = page_dict.get("layoutId", {}).get("literal", "")
            return f"layouts/{layout_id}" if layout_id.startswith("custom_") else None

        new_layout_key = layout_key(self.data[target_key])
        old_layout_key = layout_key(snapshot[target_key]) if target_key in snapshot else None

        final = copy.deepcopy(snapshot)
        final["application"]["pages"] = self.data["application"]["pages"]
        final[target_key] = self.data[target_key]

        for key in new_widget_keys:
            if key in self.data:
                final[key] = self.data[key]

        for key in old_widget_keys - new_widget_keys.keys():
            final.pop(key, None)

        if new_layout_key and new_layout_key in self.data:
            final[new_layout_key] = self.data[new_layout_key]
        if old_layout_key and old_layout_key != new_layout_key:
            # A custom layout can now be shared across pages (web_page._register_custom_layout
            # dedups identical shapes) - only actually remove it if no other page still
            # references it, or an untouched page restored unchanged from the snapshot would be
            # left pointing at a layout definition we just deleted.
            still_referenced = any(
                key != target_key and key.startswith("pages/") and
                page_dict.get("layoutId", {}).get("literal", "") == old_layout_key[len("layouts/"):]
                for key, page_dict in final.items()
            )
            if not still_referenced:
                final.pop(old_layout_key, None)

        self.data = final
        return True

    def add_page_to_tree(self,page_parent:dict,page_name:str,page_slug:str) -> dict:
        """
        Create a WebUI page entry in the pages tree and return a handle to the created or existing node.
        
        :param page_parent: Parent page dictionary in the pages tree where the page is added.
        :type page_parent: dict
        :param page_name: Display name for the page to be created.
        :type page_name: str
        :param page_slug: Slug identifier for the page.
        :type page_slug: str
        :return: Dictionary representing the page in the pages tree.
        :rtype: dict
        """

        pagename = "pages/"+page_slug

        # Ensure the pages tree structure exists.
        if "pages" not in self.data["application"]:
            self.data["application"]["pages"] = { 
                "literal" : {
                    "name": "root",
                    "slug": "root",
                    "children": [                      
                        {
                            "name": "Main Project",
                            "slug": "main_project",
                            "type": "pagev2-grid",
                            "children": [  
                                {
                                    "name": "home",
                                    "slug": "home",
                                    "type": "pagev2-grid",
                                    "children": []
                                }
                            ]
                        }
                    ]
                }
            }

        # Add the page to the pages tree if not already present.
        # Match/create using the prefixed slug throughout, so a page from a library component
        # (Prefix != "") is recognized as already present on a later run against a persisted tree
        # (single-page mode loads and reuses an existing tree instead of always starting empty).
        if self.comp_dict["Prefix"] != "":
            page_slug = self.comp_dict["Prefix"] + "::" + page_slug

        pages_tree = page_parent["children"]
        in_list = 0
        for existing_page in pages_tree:
            if existing_page["slug"] == page_slug:
                in_list = 1
                pages_tree_dict = existing_page
                break
        if in_list == 0:
            pages_tree_entry = {
                "name": page_name,
                "type": "pagev2-grid",
                "slug": page_slug,
                "children": []
            }
            pages_tree.append(pages_tree_entry)
            pages_tree_dict = pages_tree_entry

        return pages_tree_dict

    def _find_matching_standard_layout(self, layout_plan) -> Optional[str]:
        """Return the preset name (e.g. "Layout5") whose shape exactly matches layout_plan's,
        or None if it matches none of them. See STANDARD_LAYOUTS."""
        shape = (layout_plan.grid_template_columns, layout_plan.grid_template_rows, layout_plan.grid_template_areas)
        for name, preset_shape in STANDARD_LAYOUTS.items():
            if shape == preset_shape:
                return name
        return None

    def _find_matching_custom_layout(self, layout_plan, unused_only: bool = False) -> Optional[str]:
        """Return the layoutId of an already-registered custom_* layout (in this run, or loaded
        from an existing webui.json in --page mode) whose shape exactly matches layout_plan's,
        or None if none matches. unused_only: only one no page uses yet (e.g. the reconverted
        page's own previous layout in --page mode), so it is never shared."""
        shape = (layout_plan.grid_template_columns, layout_plan.grid_template_rows, layout_plan.grid_template_areas)
        used_ids = {entry.get("layoutId", {}).get("literal") for key, entry in self.data.items()
                    if key.startswith("pages/") and isinstance(entry, dict)} if unused_only else set()
        for key, entry in self.data.items():
            if not key.startswith("layouts/custom_") or key[len("layouts/"):] in used_ids:
                continue
            props = entry.get("definition", {}).get("literal", {}).get("props", {})
            existing_shape = (props.get("gridTemplateColumns"), props.get("gridTemplateRows"), props.get("gridTemplateAreas"))
            if shape == existing_shape:
                return key[len("layouts/"):]
        return None

    def _next_custom_layout_order(self, rows: int, cols: int) -> int:
        """Next unused order number for the custom_r{rows}c{cols}_ bucket - found by scanning
        self.data rather than a separately-tracked counter, so it stays correct across
        --page-mode reruns the same way _find_matching_custom_layout() does."""
        prefix = f"layouts/custom_r{rows}c{cols}_"
        pattern = re.compile(re.escape(prefix) + r"(\d+)$")
        max_n = 0
        for key in self.data:
            m = pattern.match(key)
            if m:
                max_n = max(max_n, int(m.group(1)))
        return max_n + 1

    def _register_custom_layout(self, layout_plan) -> str:
        """
        Resolve the layoutId for a detected custom CSS grid layout (win_layout.LayoutPlan):
        reuse a standard preset (STANDARD_LAYOUTS) or an already-registered custom_* layout with
        the exact same shape when one exists, otherwise register a new
        `layouts/custom_r{rows}c{cols}_{n}` entry and return that. Schema confirmed via a real
        hand-built reference example (there is no public documentation for it) - see
        documentation/layout heuristic.md.

        :param layout_plan: Detected custom grid layout.
        :type layout_plan: win_layout.LayoutPlan
        :return: The layoutId to assign to the page.
        :rtype: str
        """
        # A standard preset is always used when it matches. --share-layouts: pages with the same
        # grid shape also share one custom_* entry. Off (default): every page needing a custom
        # layout gets its own, so editing one page's layout in WebUI never changes another page.
        standard_match = self._find_matching_standard_layout(layout_plan)
        if standard_match is not None:
            return standard_match

        existing_match = self._find_matching_custom_layout(layout_plan, unused_only=not self.share_layouts)
        if existing_match is not None:
            return existing_match

        order = self._next_custom_layout_order(layout_plan.rows, layout_plan.cols)
        layout_id = f"custom_r{layout_plan.rows}c{layout_plan.cols}_{order}"

        items = []
        for area_name in layout_plan.area_names:
            letters = area_name[len("area-"):]
            items.append({
                "componentName": "WidgetArea",
                "props": {
                    "gridArea": area_name,
                    "name": f"Area {letters.upper()}",
                    "gridAutoFlow": "row"
                }
            })

        layout_entry = {
            f"layouts/{layout_id}": {
                "definition": {
                    "literal": {
                        "componentName": "Grid",
                        "props": {
                            "gridTemplateColumns": layout_plan.grid_template_columns,
                            "gridTemplateRows": layout_plan.grid_template_rows,
                            "gridTemplateAreas": layout_plan.grid_template_areas
                        },
                        "items": items
                    }
                },
                "displayName": {
                    "literal": layout_id
                }
            }
        }
        self.data.update(layout_entry)

        return layout_id

    def add_page_to_pages_list(self,page_slug:str, ancestor_info:dict, layout_plan=None) -> dict:
        """
        Create a WebUI page dictionary in the pages list and return a handle to it.

        :param page_slug: Slug identifier for the page to be created.
        :type page_slug: str
        :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
        :type ancestor_info: dict
        :param layout_plan: Detected custom grid layout for this page (win_layout.LayoutPlan), or
            None to keep the existing default Layout9/Layout10 behavior.
        :type layout_plan: win_layout.LayoutPlan | None
        :return: Page dictionary suitable for attaching widgets.
        :rtype: dict
        """

        pagename = "pages/"+page_slug

        # Choose layout of page: a detected custom grid takes precedence; otherwise fall back to
        # the existing default layouts.
        if layout_plan is not None:
            layout = self._register_custom_layout(layout_plan)
        else:
            ancestor_has_tabbed_widget = ancestor_info.get('has_tabbed_widget',0)
            if ancestor_has_tabbed_widget == 1:
                layout = "Layout9"
            else:
                layout = "Layout10"

        # Create the page dictionary
        webpage_dict = {
                "aimms.widget.type": {
                    "literal": "pagev2-grid"
                },
                "bindings": {
                    "literal": []
                },
                "layoutId": {
                    "literal": layout
                },
                "widgets": {
                    "literal": []
                }
            }
        pages_list_entry_dict = {  
            pagename: webpage_dict
        }

        # Append the page to end of the main data dictionary
        self.data.update(pages_list_entry_dict)

        # return a handle to the created page dictionary, such that Webui widgets can be added to it.
        return webpage_dict

    def update_page_dict(self, webui_page_dict:dict, area:str, widget_name:str) -> None:
        """
        Update a WebUI page dictionary to reference the given widget in the specified grid area.
        
        :param webui_page_dict: WebUI page specification where the widget reference will be added.
        :type webui_page_dict: dict
        :param area: Grid area identifier where the widget should be placed.
        :type area: str
        :param widget_name: Name of the widget to reference within the page.
        :type widget_name: str
        :return: None. Adds binding and widget entries to the page definition.
        :rtype: None
        """

        if self.comp_dict["Prefix"] == "":
            widget_uri = widget_name
        else:
            widget_uri = f"{self.comp_dict["Prefix"]}::{widget_name}"

        # Create a reference to the widget in the page's bindings list
        webui_widget_in_binding_list_page = { 
            "widgetUri": widget_uri, 
            "gridArea": area,
            "dndId": area + widget_uri
        }
        # Add this reference to the page bindings list
        webui_page_dict["bindings"]["literal"].append(webui_widget_in_binding_list_page)

        # Create a reference to the widget in the page's widgets list  
        if self.comp_dict["Prefix"] == "":
            widget_uri = widget_name
        else:
            widget_uri = f"{self.comp_dict['Prefix']}::{widget_name}"
        webui_widget_in_widget_list_page = { 
            "uri": widget_uri, 
            "layoutInfo": {
                "width": "2",
                "height": "1"
            }
        }
        # Add this reference to the page widgets list.
        webui_page_dict["widgets"]["literal"].append(webui_widget_in_widget_list_page)  

    def _apply_widget_visibility(self, webui_widget_details:dict, visible_expr:str=None) -> None:
        """
        Set a widget's "widget.visible" WebUI binding from the AIMMS boolean expression resolved
        for its source PageObject's WinUI <Hidden> visibility (see
        win_object_tools.compute_layout_slot / resolve_widget_visibility - already correctly
        negated there, since WinUI's Hidden and WebUI's visible have opposite polarity). A no-op
        when visible_expr is None (not conditionally hidden), leaving the widget always visible
        as before.

        Does NOT touch compact mode - that belongs on whatever widget the end user actually
        toggles the controlling parameter with (if any exists on this component's pages), not on
        this shown/hidden widget itself. See _mark_visibility_control_widgets_compact(), applied
        once across the whole component right before get_data() hands the data off to be written.

        :param webui_widget_details: The widget's own dict, mutated in place.
        :type webui_widget_details: dict
        :param visible_expr: The AIMMS expression this widget's visibility depends on, or None.
        :type visible_expr: str
        :return: None.
        :rtype: None
        """
        if visible_expr:
            webui_widget_details['widget.visible'] = { "aimms": { "contents": [visible_expr] } }

    def add_button_widget(self, webui_page_dict:dict, widget_info_dict:dict, stable_id:str, area:str=None, title:str=None, visible_expr:str=None) -> str:
        """
        Create a WebUI button widget and add it to the provided page definition.

        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the button action and title.
        :type widget_info_dict: dict
        :param stable_id: Stable identity of the underlying WinUI object (see win_object_tools.compute_stable_id).
        :type stable_id: str
        :param visible_expr: AIMMS boolean expression driving this widget's runtime visibility (see
            win_object_tools.compute_layout_slot), or None to always show it.
        :type visible_expr: str
        :return: Name assigned to the created button widget.
        :rtype: str
        """

        widget_type = "button"
        widget_name = f"{widget_type}_{stable_id}"

        # Create the button widget dictionary
        webui_widget_details = {}
        procedure_name = widget_info_dict.get('procedure', '')
        if procedure_name != '':
            webui_widget_details['action'] = {
                "literal": {
                    "type": "procedure",
                    "value": procedure_name
                }
            }
        webui_widget_details['aimms.widget.type'] =  { "literal": widget_type }
        webui_widget_details['name'] = { "literal": widget_name }
        the_button_title = widget_info_dict.get('title', '')
        # A button with no title of its own falls back to a caption the layout heuristic folded
        # in (e.g. a separate Text label overlapping the button), before the widget-name fallback.
        if the_button_title == '' and title:
            the_button_title = title
        if the_button_title == '':
            the_button_title = widget_name
        webui_widget_details['title'] = { "literal": the_button_title }
        self._apply_widget_visibility(webui_widget_details, visible_expr)

        webui_widget = { "widgets/"+widget_name: webui_widget_details }

        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the button widget - the layout heuristic's if it placed one,
        # otherwise the old default ("area-d" of Layout10)
        if area is None:
            area = "area-d"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_text_widget(self, webui_page_dict:dict, widget_info_dict:dict, stable_id:str, area:str=None, title:str=None, visible_expr:str=None) -> str:
        """
        Create a WebUI text widget and add it to the provided page definition.

        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the content and literal handling for the text widget.
        :type widget_info_dict: dict
        :param stable_id: Stable identity of the underlying WinUI object (see win_object_tools.compute_stable_id).
        :type stable_id: str
        :param visible_expr: AIMMS boolean expression driving this widget's runtime visibility (see
            win_object_tools.compute_layout_slot), or None to always show it.
        :type visible_expr: str
        :return: Name assigned to the created text widget.
        :rtype: str
        """

        widget_type = "text"
        widget_name = f"{widget_type}_{stable_id}"

        # Create the button widget dictionary
        content_dict = {}
        if widget_info_dict.get("IsLiteral",0) == 1:   
            content_dict = {
                "literal": "<div>" + widget_info_dict.get("LiteralText", "Unable to get literal text") + "</div>"
            } 
        else:
            content_dict = {
                "aimms": {
                    "contents": [
                        widget_info_dict.get("LiteralText", "Unable to get string parameter name")
                    ],
                    "slices": []
                }
            }
        webui_widget_details = {
            "aimms.widget.type": {
                "literal": widget_type
            },
            "contents":content_dict,
            "name": {
                "literal": widget_name
            }
        }
        if title:
            webui_widget_details['title'] = { "literal": title }
        self._apply_widget_visibility(webui_widget_details, visible_expr)
        webui_widget = { "widgets/"+widget_name: webui_widget_details }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the text widget - the layout heuristic's if it placed one,
        # otherwise the old default ("area-a" of Layout10)
        if area is None:
            area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_network_widget(self, webui_page_dict:dict, kind:str, details:dict, stable_id:str, area:str=None, title:str=None, visible_expr:str=None) -> str:
        """
        Create a WebUI Map ("map-v2") or Diagram widget from a converted WinUI Network Object (see
        win_network.winpage_network, which builds `details`: nodes/arcs/bounds keys) and add it
        to the page.

        :param kind: "map" or "diagram".
        :return: Name assigned to the created widget.
        """
        widget_name = f"{kind}_{stable_id}"
        webui_widget_details = {
            "aimms.widget.type": { "literal": "map-v2" if kind == "map" else "diagram" },
            **details,
            "name": { "literal": widget_name }
        }
        if title:
            webui_widget_details['title'] = { "literal": title }
        self._apply_widget_visibility(webui_widget_details, visible_expr)
        self.data.update({ "widgets/"+widget_name: webui_widget_details })
        self.update_page_dict( webui_page_dict, area if area is not None else "area-a", widget_name)
        return widget_name

    def add_iframe_widget(self, webui_page_dict:dict, widget_info_dict:dict, stable_id:str, area:str=None, title:str=None, visible_expr:str=None) -> str:
        """
        Create a WebUI iframe widget and add it to the provided page definition.

        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the iframe contents and literal handling.
        :type widget_info_dict: dict
        :param stable_id: Stable identity of the underlying WinUI object (see win_object_tools.compute_stable_id).
        :type stable_id: str
        :param visible_expr: AIMMS boolean expression driving this widget's runtime visibility (see
            win_object_tools.compute_layout_slot), or None to always show it.
        :type visible_expr: str
        :return: Name assigned to the created iframe widget.
        :rtype: str
        """

        widget_type = "iframe"
        widget_name = f"{widget_type}_{stable_id}"

        # Create the button widget dictionary
        literal_text = widget_info_dict.get("LiteralText", "Unable to get literal text") 
        content_dict = {}
        if widget_info_dict.get("IsLiteral",0) == 1:
            content_dict = {
                "literal": literal_text
            }
        else:
            content_dict = {
                "aimms": {
                    "contents": [
                        literal_text
                    ]
                }
            }
        webui_widget_details = {
            "aimms.widget.type": {
                "literal": widget_type
            },
            "contents":
                content_dict
            ,
            "name": {
                "literal": widget_name
            }
        }
        if title:
            webui_widget_details['title'] = { "literal": title }
        self._apply_widget_visibility(webui_widget_details, visible_expr)
        webui_widget = { "widgets/"+widget_name: webui_widget_details }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the iframe widget - the layout heuristic's if it placed one,
        # otherwise the old default ("area-a" of Layout10)
        if area is None:
            area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_image_widget(self, webui_page_dict:dict, widget_info_dict:dict, stable_id:str, area:str=None, title:str=None, visible_expr:str=None) -> str:
        """
        Create a WebUI image widget and add it to the provided page definition.

        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the image contents and literal handling.
        :type widget_info_dict: dict
        :param stable_id: Stable identity of the underlying WinUI object (see win_object_tools.compute_stable_id).
        :type stable_id: str
        :param visible_expr: AIMMS boolean expression driving this widget's runtime visibility (see
            win_object_tools.compute_layout_slot), or None to always show it.
        :type visible_expr: str
        :return: Name assigned to the created image widget.
        :rtype: str
        """

        widget_type = "image"
        widget_name = f"{widget_type}_{stable_id}"

        # Create the button widget dictionary
        literal_text = widget_info_dict.get("LiteralPicture", "Unable to get literal picture") 
        content_dict = {}
        if widget_info_dict.get("IsLiteral",0) == 1:
            content_dict = {
                "literal": literal_text
            }
        else:
            content_dict = {
                "aimms": {
                    "contents": [
                        literal_text
                    ]
                }
            }
        webui_widget_details = {
            "aimms.widget.type": {
                "literal": widget_type
            },
            "contents":
                content_dict
            ,
            "name": {
                "literal": widget_name
            }
        }
        if title:
            webui_widget_details['title'] = { "literal": title }
        self._apply_widget_visibility(webui_widget_details, visible_expr)
        webui_widget = { "widgets/"+widget_name: webui_widget_details }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the image widget - the layout heuristic's if it placed one,
        # otherwise the old default ("area-a" of Layout10)
        if area is None:
            area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_tabbed_widget(self, webui_page_dict:dict, widget_info_dict:dict, ancestor_info:dict, stable_id:str, area:str=None, title:str=None, visible_expr:str=None) -> str:
        """
        Create a tabbed widget

        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the widget contents and partitioning.
        :type widget_info_dict: dict
        :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
        :type ancestor_info: dict
        :param stable_id: Stable identity of the underlying WinUI object (see win_object_tools.compute_stable_id).
        :type stable_id: str
        :param visible_expr: AIMMS boolean expression driving this widget's runtime visibility (see
            win_object_tools.compute_layout_slot), or None to always show it.
        :type visible_expr: str
        :return: Name assigned to the created data widget.
        :rtype: str
        """

        widget_type = "tabbedpages"
        widget_name = f"{widget_type}_{stable_id}"

        # Create the widget dictionary
        webui_widget_contents = {}
        webui_widget_contents["aimms.widget.type"] = { "literal": widget_type }
        webui_widget_contents["name"] = { "literal": widget_name }

        param_name = widget_info_dict.get('tabbed_configuration','')

        tabbedpages_tab_aimms_contents = [ f"{param_name}"]
        tabbedpages_tab_aimms_slices_list = [ 
              {
                "index": "webui::indexNoOfTabs",
                "type": "free",
                "value": "webui::indexNoOfTabs"
              },
              {
                "index": "webui::indexTabSpec",
                "type": "free",
                "value": "webui::indexTabSpec"
              }
        ]
        tabbedpages_tab_aimms = {
            "contents" :  tabbedpages_tab_aimms_contents,
            "slices"   : [ 
                {
                    "identifier" : f"{param_name}",
                    "slice" : tabbedpages_tab_aimms_slices_list
                }
            ]
        }
        webui_widget_contents["tabbedpages.tabs"]  = {
            "aimms" : tabbedpages_tab_aimms
        }
        if title:
            webui_widget_contents['title'] = { "literal": title }
        self._apply_widget_visibility(webui_widget_contents, visible_expr)

        webui_widget = {
            "widgets/"+widget_name:  webui_widget_contents
        }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the tabbed widget - the layout heuristic's if it placed one,
        # otherwise the old default ("area-a" of Layout10)
        if area is None:
            area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_data_widget(self, aimms_model: Model, gii_dict: dict, webui_page_dict:dict, widget_info_dict:dict, content_lists_expected:dict, ancestor_info:dict, stable_id:str, area:str=None, title:str=None, visible_expr:str=None) -> str:
        """
        Create a data-oriented WebUI widget (table, scalar, or selection box) and add it to the provided page definition.

        :param gii_dict: Runtime library dictionary; consulted for a synthetic indicator
            Parameter's known dimension (see gii_module.synthetic_domain_indices) when building
            a table's per-content-item slice, since such an identifier only exists as a queued
            text edit at this point, not yet in the live AIMMS session.
        :type gii_dict: dict
        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the widget contents and partitioning.
        :type widget_info_dict: dict
        :param content_lists_expected: Flags indicating which content partitions are expected for the widget type.
        :type content_lists_expected: dict
        :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
        :type ancestor_info: dict
        :param stable_id: Stable identity of the underlying WinUI object (see win_object_tools.compute_stable_id).
        :type stable_id: str
        :param visible_expr: AIMMS boolean expression driving this widget's runtime visibility (see
            win_object_tools.compute_layout_slot), or None to always show it.
        :type visible_expr: str
        :return: Name assigned to the created data widget.
        :rtype: str
        """

        inside_tabbed_widget = ancestor_info.get('has_tabbed_widget',0)

        if content_lists_expected['objecttype'] in ('scalar', 'selectionbox-v2', 'multiselect'):
            is_scalar = 1
        else:
            is_scalar = 0

        # In WebUI, scalars inside a table, look really overdone.
        widget_type = content_lists_expected.get("objecttype","table")
        if is_scalar == 0 and widget_type == 'table':
            col_header_list = widget_info_dict["contents.partition"]["colHeader"]
            row_header_list = widget_info_dict["contents.partition"]["rowHeader"]
            len_col_header_list = len(col_header_list)
            len_row_header_list = len(row_header_list)
            if len_col_header_list == 0 and len_row_header_list == 0:
                is_scalar = 1
                widget_type = 'scalar'

        widget_name = f"{widget_type}_{stable_id}"

        # Prepare the contents.partition dictionary, only including the expected content lists
        contents_partition = {}
        if content_lists_expected.get("rowHeader",0) == 1: 
            contents_partition["rowHeader"] = widget_info_dict["contents.partition"]["rowHeader"]
        if content_lists_expected.get("colHeader",0) == 1: 
            contents_partition["colHeader"] = widget_info_dict["contents.partition"]["colHeader"]
        if content_lists_expected.get("header",0) == 1: 
            contents_partition["header"] = widget_info_dict["contents.partition"]["header"]
        if content_lists_expected.get("aggregated",0) == 1: 
            contents_partition["aggregated"] = widget_info_dict["contents.partition"]["aggregated"]
        if content_lists_expected.get("stacked",0) == 1: 
            contents_partition["stacked"] = widget_info_dict["contents.partition"]["stacked"]
        if content_lists_expected.get("overlays",0) == 1: 
            contents_partition["overlays"] = widget_info_dict["contents.partition"]["overlays"]
        if content_lists_expected.get("grouped",0) == 1: 
            contents_partition["grouped"] = widget_info_dict["contents.partition"]["grouped"]

        decimals_dict  = widget_info_dict['decimals'] 
        visible_dict   = widget_info_dict['visible']
        readonly_dict  = widget_info_dict['readonly'] 

        # Create the widget dictionary
        webui_widget_contents = {}
        webui_widget_contents["aimms.widget.type"] = { "literal": widget_type }
        if table_v2 and (is_scalar==0) and (widget_type in ('table', 'combinationchart')):
            # Get the list of v1 items.
            info_contents_dict = widget_info_dict["contents"]
            info_contents_aimms_dict = info_contents_dict["aimms"]
            contents_list = info_contents_aimms_dict["contents"]

            # When the references identifier is sliced by subsets, element parameters, or quoted elements, there is a "slices" list.
            if "slices" in info_contents_aimms_dict:
                has_slices = 1
                slices_list = info_contents_aimms_dict["slices"]
                no_slices = len( slices_list )
            else:
                has_slices = 0
                slices_list = []
                no_slices = 0

            # number of items; we need to loop (in parallel, several times over the number of items)
            no_content_items = len( contents_list ) 

            # Construct a display order list, just a reverse list of the contents (further specified below)
            web_display_order_list = []
            item_no = 1
            for item in contents_list: 
                item_reverse_no = item_no - 1 # no_content_items - item_no, test: w2w0014, w2w0002
                item_no += 1
                web_display_order_list.append(f"contents.{item_reverse_no}")
            webui_widget_contents["contents.__display_order__"] = { "literal" : web_display_order_list }

            # The display domain (if any) is shared by every content item in the table.
            displaydomain_info = widget_info_dict.get("contents.displaydomain")

            # Construct each identifier entry separately.
            item_no = 0
            for item in contents_list:
                identifier_name = item

                # The referenced identifier first.
                contents_identifier_key = f"contents.{item_no}.identifier"
                contents_identifier_slices = []
                # A freshly generated synthetic indicator Parameter (see
                # win_object_tools._substitute_set_indicator_reference /
                # gii_module.ensure_indicator_parameter) only exists as a queued text edit at
                # this point, not yet in the live AIMMS session - modeledit_aimmspy2.getDim/
                # getDomainIndex would report it as undeclared, so consult the known dimension
                # recorded when it was created first.
                synthetic_indices = gii_module.synthetic_domain_indices(gii_dict, self.comp_dict, identifier_name)
                if synthetic_indices is not None:
                    identifier_dim = len(synthetic_indices)
                else:
                    identifier_dim = modeledit_aimmspy2.getDim(aimms_model, identifier_name)

                slice_item_no = 0
                if has_slices:
                    while ( ( slice_item_no < no_slices                                   ) and
                            ( slices_list[slice_item_no]["identifier"] != identifier_name )     ):
                        slice_item_no += 1

                for index_no in range(identifier_dim):
                    arg_type = "free"
                    qualified_index_name = None
                    if slice_item_no < no_slices:
                        # win_object_tools.investigate_contents already worked out this exact
                        # position's own effective index (its own "index" key) - reuse it as-is
                        # rather than re-deriving independently below: a content reference can
                        # free-slice an identifier with a DIFFERENT, range-compatible Index than
                        # the identifier's own declared one (see
                        # win_object_tools.resolve_effective_index_name - a real RSC model does
                        # this), and re-deriving via getDomainIndex here would silently go back
                        # to the identifier's own (wrong, for this reference) declared index.
                        arguments_list_slice = slices_list[slice_item_no]["slice"]
                        arg_rec = arguments_list_slice[ index_no ]
                        qualified_index_name = arg_rec["index"]
                        arg_type = arg_rec["type"]
                        arg_name = arg_rec["value"]
                    if qualified_index_name is None:
                        if synthetic_indices is not None:
                            index_name = synthetic_indices[index_no]
                        else:
                            index_name = modeledit_aimmspy2.getDomainIndex(aimms_model, identifier_name, index_no + 1)
                        # A synthetic indicator Index (see gii_module.ensure_indicator_index)
                        # lives nested inside this component's own GeneratedInterfaceIdentifiers
                        # module - this "index" is evaluated from outside it (the widget's own
                        # content slice in webui.json), so a bare "i_indicator_s_u" doesn't
                        # resolve there, only the qualified "giim::i_indicator_s_u" does.
                        qualified_index_name = gii_module.qualify_synthetic_index(gii_dict, self.comp_dict, index_name)
                        arg_name = qualified_index_name
                    contents_identifier_slice_item = {
                        "index" : qualified_index_name,
                        "type"  : arg_type,
                        "value" : arg_name
                    }
                    contents_identifier_slices.append(contents_identifier_slice_item)
                content_identifier_literal = { 
                    "identifier" : identifier_name,
                    "slice"      : contents_identifier_slices
                }
                webui_widget_contents[contents_identifier_key] = { "literal" : content_identifier_literal }

                # A Combination Chart's own per-series chart type (e.g. "line" for a converted
                # WinUI curve, "column" for a converted WinUI bar chart, or a per-series mix of
                # "line"/"area" for a converted WinUI 2D Chart - see win_linechart.py/
                # win_barchart.py's content_lists_expected["chart_series_type"], a single value
                # shared by every content item since their own source WinUI object only ever
                # carries one; win_2dchart.py's own "chart_series_type_by_item" instead - keyed by
                # this same item_no, see its own docstring for why position rather than name - can
                # override that shared default per item, since a single WinUI 2D Chart can mix
                # chart types across its own series).
                if widget_type == 'combinationchart':
                    contents_chart_type_key = f"contents.{item_no}.chart.type"
                    chart_type_by_item = content_lists_expected.get("chart_series_type_by_item", {})
                    chart_type_value = chart_type_by_item.get(item_no, content_lists_expected.get("chart_series_type", "line"))
                    webui_widget_contents[contents_chart_type_key] = { "literal" : chart_type_value }

                # The display domain for this identifier (same literal for every item in the table).
                if displaydomain_info is not None:
                    contents_displaydomain_key = f"contents.{item_no}.displaydomain"
                    webui_widget_contents[contents_displaydomain_key] = { "literal" : displaydomain_info }

                # A Combination Chart's series has no per-item decimals/readonly/visibility
                # controls (confirmed against a hand-built reference widget - see
                # win_linechart.py/win_barchart.py) - only a "table" widget's own cells do.
                if widget_type == 'table':
                    # The number of decimals for this identifier
                    contents_numdecimals_key  = f"contents.{item_no}.numdecimals"
                    if identifier_name in decimals_dict:
                        decimals_entry = decimals_dict[identifier_name]
                        if decimals_entry == {}:
                            webui_widget_contents[contents_numdecimals_key] = { "literal" : 2 }
                        else:
                            is_literal_decimals = decimals_entry.get('literal',1)
                            if is_literal_decimals == 1:
                                webui_widget_contents[contents_numdecimals_key] = {
                                    "literal" :  decimals_entry.get('value',2)
                                }
                            else:
                                webui_widget_contents[contents_numdecimals_key] = {
                                    "aimms" :  {
                                        "contents" : [ decimals_entry.get('value','') ],
                                        "slices" : []
                                    }
                                }
                    else:
                        webui_widget_contents[contents_numdecimals_key] = { "literal" : 2 }

                    # Is that identifier read only?
                    contents_read_only_key  = f"contents.{item_no}.readonly"
                    if identifier_name in readonly_dict:
                        readonly_entry = readonly_dict[identifier_name]
                        if readonly_entry == {}:
                            webui_widget_contents[contents_read_only_key] = { "literal" : "Default" }
                        else:
                            is_literal_readonly = readonly_entry.get('literal',1)
                            if is_literal_readonly:
                                webui_widget_contents[contents_read_only_key] = {
                                    "literal" :  readonly_entry.get('value',0)
                                }
                            else:
                                webui_widget_contents[contents_read_only_key] = {
                                    "aimms" :  {
                                        "contents" : [ readonly_entry.get('value','') ],
                                        "slices" : []
                                    }
                                }
                    else:
                        webui_widget_contents[contents_read_only_key] = { "literal" : "Default" }

                    # Is that identifier visible?
                    contents_visibility_key = f"contents.{item_no}.visibility"
                    if identifier_name in visible_dict:
                        visibility_entry = visible_dict[identifier_name]
                        if visibility_entry == {}:
                            webui_widget_contents[contents_visibility_key] = { "literal" : "Default" }
                        else:
                            is_literal_visibility = visibility_entry.get('literal',1)
                            if is_literal_visibility:
                                webui_widget_contents[contents_visibility_key] = {
                                    "literal" :  visibility_entry.get('value',0)
                                }
                            else:
                                webui_widget_contents[contents_visibility_key] = {
                                    "aimms" :  {
                                        "contents" : [ visibility_entry.get('value','') ],
                                        "slices" : []
                                    }
                                }
                    else:
                        webui_widget_contents[contents_visibility_key] = { "literal" : "Default" }

                item_no += 1
        else:
            webui_widget_contents["contents"] = widget_info_dict["contents"]

        if is_scalar == 0:
            webui_widget_contents["contents.partition"] = { "literal": contents_partition }
            # A pivot with the identifier set on its rows and nothing on its columns (a list of
            # identifiers with a single value column) has no column header in WinUI; the WebUI
            # would show an empty one, headed "Identifier".
            if (table_v2 and widget_type == 'table' and content_lists_expected.get("colHeader",0) == 1
                    and not contents_partition["colHeader"]
                    and "<IDENTIFIER-SET>" in contents_partition.get("rowHeader", [])):
                webui_widget_contents["header.visibility"] = { "literal": "HIDE_COLUMN_HEADER" }
        webui_widget_contents["name"] = { "literal": widget_name }
        if widget_info_dict.get('store.focus.in','') != '':
            webui_widget_contents['store.focus.in'] = { "literal" : widget_info_dict['store.focus.in'] }
        webui_widget_contents["views"] = { "literal":  {} }
        if title:
            webui_widget_contents['title'] = { "literal": title }
        self._apply_widget_visibility(webui_widget_contents, visible_expr)
        # A checkbox-style Selection Object bound directly to a scalar Parameter (see
        # win_elemselec._resolve_scalar_parameter_identifier) is always compact - unlike
        # _mark_visibility_control_widgets_compact's cross-widget pass below, this doesn't
        # depend on the parameter also happening to drive some other widget's visibility.
        if content_lists_expected.get("compact"):
            webui_widget_contents['compact'] = { "literal": 1 }

        webui_widget = {
            "widgets/"+widget_name:  webui_widget_contents
        }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the data widget - the layout heuristic's if it placed one,
        # otherwise the old defaults ("area-a" of Layout10; scalars in area b, selectionbox in area c)
        if area is None:
            if inside_tabbed_widget:
                area = "area-a"
            elif is_scalar == 1:
                if content_lists_expected['objecttype'] in ('selectionbox-v2', 'multiselect'):
                    area = "area-c"
                else:
                    area = "area-b"
            else:
                area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name 

    def set_procedure_onload(self, webui_page_dict: dict, procname:str) -> None:
        """
        Set a procedure to be executed when the WebUI page is loaded.
        
        :param webui_page_dict: WebUI page specification to augment with the onload procedure.
        :type webui_page_dict: dict
        :param procname: Name of the AIMMS procedure to run on page load.
        :type procname: str
        :return: None. Updates the page dictionary with the onload configuration.
        :rtype: None
        """

        if self.comp_dict["Prefix"] == "":
            nameproc = procname
        else:
            nameproc = f"{self.comp_dict['Prefix']}::{procname}"
        webui_page_dict["onload"] = {
            "aimms": {
                "run": nameproc 
            }
        }
        self.data.update(webui_page_dict)

    def set_procedure_uponleave(self, webui_page_dict: dict, procname:str) -> None:
        """
        Set a procedure to be executed when the WebUI page is left.
        
        :param webui_page_dict: WebUI page specification to augment with the leave procedure.
        :type webui_page_dict: dict
        :param procname: Name of the AIMMS procedure to run on page leave.
        :type procname: str
        :return: None. Updates the page dictionary with the pageleave configuration.
        :rtype: None
        """

        if self.comp_dict["Prefix"] == "":
            nameproc = procname
        else:
            nameproc = f"{self.comp_dict['Prefix']}::{procname}"
        webui_page_dict["pageleave"] = {
            "aimms": {
                "run": nameproc 
            }
        }
        self.data.update(webui_page_dict)
    
