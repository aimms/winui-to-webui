"""TypedDict definitions for the WinUI -> WebUI converter.

Keep these types lightweight — they are only used for static checking and
IDE assistance. Runtime continues to use plain dicts.
"""
from typing import Any, Dict

# Use simple Dict aliases instead of TypedDicts with invalid
# identifier keys (e.g. keys that contain dots). These aliases
# still help IDEs and mypy understand the general shape while
# avoiding syntax errors.
WidgetDict = Dict[str, Any]
PageDict = Dict[str, Any]
WebUIData = Dict[str, Any]
