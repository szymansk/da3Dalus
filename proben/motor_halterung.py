import OCC.Core.gp as Ogp
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Extend.ShapeFactory as OExs
from Extra.mydisplay import myDisplay
import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs
import tigl3.configuration as TConfig
import tigl3.geometry as TGeo

from Extra.mydisplay import myDisplay
from Extra.BooleanOperationsForLists import *
from Extra.patterns import *
import Extra.tigl_extractor as tg
import Dimensions.ShapeDimensions as PDim

if __name__ == "__main__":
    m = myDisplay.instance(True, 5)

    tigl_handle = tg.get_tigl_handler("simple_aircraft")
    config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
    cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_handle._handle.value)
    fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(1)

    fuselage_loft: TGeo.CNamedShape = fuselage.get_loft()
    fuselage_shape: OTopo.TopoDS_Shape = fuselage_loft.shape()
    fuselage_dimensions = PDim.ShapeDimensions(fuselage_shape)

    engines = TConfig.CCPACSEngines = cpacs_configuration.get_engines()
    engine_positions: TConfig.CCPACSEnginePositions = cpacs_configuration.get_engine_positions()
    print(f"{engine_positions.get_engine_position_count()=}")
    pos: TConfig.CCPACSEnginePosition = engine_positions.get_engine_position()
    pos_parent: TConfig.CCPACSEnginePosition = pos.get_parent()
    print(type(pos_parent))

    lenght = 5
    width = 3
    height = width
    factor = 0.7
    outer_box = OPrim.BRepPrimAPI_MakeBox(lenght, width, height).Shape()
    outer_box = OExs.translate_shp(outer_box, Ogp.gp_Vec(0, -width / 2, -height / 2))

    x_pos = (1 - factor) * lenght
    inner_box = OPrim.BRepPrimAPI_MakeBox(lenght * factor, width * factor, height * factor).Shape()
    inner_box = OExs.translate_shp(inner_box, Ogp.gp_Vec(x_pos, -width / 2 * factor, -height / 2 * factor))

    radius = width * factor / 2
    cylinder = OPrim.BRepPrimAPI_MakeCylinder(radius, lenght).Shape()
    cylinder = OExs.rotate_shape(cylinder, Ogp.gp_OY(), 90)

    shapes_to_cut = [inner_box, cylinder]
    engine_mount = []
    engine_mount.append(cut_list_of_shapes(outer_box, shapes_to_cut, "Here"))

    radius = 0.3
    cylinder_lenght = lenght * 0.4
    outer_cylinder = OPrim.BRepPrimAPI_MakeCylinder(radius, cylinder_lenght).Shape()
    outer_cylinder = OExs.rotate_shape(outer_cylinder, Ogp.gp_OY(), 90)
    inner_cylinder = OPrim.BRepPrimAPI_MakeCylinder(radius * .5, cylinder_lenght).Shape()
    inner_cylinder = OExs.rotate_shape(inner_cylinder, Ogp.gp_OY(), 90)
    mutter = OAlgo.BRepAlgoAPI_Cut(outer_cylinder, inner_cylinder).Shape()
    mutter = OExs.translate_shp(mutter, Ogp.gp_Vec(0, width / 2, 0))
    muttern = create_circular_pattern(mutter, 4)
    engine_mount.append(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1], muttern).Shape())
    m.display_fuse(engine_mount[-1], engine_mount[-2], muttern)

    cutout_angle = [OPrim.BRepPrimAPI_MakeBox(lenght, 2 * width, 2 * height).Shape()]
    alpha_angle = 5
    beta_angle = 3
    cutout_angle.append(OExs.translate_shp(cutout_angle[-1], Ogp.gp_Vec(-lenght * 0.9, -width, -height)))
    cutout_angle.append(OExs.rotate_shape(cutout_angle[-1], Ogp.gp_OY(), alpha_angle))
    cutout_angle.append(OExs.rotate_shape(cutout_angle[-1], Ogp.gp_OZ(), beta_angle))

    engine_mount.append(OAlgo.BRepAlgoAPI_Cut(engine_mount[-1], cutout_angle[-1]).Shape())
    m.display_cut(engine_mount[-1], engine_mount[-2], cutout_angle[-1])

    m.display_in_origin(cylinder, "", True)
    m.display_in_origin(outer_box, "", True)
    m.display_in_origin(inner_box, "", True)
    m.display_in_origin(cutout_angle[-1], "", True)
    m.display_this_shape(engine_mount[-1], "", True)
    m.start()

'''
complete=OAlgo.BRepAlgoAPI_Fuse(left,cylinder).Shape()
m.display_fuse(complete, left, cylinder) 
complete2=OAlgo.BRepAlgoAPI_Fuse(complete,right).Shape()
m.display_fuse(complete2, complete, right) 

point:Ogp.gp_Pnt =TGeo.get_center_of_mass(complete)
print(point.X(), point.Y(), point.Z())
center_of_mass = OPrim.BRepPrimAPI_MakeSphere(point, 3).Shape()
'''

# display, start_display, add_menu, add_function_to_menu = init_display()
# display.DisplayShape(center_of_mass, color="BLUE")
# display.DisplayShape(complete)
# display.DisplayShape(complement)
# display.DisplayShape(right)
# display.DisplayShape(cylinder)


# display.FitAll()
# start_display()

# write_stl_file2(complete, "Box_test.stl")
