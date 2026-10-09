# Todo list for WinUI to WebUI conversion app

* Check if interface check can be avoided.
* aimms_slug - it is possible, and with SHARC it happens, that two different page names generate the same slug.
  This can be prevented by adding two dictionaries, such that, if a slug exists, but refers to a different page, a new slug is generated.
* icon bar
* menu bar
* discuss indices and annotations for webui, like Dex, set annotations shouls also be available to indices.
* debug: log to _conversion.md the names of the widgets generated.
* GeneratedInterfaceIdentifiers, should have the origin (component, page, purpose) as part of the comment.
* Buttons, why do they not have names? Shouldn't the expressions be converted?
* me::compile should be properly safeguarded
  * situation around identifiers outside library interface attribute should be recognized and properly reported.

## Data Widgets

* Read only
* Visibility
* UponChange
* Number of decimals per identifier (table v2)
* Data coloring (and legends) --> likely need CSS.
* upon click  / upon double click --> _conversion.md: remark it is not possible.

## Page objects not yet supported

* Floating Index
* Tabbed Page Object
* Navigation Object
* Selection Object
* 2D Chart
* Slider
* Indexed Page Object

## SHARC specific

* Handle Scalar object with more that 5 rows, and multiple columns as a WebUI table and use page open / page close to transfer the data to these scalars.
* Test if draw widget can handle a flowsheeter (with numerous scalars on the arcs)
