from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
from web_page_types import WebUIData  # type: ignore
import json
import pathlib
import tools
from aimmspy.project.project import Project, Model
import modeledit_aimmspy
import modeledit_aimmspy2

"""
This module defines the WebUI class to manage AIMMS WebUI specifications.   
It provides methods to create pages and widgets within the WebUI structure. 
"""

# Switching to table v2
table_v2 = 1

# WinUI object do not have names. 
# WebUI widgets need unique names.
# Thus we will construct unique names by numbering the widgets sequentially.
# Global variable to keep track of widget numbering
widget_number = 1
def get_next_widget_number() -> int:
    """
    Return the next unique widget number and increment the global counter for widget naming.
    
    :return: Sequential widget number for constructing unique widget names.
    :rtype: int
    """
    global widget_number
    widget_number += 1
    return widget_number 

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

    def get_data(self) -> dict:
        """
        Return the entire WebUI data dictionary managed by the helper.
        
        :return: WebUI data structure to be serialized to JSON.
        :rtype: dict
        """
        return self.data

    def get_root_page(self) -> dict:
        """
        Return a handle to the root page dictionary in the pages tree.
        
        :return: Root page dictionary from the WebUI pages tree.
        :rtype: dict
        """
        return self.data["application"]["pages"]["literal"]["children"][0]

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
        pages_tree = page_parent["children"]
        in_list = 0
        for existing_page in pages_tree:
            if existing_page["slug"] == page_slug:
                in_list = 1
                pages_tree_dict = existing_page
                break
        if in_list == 0:
            if self.comp_dict["Prefix"] == "":
                page_slug = page_slug
            else:
                page_slug = self.comp_dict["Prefix"] + "::" + page_slug
            pages_tree_entry = {
                "name": page_name,
                "type": "pagev2-grid",
                "slug": page_slug,
                "children": []
            }
            pages_tree.append(pages_tree_entry)
            pages_tree_dict = pages_tree_entry

        return pages_tree_dict
                           
    def add_page_to_pages_list(self,page_slug:str, ancestor_info:dict) -> dict:
        """
        Create a WebUI page dictionary in the pages list and return a handle to it.
        
        :param page_slug: Slug identifier for the page to be created.
        :type page_slug: str
        :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
        :type ancestor_info: dict
        :return: Page dictionary suitable for attaching widgets.
        :rtype: dict
        """

        pagename = "pages/"+page_slug

        # Choose layout of page.
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

    def add_button_widget(self, webui_page_dict:dict, widget_info_dict:dict) -> str:
        """
        Create a WebUI button widget and add it to the provided page definition.
        
        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the button action and title.
        :type widget_info_dict: dict
        :return: Name assigned to the created button widget.
        :rtype: str
        """

        # Use the global widget_number to ensure unique widget names
        widget_number = get_next_widget_number()
        widget_type = "button"
        widget_name = f"{widget_type}_{widget_number}"

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
        if the_button_title == '':
            the_button_title = widget_name
        webui_widget_details['title'] = { "literal": the_button_title }

        webui_widget = { "widgets/"+widget_name: webui_widget_details }
            
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the button widget (for now buttons are presented in "area-d" of Layout10)
        area = "area-d"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_text_widget(self, webui_page_dict:dict, widget_info_dict:dict) -> str:
        """
        Create a WebUI text widget and add it to the provided page definition.
        
        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the content and literal handling for the text widget.
        :type widget_info_dict: dict
        :return: Name assigned to the created text widget.
        :rtype: str
        """

        # Use the global widget_number to ensure unique widget names
        widget_number = get_next_widget_number()
        widget_type = "text"
        widget_name = f"{widget_type}_{widget_number}"

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
        webui_widget = { 
            "widgets/"+widget_name: {
                "aimms.widget.type": {
                    "literal": widget_type
                },
                "contents":content_dict,
                "name": {
                    "literal": widget_name     
                } 
            }
        }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the text widget (for now texts are presented in "area-a" of Layout10)
        area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_iframe_widget(self, webui_page_dict:dict, widget_info_dict:dict) -> str:
        """
        Create a WebUI iframe widget and add it to the provided page definition.
        
        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the iframe contents and literal handling.
        :type widget_info_dict: dict
        :return: Name assigned to the created iframe widget.
        :rtype: str
        """

        # Use the global widget_number to ensure unique widget names
        widget_number = get_next_widget_number()
        widget_type = "iframe"
        widget_name = f"{widget_type}_{widget_number}"

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
        webui_widget = { 
            "widgets/"+widget_name: {
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
        }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the text widget (for now texts are presented in "area-a" of Layout10)
        area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_image_widget(self, webui_page_dict:dict, widget_info_dict:dict) -> str:
        """
        Create a WebUI image widget and add it to the provided page definition.
        
        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the image contents and literal handling.
        :type widget_info_dict: dict
        :return: Name assigned to the created image widget.
        :rtype: str
        """

        # Use the global widget_number to ensure unique widget names
        widget_number = get_next_widget_number()
        widget_type = "image"
        widget_name = f"{widget_type}_{widget_number}"

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
        webui_widget = { 
            "widgets/"+widget_name: {
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
        }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the text widget (for now texts are presented in "area-a" of Layout10)
        area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_tabbed_widget(self, webui_page_dict:dict, widget_info_dict:dict, ancestor_info:dict) -> str:
        """
        Create a tabbed widget
        
        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the widget contents and partitioning.
        :type widget_info_dict: dict
        :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
        :type ancestor_info: dict
        :return: Name assigned to the created data widget.
        :rtype: str
        """

        # Use the global widget_number to ensure unique widget names
        widget_number = get_next_widget_number()
        widget_type = "tabbedpages"
        widget_name = f"{widget_type}_{widget_number}"

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

        webui_widget = { 
            "widgets/"+widget_name:  webui_widget_contents  
        }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the data widget (for now data widgets are presented in "area-a" of Layout10)
        # scalars in area b, selectionbox in area c.
        area = "area-a"
        self.update_page_dict( webui_page_dict, area, widget_name)

        return widget_name

    def add_data_widget(self, aimms_model: Model, webui_page_dict:dict, widget_info_dict:dict, content_lists_expected:dict, ancestor_info:dict) -> str:
        """
        Create a data-oriented WebUI widget (table, scalar, or selection box) and add it to the provided page definition.
        
        :param webui_page_dict: WebUI page specification to which the widget will be added.
        :type webui_page_dict: dict
        :param widget_info_dict: Input data describing the widget contents and partitioning.
        :type widget_info_dict: dict
        :param content_lists_expected: Flags indicating which content partitions are expected for the widget type.
        :type content_lists_expected: dict
        :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
        :type ancestor_info: dict
        :return: Name assigned to the created data widget.
        :rtype: str
        """

        inside_tabbed_widget = ancestor_info.get('has_tabbed_widget',0)

        if content_lists_expected['objecttype'] == 'scalar' or content_lists_expected['objecttype'] == 'selectionbox-v2':
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

        # Use the global widget_number to ensure unique widget names
        widget_number = get_next_widget_number()
        if widget_number == 3:
            dummy = 1
        widget_name = f"{widget_type}_{widget_number}"

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
        if widget_number == 5:
            dummy = 1
        webui_widget_contents = {}
        webui_widget_contents["aimms.widget.type"] = { "literal": widget_type }
        if table_v2 and (is_scalar==0) and (widget_type=='table'):
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
 
            # Construct each identifier entry separately.
            item_no = 0
            for item in contents_list:
                identifier_name = item

                # The referenced identifier first.
                contents_identifier_key = f"contents.{item_no}.identifier"
                contents_identifier_slices = []
                identifier_dim = modeledit_aimmspy2.getDim(aimms_model, identifier_name)
                
                slice_item_no = 0
                if has_slices:
                    while ( ( slice_item_no < no_slices                                   ) and 
                            ( slices_list[slice_item_no]["identifier"] != identifier_name )     ):
                        slice_item_no += 1

                for index_no in range(identifier_dim):
                    index_name = modeledit_aimmspy2.getDomainIndex(aimms_model, identifier_name, index_no + 1)
                    arg_type = "free"
                    arg_name = index_name
                    if slice_item_no < no_slices:
                        arguments_list_slice = slices_list[slice_item_no]["slice"]
                        arg_rec = arguments_list_slice[ index_no ]
                        arg_type = arg_rec["type"]
                        arg_name = arg_rec["value"]
                    contents_identifier_slice_item = { 
                        "index" : index_name,
                        "type"  : arg_type,
                        "value" : arg_name
                    }
                    contents_identifier_slices.append(contents_identifier_slice_item)
                content_identifier_literal = { 
                    "identifier" : identifier_name,
                    "slice"      : contents_identifier_slices
                }
                webui_widget_contents[contents_identifier_key] = { "literal" : content_identifier_literal }

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

        if widget_info_dict.get("contents.displaydomain") is not None:
            webui_widget_contents["contents.displaydomain"] = widget_info_dict["contents.displaydomain"]    
        if is_scalar == 0:
            webui_widget_contents["contents.partition"] = { "literal": contents_partition }
        webui_widget_contents["name"] = { "literal": widget_name }
        if widget_info_dict.get('store.focus.in','') != '':
            webui_widget_contents['store.focus.in'] = { "literal" : widget_info_dict['store.focus.in'] }
        webui_widget_contents["views"] = { "literal":  {} }
        
        webui_widget = { 
            "widgets/"+widget_name:  webui_widget_contents  
        }
        # Also add the widget to the main data dictionary
        self.data.update(webui_widget)

        # pick a grid area for the data widget (for now data widgets are presented in "area-a" of Layout10)
        # scalars in area b, selectionbox in area c.
        if inside_tabbed_widget:
            area = "area-a"
        elif is_scalar == 1:
            if content_lists_expected['objecttype'] == 'selectionbox-v2':
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
    
