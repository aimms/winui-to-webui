# Converts a WinUI picture object to a WebUI image widget.

from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use
#from lxml import etree as ET
import lxml.etree as ET

import web_page
import win_object_tools
from aimmspy.project.project import Project, Model
import os
import pathlib
import converter_logging
import shutil

def winpage_picture(webui: web_page.WebUI, aimms_model: Model, gii_dict: dict, component_dict:dict, webui_page_dict: dict, page_name: str, winui_picture_xml:ET.Element, ancestor_info:dict) -> None:
    """
    Convert a WinUI picture object into a WebUI image widget and attach it to the target page.
    
    :param webui: Helper used to build and store WebUI data.
    :type webui: web_page.WebUI
    :param aimms_model: AIMMS model handle used for compatibility with other converters.
    :type aimms_model: Model
    :param gii_dict: Runtime library dictionary produced during conversion.
    :type gii_dict: dict
    :param component_dict: Metadata describing the current component being converted.
    :type component_dict: dict
    :param webui_page_dict: WebUI page dictionary to which the widget will be added.
    :type webui_page_dict: dict
    :param page_name: Name of the page being processed.
    :type page_name: str
    :param winui_picture_xml: XML element representing the WinUI picture definition.
    :type winui_picture_xml: ET.Element
    :param ancestor_info: Metadata describing properties of the ancestor, for instance if it has a tabbed widget.
    :type ancestor_info: dict
    :return: None. Copies literal images when possible and generates widget data.
    :rtype: None
    """
    
    info_dict: dict[str, Any] = {}
    for picture_child in winui_picture_xml:
        if picture_child.tag == 'FileName':
            literal_picture = str(picture_child.text)
            # if literal_picture.find('BackgroundCover') >= 0:
            #     dummy = 1
            if len(literal_picture) > 2 and literal_picture[0] == '"' and literal_picture[-1] == '"':
                literal_picture = literal_picture[1:-1]
            if len(literal_picture) > 7:
                if literal_picture[:6] == '<prj>:':
                    literal_picture = 'MainProject\\User Files\\' + literal_picture[6:]
                if literal_picture[:5]  == '<lib:':
                    start_rest = literal_picture.find('>:')
                    if start_rest > 0:
                        literal_picture = component_dict['Path'] + '\\User Files\\' + literal_picture[start_rest+2:]

            is_literal_picture = str(picture_child.get('LiteralFileName'))
            is_literal = 0
            if ( is_literal_picture == 'true' ) or ( is_literal_picture == '1' ):
                is_literal = 1

            # Ensure the folder WebUI/resources/images exists for the current component.
            dest_folder_name = os.path.join( component_dict['Path'], 'WebUI', 'resources', 'images' )
            dest_folder_path = pathlib.Path(dest_folder_name)
            if not dest_folder_path.exists():
                dest_folder_path.mkdir(parents=True)

            # A wonderful feature of the image widget is that it takes the images only from the WebUI/resources/images folder.
            if is_literal:
                picture_path = pathlib.Path(literal_picture)
                if picture_path.exists():
                    shutil.copy2(literal_picture, dest_folder_name)
                    literal_picture = picture_path.name 
                else:
                    converter_logging.exoticW([
                        f"Picture object on {page_name} uses {literal_picture}.  But this image does not exist"],
                        component_dict, "purpose: picture", page_name)
            else:
                converter_logging.exoticW([
                    f"A Picture object uses model identifier {literal_picture}.",
                    "The WebUI image widget only uses images stored in the folder WebUI/resources/images.",
                    f"Please ensure the {literal_picture} [references a file in that folder](https://documentation.aimms.com/webui/image-widget.html#image-widget), and that the corresponding image is also stored there."],
                    component_dict, "picture", page_name)

            # Use when using the image widget:
            info_dict["LiteralPicture"] = literal_picture
            info_dict["IsLiteral"] = is_literal

            # Use when using the iframe widget:
            # info_dict["LiteralText"] = literal_picture
            # info_dict["IsLiteral"] = is_literal

    if info_dict != {}:
        webui.add_image_widget(webui_page_dict, info_dict)
        # webui.add_iframe_widget(webui_page_dict, info_dict)
