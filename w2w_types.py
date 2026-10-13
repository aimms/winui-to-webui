"""TypedDict definitions for the WinUI -> WebUI converter (named to avoid
conflict with the stdlib `types` module).
"""
from typing import Any, Dict

# Use simple Dict aliases instead of TypedDicts with invalid
# identifier keys (e.g. keys that contain dots). These aliases
# still help IDEs and mypy understand the general shape while
# avoiding syntax errors.
WidgetDict = Dict[str, Any]
PageDict = Dict[str, Any]
WebUIData = Dict[str, Any]
