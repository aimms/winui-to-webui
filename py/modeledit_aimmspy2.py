from typing import List, Dict, Tuple, Any, Union # Add Tuple and any other types you use

import os
# Import ingredients from aimmspy.
from aimmspy.project.project import Project, Model
from aimmspy.utils import find_aimms_path
import converter_logging

import modeledit_aimmspy
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from modeledit_aimmspy import Model

def getAttribute(aimms_model: Model, id: str, attr: str) -> str:
    """
    Retrieve the text of attribute `attr` for identifier `id` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :param attr: Attribute name (must exist in `AllAttributeNames`).
    :type attr: str
    :return: Text value of the requested attribute.
    :rtype: str
    """
    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.sp_attrName.assign(attr)
    aimms_model.meap.pr_attributeToString()
    sp_attrText = str(aimms_model.meap.sp_attrText.data())

    return sp_attrText

def isSubset(aimms_model: Model, subset:str, superset: str) -> int:
    """
    Determine whether `subset` is declared as a subset of `superset` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param subset: Name of the potential subset.
    :type subset: str
    :param superset: Name of the candidate superset.
    :type superset: str
    :return: 1 when `subset` is a subset of `superset`, otherwise 0.
    :rtype: int
    """
    aimms_model.meap.sp_subsetName.assign(subset)
    aimms_model.meap.sp_superSetName.assign(superset)
    aimms_model.meap.pr_declaredSubset()
    f_is_subset = float(aimms_model.meap.bp_isSubset.data())
    i_is_subset = int(f_is_subset)

    return i_is_subset

def getDomainIndex(aimms_model: Model, id:str, indexPos:int) -> str:
    """
    Return the domain index name at position `indexPos` for identifier `id` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :param indexPos: One-based position of the domain index.
    :type indexPos: int
    :return: Name of the domain index at the requested position.
    :rtype: str
    """
    indexName: str

    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.p_indexPos.assign(float(indexPos))
    aimms_model.meap.pr_domainIndex()
    indexName = str(aimms_model.meap.sp_indexName.data())

    return indexName

def getDim(aimms_model: Model, id:str) -> int:
    """
    Return the dimension of identifier `id` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :return: Dimension of the identifier as an integer.
    :rtype: int
    """
    d_f: float
    d_i: int

    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.pr_getDim()
    d_f = float(aimms_model.meap.p_dim.data())
    d_i = int(d_f)

    return d_i 

def getIdentifierElementRange(aimms_model: Model, id:str)-> str:
    """
    Return the set name that forms the element range of identifier `id`; return an empty string when none exists.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :return: Name of the element range set or an empty string if undefined.
    :rtype: str
    """
    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.pr_getDim()
    sp_elementRange = str(aimms_model.meap.sp_elementRange.data())

    return sp_elementRange

def getText(aimms_model: Model, id:str) -> str:
    """
    Return the textual contents of identifier `id` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :return: Text associated with the identifier.
    :rtype: str
    """
    t_s: str

    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.pr_getText()
    t_s = str(aimms_model.meap.sp_text.data())

    return t_s



def getType(aimms_model: Model, id:str) -> str:
    """
    Return the type of identifier `id` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :return: Identifier type as reported by the AIMMS model.
    :rtype: str
    """
    t_s: str

    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.pr_getType()
    t_s = str(aimms_model.meap.sp_type.data())

    return t_s

def getIndexRange(aimms_model: Model, id:str) -> str:
    """
    Return the declared range of index `id` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Index name in the AIMMS model.
    :type id: str
    :return: Name of the index range set.
    :rtype: str
    """
    ir_s: str

    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.pr_getIndexRange()
    ir_s = str(aimms_model.meap.sp_indexRange.data())

    return ir_s

def doCompile(aimms_model: Model, id:str) -> None:
    """
    Compile identifier `id` within the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name to compile.
    :type id: str
    :return: None. Triggers compilation inside the AIMMS model.
    :rtype: None
    """
    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.pr_compile()
    errorstring = str(aimms_model.meap.sp_compilermessage.data())
    if errorstring != '':
        converter_logging.lines([f"compiling {id} resulted in error:","",errorstring])

def create(aimms_model: Model, id:str, type:str, parent:str, pos:int) -> str:
    """
    Create identifier `id` of type `type` under parent `parent` at position `pos` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Name of the identifier to create.
    :type id: str
    :param type: Identifier type to create.
    :type type: str
    :param parent: Parent identifier name.
    :type parent: str
    :param pos: Position within the parent where the identifier should be inserted.
    :type pos: int
    :return: Name of the created identifier returned by AIMMS.
    :rtype: str
    """
    aimms_model.meap.sp_newIdName.assign(id)
    aimms_model.meap.sp_newIdType.assign(type)
    aimms_model.meap.sp_newIdParent.assign(parent)
    aimms_model.meap.p_newIdPos.assign(float(pos))
    aimms_model.meap.pr_create()

    r_s: str = str(aimms_model.meap.sp_createdId.data())

    return r_s

def createLibrary(aimms_model: Model, lib_name:str, prefix_name:str) -> str:
    """
    Create a library named `lib_name` with prefix `prefix_name` in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param lib_name: Name of the library to create.
    :type lib_name: str
    :param prefix_name: Prefix assigned to the library.
    :type prefix_name: str
    :return: Name of the created library as returned by AIMMS.
    :rtype: str
    """
    aimms_model.meap.sp_libraryName.assign(lib_name)
    aimms_model.meap.sp_prefixName.assign(prefix_name)
    aimms_model.meap.pr_createLibrary()

    r_s: str = str(aimms_model.meap.sp_createdLibrary.data())

    return r_s

def exportNode(aimms_model: Model, id:str, filepath:str) -> None:
    """
    Export node `id` from the AIMMS model to the specified file path.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name to export.
    :type id: str
    :param filepath: Target file path for the exported node.
    :type filepath: str
    :return: None. Writes the node contents to disk via AIMMS.
    :rtype: None
    """
    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.sp_exportFilename.assign(filepath)
    aimms_model.meap.pr_exportNode()    

def setAttributeText(aimms_model: Model, id:str, attr:str, text:str) -> None:
    """
    Set attribute `attr` of identifier `id` in the AIMMS model to the provided text.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :param attr: Attribute name to update (element of `AllAttributeNames`).
    :type attr: str
    :param text: Text value to assign to the attribute.
    :type text: str
    :return: None. Updates the attribute text inside the AIMMS model.
    :rtype: None
    """
    aimms_model.meap.sp_id.assign(id)
    aimms_model.meap.sp_attrName.assign(attr)
    aimms_model.meap.sp_attrText.assign(text)
    aimms_model.meap.pr_setAttribute()


###################################################################################################

#  Utility functions based on the above basic functions.

def isScalarElementParameter(aimms_model:Model, id:str) -> int:
    """
    Determine whether identifier `id` is a scalar element parameter in the AIMMS model.
    
    :param aimms_model: Handle to the aimmspy-created link to the AIMMS model.
    :type aimms_model: Model
    :param id: Identifier name in the AIMMS model.
    :type id: str
    :return: 1 when `id` is a scalar element parameter, otherwise 0.
    :rtype: int
    """
    is_sep: int

    if ( getDim(aimms_model, id) == 0 ) and ( getType(aimms_model, id) == 'element parameter' ):
        is_sep = 1
    else:
        is_sep = 0

    return is_sep
