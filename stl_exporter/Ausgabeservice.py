import logging
import os

from OCC.Core.IMeshTools import IMeshTools_Parameters
from OCC.Core.BRepMesh import BRepMesh_IncrementalMesh
from OCC.Core.StlAPI import StlAPI_Writer
import tigl3.geometry as TGeo
from pathlib import Path
import OCC.Core.TopoDS as OTopo

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

    def write_stl_file2(self, named_shape: TGeo.CNamedShape, filename, mode="ascii", linear_deflection=0.00002):

        export_folder = Path(__file__).parent.parent / "stls"
        # creates folder if it does not exist
        export_folder.mkdir(parents=True, exist_ok=True)
        filepath = export_folder / f"{named_shape.name()}.stl"

        # getting the absolute path of the file that is to be exported
        abs_filepath = filepath.absolute()

        # parameter validation
        if not OTopo.TopoDS_Iterator(named_shape.shape()).More():
            raise AssertionError("Shape cannot be null.")
        if mode not in ["ascii", "binary"]:
            raise AssertionError("Mode should be either 'ascii' or 'binary'.")
        if os.path.isfile(filepath):
            print(f"Warning: {filepath} already exists and will be replaced.")

        # turning the shape into a mesh of triangles
        params = IMeshTools_Parameters()
        params.Deflection = linear_deflection
        params.InParallel = True
        params.AllowQualityDecrease = False

        mesh = BRepMesh_IncrementalMesh(named_shape.shape(), params)

        mesh.Perform()
        if not mesh.IsDone():
            raise AssertionError("Mesh is not done.")

        # creating an STL exporter instance
        stl_exporter = StlAPI_Writer()

        # setting the STL exporter mode
        if mode == "ascii":
            stl_exporter.SetASCIIMode(True)
        else:  # binary, just set the ASCII flag to False
            stl_exporter.SetASCIIMode(False)

        # writing the STL data to a file
        stl_exporter.Write(named_shape.shape(), str(abs_filepath))

        if not os.path.isfile(abs_filepath):
            raise IOError("File not written to disk.")

    def write_stls_from_list(self, list, plane_part="test"):
        for i, named_shape in enumerate(list):
            logging.info(f"Exporting {named_shape.name()}")
            self.write_stl_file2(named_shape, named_shape.name())
