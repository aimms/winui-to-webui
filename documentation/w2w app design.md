# Design of the w2w app

* The w2w app visits all pages mentioned in the PageManager.xml file of the main project, and of the libraries.
  * The WinUI page specification is an XML file.
  * The WebUI page specification is a json file.
  * Python is suited to handle these file types.
* Each WinUI page object, a corresponding WebUI object is created (if possible and relevant)
* To make meaningful conversions, the dimension and index domain of data identifiers needs to be known.  This information is obtained via pyaimms.
* When a single identifier is needed, for an expression or an action sequence, this identifier is generated in the runtime library GeneratedInterfaceIdentifiers.
