# Detailed differences between WinUI and WebUI

For now, the following list is unordered.

## WinUI scalar widget

* Heavily used in SHARC/FCC:
  * WinUI: Able to refer to .lower, or .upper.
  * WinUI: Even able to refer to .[lower, .level, .upper]

## Overlapping objects

This is possible in WinUI, but not in WebUI.
Many applications use this feature, but using CSS in WebUI is better.

## WinUI features

Overlapping objects, nice for backgrounds, images on buttons, ...

Pivot tables rely on so-called state files. Binary, AIMMS specific.

Icon bar and Menu bar in Windows app style.

Ability to refer to the suffices of a variable

## WebUI features

Workflow, status bar, side panels, page menu
