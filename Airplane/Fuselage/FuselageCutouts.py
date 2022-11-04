import OCC.Core.BRepPrimAPI as OPrim
import OCC.Core.TopoDS as OTopo
import OCC.Core.gp as Ogp
import OCC.Extend.ShapeFactory as OExs

import Extra.BooleanOperationsForLists as Bof
import Extra.patterns as Pat
from Dimensions.ShapeDimensions import ShapeDimensions


class FuselageCutouts:
    def __int__(self):
        self.shape: None

    def create_cylinder_pattern(self, radius, height, quantity, distance) -> OTopo.TopoDS_Shape:
        cylinder = OPrim.BRepPrimAPI_MakeCylinder(radius, height).Shape()
        cylinder_pattern = Pat.create_linear_pattern(cylinder, quantity, distance)
        return cylinder_pattern

    def create_hardware_cutout(self, fuselage_dimensions: ShapeDimensions, wing_dimensions: ShapeDimensions,
                               width_factor, position="bottom") -> OTopo.TopoDS_Shape:
        """
        :param fuselage_dimensions:
        :param wing_dimensions:
        :param width_factor: factor used to create the inner ribcage
        :param position: describes the position of the cutout, top/bottom
        :return:
        """
        hardware_cutout_lenght = wing_dimensions.get_length()
        hardware_cutout_width = fuselage_dimensions.get_width() * width_factor * 0.9
        hardware_cutout_height = fuselage_dimensions.get_height() / 2

        hardware_x_pos = wing_dimensions.get_xmin() + wing_dimensions.get_length() * 0.2
        hardware_y_pos = -hardware_cutout_width / 2
        if position == "bottom":
            hardware_z_pos = fuselage_dimensions.get_zmin()
        else:
            hardware_z_pos = fuselage_dimensions.get_zmax() - hardware_cutout_height

        box = OPrim.BRepPrimAPI_MakeBox(hardware_cutout_lenght, hardware_cutout_width, hardware_cutout_height).Shape()
        moved_box = OExs.translate_shp(box,
                                       Ogp.gp_Vec(hardware_x_pos, hardware_y_pos, hardware_z_pos))

        cylinder = OPrim.BRepPrimAPI_MakeCylinder(hardware_cutout_width / 2, hardware_cutout_height).Shape()
        c1 = OExs.translate_shp(cylinder, Ogp.gp_Vec(hardware_x_pos, 0.0, hardware_z_pos))
        hardware_x_pos += hardware_cutout_lenght
        c2 = OExs.translate_shp(cylinder, Ogp.gp_Vec(hardware_x_pos, 0.0, hardware_z_pos))
        c_list = [moved_box, c1, c2]
        cutout = Bof.fuse_list_of_shapes(c_list)
        return cutout
