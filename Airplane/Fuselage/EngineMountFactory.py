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


class EngineMountFactory:
    def __init__(self, tigl_handle):
        self.m = myDisplay.instance(True, 1)
        config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        cpacs_configuration: TConfig.CCPACSConfiguration = config_manager.get_configuration(tigl_handle._handle.value)
        self.fuselage: TConfig.CCPACSFuselage = cpacs_configuration.get_fuselage(1)

        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.shape()
        self.fuselage_dimensions = PDim.ShapeDimensions(self.fuselage_loft)

    def create_engine_mount(self, motor_lenght, shaft_lenght, mount_width, mount_hole_dim, alpha_angle, beta_angle):
        shapes = []
        lenght = shaft_lenght
        width = mount_width
        height = mount_width
        factor = 0.7

        panel_thickenss = 0.005
        panel = self._create_rear_panel(motor_lenght * 1.1, panel_thickenss)
        panel_dimensions = PDim.ShapeDimensions(panel)
        outer_box = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(lenght, width, height).Shape(), "outer_box")
        outer_box.set_shape(OExs.translate_shp(outer_box.shape(), Ogp.gp_Vec(0, -width / 2, -height / 2)))

        x_pos = (1 - factor) * lenght
        inner_box = TGeo.CNamedShape(
            OPrim.BRepPrimAPI_MakeBox(lenght * factor, width * factor, height * factor).Shape(), "inner_box")
        inner_box.set_shape(
            OExs.translate_shp(inner_box.shape(), Ogp.gp_Vec(x_pos, -width / 2 * factor, -height / 2 * factor)))

        radius = mount_width * factor / 2
        cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, lenght).Shape(), "cylider")
        cylinder.set_shape(OExs.rotate_shape(cylinder.shape(), Ogp.gp_OY(), 90))

        shapes_to_cut = [inner_box, cylinder]

        cuted_box = cut_list_of_shapes(outer_box, shapes_to_cut)
        cuted_box.set_name("engine_mount")
        engine_mount = [TGeo.CNamedShape]
        engine_mount.append(cuted_box)
        self.m.display_this_shape(cuted_box)

        radius = mount_hole_dim / 2
        cylinder_lenght = lenght * 0.4
        outer_cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, cylinder_lenght).Shape(),
                                          "outer_cylider")
        outer_cylinder.set_shape(OExs.rotate_shape(outer_cylinder.shape(), Ogp.gp_OY(), 90))
        inner_cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius * .5, cylinder_lenght).Shape(),
                                          "inner_cylinder")
        inner_cylinder.set_shape(OExs.rotate_shape(inner_cylinder.shape(), Ogp.gp_OY(), 90))

        horizontal_box = OPrim.BRepPrimAPI_MakeBox(lenght * factor, width * factor, height * factor).Shape()
        nut = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Cut(outer_cylinder.shape(), inner_cylinder.shape()).Shape(), "nut")
        nut.set_shape(OExs.translate_shp(nut.shape(), Ogp.gp_Vec(0, width / 2, 0)))
        nuts = create_circular_pattern(nut, 4)
        self.m.display_this_shape(nuts)
        self.m.display_this_shape(engine_mount[-1])

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1].shape(), nuts.shape()).Shape())
        engine_mount.append(new_mount)
        self.m.display_fuse(engine_mount[-1], engine_mount[-2], nuts)

        cutout_angle = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(lenght, 2 * width, 2 * height).Shape(), "cutout_agle")
        cutout_angle.set_shape(OExs.translate_shp(cutout_angle.shape(), Ogp.gp_Vec(-lenght * 0.9, -width, -height)))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OY(), alpha_angle))
        cutout_angle.set_shape(OExs.rotate_shape(cutout_angle.shape(), Ogp.gp_OZ(), beta_angle))

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Cut(engine_mount[-1].shape(), cutout_angle.shape()).Shape())
        engine_mount.append(new_mount)
        self.m.display_cut(engine_mount[-1], engine_mount[-2], cutout_angle)

        engine_mount_dimension = PDim.ShapeDimensions(engine_mount[-1])
        engine_x_pos = panel_dimensions.get_xmin() - engine_mount_dimension.get_length()
        engine_y_pos = 0
        engine_z_pos = panel_dimensions.get_zmid()

        new_mount = engine_mount[-1]
        new_mount.set_shape(
            OExs.translate_shp(engine_mount[-1].shape(), Ogp.gp_Vec(engine_x_pos, engine_y_pos, engine_z_pos)))
        engine_mount.append(new_mount)

        new_mount = engine_mount[-1]
        new_mount.set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1].shape(), panel.shape()).Shape())
        engine_mount.append(new_mount)

        # engine_mount.append(engine_mount[-1].set_shape(OExs.translate_shp(engine_mount[-1], Ogp.gp_Vec(engine_x_pos, engine_y_pos, engine_z_pos))))
        # engine_mount.append(engine_mount[-1].set_shape(OAlgo.BRepAlgoAPI_Fuse(engine_mount[-1], panel.shape()).Shape()))
        self.m.display_fuse(engine_mount[-1], engine_mount[-2], panel)

        self.m.display_in_origin(cylinder, "", True)
        self.m.display_in_origin(outer_box, "", True)
        self.m.display_in_origin(inner_box, "", True)
        self.m.display_in_origin(cutout_angle, "", True)
        self.m.display_this_shape(engine_mount[-1], "", True)
        self.m.start()

    def _create_rear_panel(self, position, thickness):
        box = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeBox(thickness, self.fuselage_dimensions.get_width(),
                                                         self.fuselage_dimensions.get_height()).Shape(), "boud_box")
        x_pos = position - thickness
        box.set_shape(OExs.translate_shp(box.shape(), Ogp.gp_Vec(x_pos, self.fuselage_dimensions.get_ymin(),
                                                                 self.fuselage_dimensions.get_zmin())))
        panel = TGeo.CNamedShape(OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, box.shape()).Shape(), "Panel")
        self.m.display_cut(panel, self.fuselage_loft, box)
        return panel

    def _front_point(self):
        #self.fuselage.set
        thickness = self.fuselage_dimensions.get_length() * 0.005
        box = [OPrim.BRepPrimAPI_MakeBox(thickness, self.fuselage_dimensions.get_width(),
                                         self.fuselage_dimensions.get_height()).Shape()]
        box.append(OExs.translate_shp(box[-1], Ogp.gp_Vec(0, self.fuselage_dimensions.get_ymin(),
                                                          self.fuselage_dimensions.get_zmin())))
        panel = OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, box[-1]).Shape()
        self.m.display_cut(panel, self.fuselage_shape, box[-1])
        return panel


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
