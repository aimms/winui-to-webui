# Layout heuristic

This heuristic is based on a discussion / brainstorm between Edo Nijmeijer and Chris Kuip on December 15, 2025.

Topic is to find a reasonable WebUI layout based on WinUI placement information of objects.

## Determining the WebUI Page Layout

A WebUI Layout is a grouping of cells in a grid.
The grid typically contains 2 to 4 rows, and 2 to 4 columns.
Even with a 4 by 4 grid, there are typically at most 4 or 5 areas, sometimes just 2 or  3 areas.

### In the presence of resize lines

When the WinUI features resize lines, these resize lines can form the basis of determining the grid,
and subsequently the layout to be used. Based on the first two or three resize lines, it should be
possible to determine the number of rows and columns in the grid that best fit this division.

The resulting areas define the grid layout to be used.
Subsequently, the objects can be placed accordingly.

### In the absence of resize lines

Not discussed is how to approach this question in the absence of resize lines.

For now the heuristic is to:

* Find the largest object
* Find the objects that are (almost) the same size
* Imagine resize lines around the area of these large objects
* If this is reasonable, use the heuristic of the previous section
* Otherwise, default to layout 10.
