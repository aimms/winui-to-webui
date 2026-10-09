# Nirvana project 0287 - Extend an AIMMS WinUI app with a WebUI

Nobody wants to create a program that is to be used only once.  *)

My name is nobody.

*) Well, that is, once per WinUI project.

## Complete tests

uv venv
.venv\Scripts\Activate
uv pip install -r .\requirements.txt
uv run main.py
.\scripts\run_all_examples.ps1
.venv/Scripts/python.exe -m mypy --ignore-missing-imports .

## Commands for development

Init development

uv venv
.venv\Scripts\Activate
then
uv sync
or
uv pip install -r .\requirements.txt

run UI:

uv run main.py
and fill in the project folder, and name of AIMMS app, press button.

run CLI (Headless):

uv run main.py "..\w2w0004\work" w2w0004
del "..\w2w0006\work\MainProject\WebUI\webui.json"
uv run main.py "..\w2w0006\work" w2w0006
(project folder, aimms app).

run a typechecker (mypy)
.venv/Scripts/python.exe -m mypy --ignore-missing-imports .

Build executable
pyinstaller --onefile --noconsole --name WinUIToWebUI main.py

Testing using pytest:
pytest -vv --maxfail=1 test_winui_to_webui.py

Testing:
  Run all examples:
  PowerShell: run_all_examples.ps1

  Run specific examples:
  .[run_all_examples.ps1](http://_vscodecontentref_/1) -Examples w2w0001,w2w0000

  Stop on first failure:
  .[run_all_examples.ps1](http://_vscodecontentref_/2) -StopOnFailure

  Where logs go:
  Per-example logs are written to logs/<example>-YYYYMMDD-HHMMSS.txt.

## Todo list

Character used for done: ✅
Character used for declined: ✗

- [✅] AIMMS Library MEAP, extend and in git.
- [✅] Title of identifier / UI Expressions
- [✅] Domain of identifier (sub element of Explicit_Identifier)image buttons to buttons
- [ ] tabbed pages
- [ ] filters: checkboxes
- [✅] explicit identifiers as expressions (low prio)
- [ ] explicit identifiers with slices either subsets or element parameters etc.
- [ ] explicit identifier title element 
- [ ] explicit identifier domain element 
- [ ] explicit identifier is hidden element 
- [ ] explicit identifier readonly element 
- [ ] explicit identifier on change procedure element 
- [ ] explicit identifier on double-click procedure element 

## Building exe's

build them using:
pip install -e .

Find them w2w_main, w2w_cli, and w2w_gui in .venv/Scripts

## Data structures used

Changes that may need repetition:
The following is added to the end of modeledit_aimmspy2.pyi by ChatGPT.

# -- Python helper function signatures (implemented in modeledit_aimmspy2.py)
# Expose these to the type checker so IDEs like Pylance recognize attributes such as `getDim`.

def initialize_aimms_model( am_pn:str) -> Model: ...
def getDomainIndex(aimms_model: Model, id: str, indexPos: int) -> str: ...
def getDim(aimms_model: Model, id: str) -> int: ...
def getIdentifierElementRange(aimms_model: Model, id: str) -> str: ...
def getText(aimms_model: Model, id: str) -> str: ...
def getType(aimms_model: Model, id: str) -> str: ...
def getIndexRange(aimms_model: Model, id: str) -> str: ...
def doCompile(aimms_model: Model, id: str) -> None: ...
def create(aimms_model: Model, id: str, type: str, parent: str, pos: int) -> str: ...
def createLibrary(aimms_model: Model, lib_name: str, prefix_name: str) -> str: ...
def exportNode(aimms_model: Model, id: str, filepath: str) -> None: ...
def setAttributeText(aimms_model: Model, id: str, attr: str, text: str) -> None: ...
def isScalarElementParameter(aimms_model: Model, id: str) -> int: ...


### WinUI

The WinUI is specified in: 
- MainProject/Pagemanager.xml the tree structure
- MainProject/Pages/*.xml the pages

### WebUI

#### webui.json file

A big dictionary, with the following members:

Application/pages: a hierachy of pages.  Corresponding to the WinUI Pagemanager tree.

At the end: A mixed list of pages and widgets, more or less in creation order.

#### A WebUI page


#### A WebUI widget:

##### Contents.partition

Each data widget may contain a contents.partition - this specifies the pivoting of the indices used.

There is an artificial index called `<IDENTIFIER-SET>`, it varies over the identifier names visualized in the widget.
The other indices are the indices used in the identifiers visualized in the widget.
This pivoting is maintained in several lists, and the exact lists depend on the data widget type used.

Table:
- rowHeader
- colHeader
- aggregated

Linechart:
- header 
- stacked
- overlays
- aggregated

Barchart:
- header  
- grouped
- stacked
- aggregated

For now, use following pivoting: 
- either use colHeader or header
- either use rowHeader, overlays, or grouped.
- barchart, linechart: indices to header.
- table: 
- Single identifier:
  - table: identifier to aggregated.
    split indices, last index to colHeader, 
    other indices to rowHeader
  - linechart: identifier to aggregated.
  - barchart: identifier to aggregated.
- Multiple identifiers:
  - table: identifiers over the columns.
  - linechart: identifiers to the overlays.
  - barchart: identifiers to the grouped.


