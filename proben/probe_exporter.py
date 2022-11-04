from math import *

import OCC.Core.BRepAlgoAPI as OAlgo
import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

from Dimensions.ShapeDimensions import ShapeDimensions
from Extra.mydisplay import myDisplay
# import stl_exporter.Ausgabeservice as stlexp
from _alt.Wand_erstellen import *


def rotate_shape(shape, axis, angle):
    """Rotate a shape around an axis, with a given angle.
    @param shape : the shape to rotate
    @point : the origin of the axis
    @vector : the axis direction
    @angle : the value of the rotation
    @return: the rotated shape.
    """
    # assert_shape_not_null(shape)
    # if unite == "deg":  # convert angle to radians
    angle = radians(angle)
    trns = Ogp.gp_Trsf()
    trns.SetRotation(axis, angle)
    brep_trns = OBui.BRepBuilderAPI_Transform(shape, trns, False)
    brep_trns.Build()
    shp = brep_trns.Shape()

    return shp


if __name__ == "__main__":
    i_cpacs = 1
    tixi_h = tixi3wrapper.Tixi3()
    m = myDisplay.instance(True)

    tigl_handle = tigl3wrapper.Tigl3()
    if i_cpacs == 1:
        tixi_h.open(
            r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v6.xml")
    tigl_handle.open(tixi_h, "")

    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_handle._handle.value)
    fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(1)
    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()

    fuselage_dim = ShapeDimensions(fuselage_shape)

    box = OPrim.BRepPrimAPI_MakeBox(fuselage_dim.get_length() / 2, fuselage_dim.get_width(),
                                    fuselage_dim.get_height()).Shape()
    moved_box = OExs.translate_shp(box, Ogp.gp_Vec(0, -fuselage_dim.get_width() / 2, 0))
    cuted_fuselage = OAlgo.BRepAlgoAPI_Fuse(fuselage_shape, moved_box).Shape()
    m.display_fuse(cuted_fuselage, fuselage_shape, moved_box)

    # slicer=s.ShapeSlicer()

    m.display_this_shape(fuselage_shape)
    m.start_display()

    write_stl_file2(cuted_fuselage, "fuselage_cuted.stl")
