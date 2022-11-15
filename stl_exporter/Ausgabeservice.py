import logging
import os

from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer

from OCC.Core.IFSelect import IFSelect_RetError
from OCC.Core.Interface import Interface_Static_SetCVal
from OCC.Core.STEPConstruct import stepconstruct_FindEntity
from OCC.Core.STEPControl import (STEPControl_AsIs, STEPControl_Writer)
from OCC.Core.TCollection import TCollection_HAsciiString
from OCC.Core.BRepPrimAPI import BRepPrimAPI_MakeBox
from OCC.Extend.DataExchange import read_step_file_with_names_colors


# stlapi.Write()

class exporter:
    def __init__(self):
        pass

    def write_stl_tigl(self, a_shape):
        import tigl3.exports
        exporter = tigl3.exports.create_exporter("stl")
        exporter.add_shape(a_shape)
        exporter.write("test.stl")

    def write_stl_file(self, a_shape, filename):
        from tigl3.exports import create_exporter
        '''
        if a_shape.IsNull():
            raise AssertionError("Shape is null.")
        if os.path.isfile(filename):
            print(f"Warning: {filename} already exists and will be replaced") 
        '''

        stl_exporter = create_exporter("stl")
        stl_exporter.add_shape(a_shape)
        # stl_exporter.write("test.stl")
        stl_exporter.write(filename + ".stl")

        if not os.path.isfile(filename):
            raise IOError("File not written to disk.")

    # deflection 0.01 feinmaschiger
    # angular_deflection = 0.01
    # linear deflection 0.003 dauert lange aber superglatt oberfläche
    def write_stl_file2(self, a_shape, filename, mode="ascii", linear_deflection=0.01, angular_deflection=0.05):
        mypath = "stls\\" + filename + ".stl"
        if a_shape.shape().IsNull():
            raise AssertionError("Shape is null.")
        if mode not in ["ascii", "binary"]:
            raise AssertionError("mode should be either ascii or binary")
        if os.path.isfile(mypath):
            print(f"Warning: {mypath} already exists and will be replaced")
        # first mesh the shape
        mesh = BRepMesh_IncrementalMesh(
            a_shape.shape(), linear_deflection, False, angular_deflection, True
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
        stl_exporter.Write(a_shape.shape(), mypath)

        if not os.path.isfile(mypath):
            raise IOError("File not written to disk.")

    def write_stls_from_list(self, list, plane_part="test"):
        for i, shape in enumerate(list):
            name = plane_part + str(i)
            logging.info(f"Exporting {name}")
            self.write_stl_file2(shape, name)

    def write_step_from_list(self, list, plane_part="test"):
        for i, shape in enumerate(list):
            name = plane_part + str(i)
            logging.info(f"Exporting {name}")
            self.write_step_file(shape, name)

    def write_step_file(self, shape, name):
        schema = 'AP203'
        assembly_mode = 1

        writer = STEPControl_Writer()
        fp = writer.WS().TransferWriter().FinderProcess()
        Interface_Static_SetCVal('write.step.schema', schema)
        Interface_Static_SetCVal('write.step.unit', 'M')
        Interface_Static_SetCVal('write.step.assembly', str(assembly_mode))

        components = [shape]
        comp_names = [name]
        for i, comp in enumerate(components):
            Interface_Static_SetCVal('write.step.product.name', comp_names[i])
            status = writer.Transfer(comp, STEPControl_AsIs)
            if int(status) > int(IFSelect_RetError):
                raise Exception('Some Error occurred')

            # This portion is not working as I hoped
            item = stepconstruct_FindEntity(fp, comp)
            if not item:
                raise Exception('Item not found')

            item.SetName(TCollection_HAsciiString(comp_names[i]))
            logging.info(f"Writing {name} STEP")
            status = writer.Write(name + ".stp")
            if int(status) > int(IFSelect_RetError):
                raise Exception('Something bad happened')
