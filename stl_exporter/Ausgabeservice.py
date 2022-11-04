import logging
import os

from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer


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
        mypath = "stls\\" + filename
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

    def write_stls_from_list(self, list, plane_part="test"):
        for i, shape in enumerate(list):
            name = plane_part + str(i) + ".stl"
            logging.info(f"Exporting {name}")
            self.write_stl_file2(shape, name)
