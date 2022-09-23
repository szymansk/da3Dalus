import os

from OCC.Core.TopoDS import TopoDS_Shape
from OCC.Core.TopAbs import TopAbs_SOLID, TopAbs_SHELL, TopAbs_COMPOUND
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import stlapi_Read, StlAPI_Writer
from OCC.Core.BRep import BRep_Builder
from OCC.Core.gp import gp_Pnt, gp_Dir, gp_Pnt2d
from OCC.Core.Bnd import Bnd_Box2d
from OCC.Core.TopoDS import TopoDS_Compound
from OCC.Core.IGESControl import (IGESControl_Controller,IGESControl_Reader,IGESControl_Writer,)
from OCC.Core.STEPControl import (STEPControl_Reader,STEPControl_Writer,STEPControl_AsIs,)
from OCC.Core.Interface import Interface_Static_SetCVal
from OCC.Core.IFSelect import IFSelect_RetDone, IFSelect_ItemsByEntity
from OCC.Core.TDocStd import TDocStd_Document
from OCC.Core.XCAFDoc import (XCAFDoc_DocumentTool_ShapeTool,XCAFDoc_DocumentTool_ColorTool,)
from OCC.Core.STEPCAFControl import STEPCAFControl_Reader
from OCC.Core.TDF import TDF_LabelSequence, TDF_Label
from OCC.Core.TCollection import TCollection_ExtendedString
from OCC.Core.Quantity import Quantity_Color, Quantity_TOC_RGB
from OCC.Core.TopLoc import TopLoc_Location
from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_Transform

from OCC.Extend.TopologyUtils import (discretize_edge,get_sorted_hlr_edges,list_of_shapes_to_compound,)



class ausgabe:
    def write_stl_tigl(self,a_shape):
        import tigl3.exports
        exporter = tigl3.exports.create_exporter("stl")
        exporter.add_shape(a_shape)
        exporter.write("test.stl")

    def write_stl_file(self,a_shape,filename):
        from tigl3.exports import create_exporter, IgesShapeOptions
        '''
        if a_shape.IsNull():
            raise AssertionError("Shape is null.")
        if os.path.isfile(filename):
            print(f"Warning: {filename} already exists and will be replaced") 
        '''

        stl_exporter = create_exporter("stl")
        stl_exporter.add_shape(a_shape)
        #stl_exporter.write("test.stl")
        stl_exporter.write(filename +".stl")

        if not os.path.isfile(filename):
            raise IOError("File not written to disk.")

#deflection 0.01 feinmaschiger
#angular_deflection = 0.9
#linear deflection 0.003 dauert lange aber superglatt oberfläche
def write_stl_file2(a_shape,filename,mode="ascii",linear_deflection=0.03,angular_deflection=0.01):
    mypath= "stls\\" + filename
    if a_shape.IsNull():
        raise AssertionError("Shape is null.")
    if mode not in ["ascii", "binary"]:
        raise AssertionError("mode should be either ascii or binary")
    if os.path.isfile(mypath):
        print(f"Warning: {mypath} already exists and will be replaced")
    # first mesh the shape
    mesh = BRepMesh_IncrementalMesh(
        a_shape, linear_deflection, False, angular_deflection, True
    )
    # mesh.SetDeflection(0.05)
    mesh.Perform()
    if not mesh.IsDone():
        raise AssertionError("Mesh is not done.")

    stl_exporter = StlAPI_Writer()
    if mode == "ascii":
        stl_exporter.SetASCIIMode(True)
    else:  # binary, just set the ASCII flag to False
        stl_exporter.SetASCIIMode(False)
    stl_exporter.Write(a_shape, mypath)
    

    if not os.path.isfile(mypath):
        raise IOError("File not written to disk.")

def write_stls_srom_list(list):
    for i,shape in enumerate(list):
        name= "fuselage\\fuselage" + str(i) + ".stl"
        write_stl_file2(shape, name)