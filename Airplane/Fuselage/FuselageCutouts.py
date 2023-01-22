import OCP.BRepPrimAPI as OPrim
import OCP.gp as Ogp
import OCP.ShapeFactory as OExs
import tigl3.geometry as TGeo

import Extra.BooleanOperationsForLists as Bof
import Extra.patterns as Pat
from Dimensions.ShapeDimensions import ShapeDimensions


class FuselageCutouts:
    @classmethod
    def create_cylinder_pattern(cls, radius: float, height: float, quantity: float,
                                distance: float) -> TGeo.CNamedShape:
        '''
        Creates a linear patter of cylinders that are used as Cutouts
        :param radius: radius of each cylinder
        :param height: height of the cylinders
        :param quantity: amount of cylinders
        :param distance: distances between each cylinder
        :return:
        '''
        cylinder = TGeo.CNamedShape(OPrim.BRepPrimAPI_MakeCylinder(radius, height).Shape(), "cylinder_cutout")
        cylinder_pattern = Pat.create_linear_pattern(cylinder, quantity, distance, "x")
        return cylinder_pattern


    @classmethod
    def create_hardware_cutout(cls, fuselage_dimensions: ShapeDimensions, wing_dimensions: ShapeDimensions,
                               width_factor, length_factor, position="bottom") -> TGeo.CNamedShape:
        """
        Creates a cutout that is the same length as the wing and has the width of the fuselage times the factor.
        It is positiones at the top or bottom
        :param length_factor:
        :param fuselage_dimensions: dimensions of the fuselage shpae
        :param wing_dimensions: dimensions of the wing shape
        :param width_factor: factor used to create the inner ribcage
        :param position: describes the position of the cutout, top/bottom
        :return:
        """
        hardware_cutout_length = wing_dimensions.get_length() * length_factor

        # times 0.8 (80%) to avoid collision
        hardware_cutout_width = fuselage_dimensions.get_width() * width_factor * 0.8
        hardware_cutout_height = fuselage_dimensions.get_height()

        hardware_x_pos = wing_dimensions.get_x_min() + wing_dimensions.get_length() * 0.2
        hardware_y_pos = -hardware_cutout_width / 2

        hardware_z_pos = fuselage_dimensions.get_z_min() - hardware_cutout_height/2 \
            if position == "bottom" \
            else fuselage_dimensions.get_z_max() - hardware_cutout_height

        box = OPrim.BRepPrimAPI_MakeBox(hardware_cutout_length, hardware_cutout_width, hardware_cutout_height).Shape()
        moved_box = TGeo.CNamedShape(OExs.translate_shp(box,
                                                        Ogp.gp_Vec(hardware_x_pos, hardware_y_pos, hardware_z_pos)),
                                     "box_cutout")

        cylinder = OPrim.BRepPrimAPI_MakeCylinder(hardware_cutout_width / 2, hardware_cutout_height).Shape()
        cylinder_front = TGeo.CNamedShape(OExs.translate_shp(cylinder, Ogp.gp_Vec(hardware_x_pos, 0.0, hardware_z_pos)),
                                          "c1_cutout")
        hardware_x_pos += hardware_cutout_length
        cylinder_back = TGeo.CNamedShape(OExs.translate_shp(cylinder, Ogp.gp_Vec(hardware_x_pos, 0.0, hardware_z_pos)),
                                         "c2_cutout")
        cutouts = [moved_box, cylinder_front, cylinder_back]
        cutout = Bof.BooleanCADOperation.fuse_list_of_named_shapes(cutouts, "hardware_cutout")
        return cutout


    @classmethod
    def create_bolt_hole(cls, overlap_dimensions: ShapeDimensions) -> TGeo.CNamedShape:
        # Woodsticks diamater= 6mm + printing thicknes 0.4mm*2 + toleranz
        radius = 0.007 / 2
        cylinder_lenght = overlap_dimensions.get_width() * 1.2
        cylinder = OPrim.BRepPrimAPI_MakeCylinder(radius, cylinder_lenght).Shape()
        cylinder = OExs.translate_shp(cylinder, Ogp.gp_Vec(0, 0, -cylinder_lenght / 2))
        cylinder = OExs.rotate_shape(cylinder, Ogp.gp_OX(), 90)

        bolt_hole = TGeo.CNamedShape(cylinder, "bolt_hole")
        distance = overlap_dimensions.get_length() * 1.1
        bolt_holes = Pat.create_linear_pattern(bolt_hole, 2, distance, "x")

        bolt_holes_dimensions = ShapeDimensions(bolt_holes)
        x_pos = overlap_dimensions.get_x_mid() - bolt_holes_dimensions.get_x_mid()
        z_pos = overlap_dimensions.get_z_min() + (overlap_dimensions.get_height() * 0.8)

        bolt_holes.set_shape(OExs.translate_shp(bolt_holes.shape(), Ogp.gp_Vec(x_pos, 0, z_pos)))
        return bolt_holes
