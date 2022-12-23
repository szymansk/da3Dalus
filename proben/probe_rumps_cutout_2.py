import OCC.Core.BRepBuilderAPI as OBui
import OCC.Core.BRepBuilderAPI as OBuilder
import OCC.Core.BRepOffsetAPI as OOff
import tigl3.configuration as TConfig

from Extra.BooleanOperationsForLists import *
from Extra.ConstructionStepsViewer import ConstructionStepsViewer
# from Airplane.Wing.CablePipeFactory import CabelPipe
from _alt.Wand_erstellen import *
from _alt.abmasse import *
from _alt.shape_verschieben import rotate_shape


class aircombat_test:
    def __init__(self, dev=False, tigl_h=None):
        if dev == False:
            self.init_prod(dev, tigl_h)
        else:
            self.init_dev(dev)

    def init_prod(self, dev, tigl_h):
        self.m = ConstructionStepsViewer.instance(dev)
        self.tigl_handle = tigl_h
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            self.tigl_handle._handle.value)

    def init_dev(self, dev=True):
        self.m = ConstructionStepsViewer.instance(dev)
        i_cpacs = 6
        self.tixi_h = tixi3wrapper.Tixi3()
        self.tigl_handle = tigl3wrapper.Tigl3()
        if i_cpacs == 1:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\fluegel_test_1008.xml")
        if i_cpacs == 2:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\CPACS_30_D150.xml")
        if i_cpacs == 3:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_skaliert_f38_one_profile.xml")
        if i_cpacs == 5:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_original_oneprofil_mitte.xml")
        if i_cpacs == 4:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\tinybit_new.xml")
        if i_cpacs == 6:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\aircombat_v2.xml")
        if i_cpacs == 7:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\test_fluegel_punkte.xml")
        if i_cpacs == 8:
            self.tixi_h.open(
                r"C:\Users\schneichel\OneDrive - adesso Group\Dokumente\GitHub\cad-modelling-service-2\test_cpacs\test_rumpf_punkte.xml")
        self.tigl_handle.open(self.tixi_h, "")
        self.config_manager: TConfig.CCPACSConfigurationManager = TConfig.CCPACSConfigurationManager_get_instance()
        self.cpacs_configuration: TConfig.CCPACSConfiguration = self.config_manager.get_configuration(
            self.tigl_handle._handle.value)

    def rotate_shape(self, shape, axis, angle):
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

    def create_mainwing(self):
        self.wing: TConfig.CCPACSWing = self.cpacs_configuration.get_wing(1)
        self.wing_loft: TGeo.CNamedShape = self.wing.get_loft()
        self.wing_shape: OTopo.TopoDS_Shape = self.wing_loft.shape()
        # Set up the mirror
        aTrsf = Ogp.gp_Trsf()
        aTrsf.SetMirror(Ogp.gp_Ax2(Ogp.gp_Pnt(0, 0, 0), Ogp.gp_Dir(0, 1, 0)))
        transformed_wing = OBuilder.BRepBuilderAPI_Transform(self.wing_shape, aTrsf)
        claculate_mainwing_dimension(self.wing_shape)
        mirrored_wing = transformed_wing.Shape()
        self.complete_wing = OAlgo.BRepAlgoAPI_Fuse(self.wing_shape, mirrored_wing).Shape()
        self.m.display_fuse(self.complete_wing, self.wing_shape, mirrored_wing, logging.NOTSET, "complete_wing")
        # self.m.display_this_shape(self.complete_wing,msg="Fused completewing")

    def create_offset_wing(self, offset=0.0008):
        self.wing_offset = OOff.BRepOffsetAPI_MakeOffsetShape(self.wing_shape, offset, 0.00001).Shape()
        self.m.display_this_shape(self.wing_offset, severity=logging.NOTSET)

    def create_right_wing(self, rib_width=0.0002, angle=45):
        wing = []
        rib = self.create_wing_ribs(rib_width, angle)
        wing.append(OAlgo.BRepAlgoAPI_Common(self.wing_shape, rib).Shape())
        self.m.display_common(wing[-1], self.wing_shape, rib, logging.NOTSET)
        wing.append(OAlgo.BRepAlgoAPI_Cut(self.wing_offset, wing[-1]).Shape())
        self.m.display_cut(wing[-1], self.wing_offset, wing[-2], logging.NOTSET)

        # Create cable pipe and add to wing
        cable_pipe = self.create_cable_pipe()
        wing.append(OAlgo.BRepAlgoAPI_Cut(wing[-1], cable_pipe).Shape())
        self.m.display_cut(wing[-1], wing[-2], cable_pipe, logging.NOTSET)

        # Create hinge recces and add to wing
        # hinge_recess=self.create_hinge_recces()
        # wing.append(OAlgo.BRepAlgoAPI_Cut(wing[-1],hinge_recess).Shape())
        # self.m.display_cut(wing[-1],hinge_recess,wing[-2])

        # Create Flapscutout
        flaps_cutout = self.create_flaps_and_cutout(wing[-1])
        wing.append(OAlgo.BRepAlgoAPI_Cut(wing[-1], flaps_cutout).Shape())
        self.m.display_cut(wing[-1], wing[-2], flaps_cutout, logging.NOTSET)
        self.wing_done = wing[-1]

    def create_wing_ribs(self, rib_width=0.0002, angle=45):
        rib = []
        rib.append(self.create_diagonal_ribs(rib_width, angle=45))
        rib.append(self.create_horizontal_wing_ribs(rib_width))
        rib.append(OAlgo.BRepAlgoAPI_Fuse(rib[-2], rib[-1]).Shape())
        self.m.display_fuse(rib[-1], rib[-3], rib[-2], logging.NOTSET)
        rib.append(self.create_carbontunnel_wing())
        rib.append(OAlgo.BRepAlgoAPI_Fuse(rib[-2], rib[-1]).Shape())
        self.m.display_fuse(rib[-1], rib[-3], rib[-2], logging.NOTSET)
        return rib[-1]
        '''
        rib.append(OAlgo.BRepAlgoAPI_Common(self.wing_shape,rib[-1]).Shape())
        self.m.display_common(rib[-1],self.wing_shape,rib[-2])
        rib.append(OAlgo.BRepAlgoAPI_Cut(self.wing_offset,rib[-1]).Shape())
        self.m.display_common(rib[-1],self.wing_offset,rib[-2])
        rib.append(self.create_flaps_and_cutout(rib))
        self.wing_done=rib[-1]
        '''

    def create_diagonal_ribs(self, rib_width, angle):
        prim = []
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(self.wing_shape)
        prim.append(OPrim.BRepPrimAPI_MakeBox(wing_lenght * 2, rib_width, wing_height).Shape())
        prim.append(OExs.rotate_shape(prim[-1], gp_OZ(), angle))
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(xmin, -rib_width, zmin)))
        self.m.display_this_shape(prim[-1], severity=logging.NOTSET)
        ribs_distance = 0.1
        ribs_quantity = round((wing_width / ribs_distance) * 2)
        prim.append(self.create_linear_pattern(prim[-1], ribs_quantity, ribs_distance, "y"))
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(0, -wing_width / 2, 0)))
        self.m.display_this_shape(prim[-1], severity=logging.NOTSET)
        return prim[-1]

    def create_horizontal_wing_ribs(self, rib_width):
        prim = []
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(self.wing_shape)
        prim.append(OPrim.BRepPrimAPI_MakeBox(rib_width, wing_width, wing_height).Shape())
        distance = wing_lenght / 4
        x_pos = xmin + distance - rib_width / 2
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(x_pos, 0.0, zmin)))
        self.m.display_this_shape(prim[-1], severity=logging.NOTSET)
        prim.append(self.create_linear_pattern(prim[-1], 3, distance, "x"))
        self.m.display_this_shape(prim[-1], severity=logging.NOTSET)
        return prim[-1]

    def create_carbontunnel_wing(self):
        prim = []
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(self.wing_shape)
        prim.append(OPrim.BRepPrimAPI_MakeCylinder(0.0024, wing_width).Shape())
        prim.append(OExs.rotate_shape(prim[-1], gp_OX(), -90))
        distance = wing_lenght / 4
        x_pos = xmin + distance
        z_pos = zmin + wing_height / 2
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(x_pos, 0.0, z_pos)))
        self.m.display_this_shape(prim[-1], severity=logging.NOTSET)
        prim.append(self.create_linear_pattern(prim[-1], 2, distance, "x"))
        self.m.display_this_shape(prim[-1], severity=logging.NOTSET)
        return prim[-1]

    def create_flaps_and_cutout(self, wing):
        logging.debug(f"Creating flaps cutout")
        prim = []
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(self.wing_shape)
        flaps_lenght, flaps_width, flaps_height = 0.03, wing_width * 0.6, wing_height
        prim.append(OPrim.BRepPrimAPI_MakeBox(flaps_lenght, flaps_width, flaps_height).Shape())
        x, y, z = xmax - flaps_lenght, wing_width * 0.4, zmin
        prim.append(OExs.translate_shp(prim[-1], Ogp.gp_Vec(x, y, z)))
        return prim[-1]
        # wing_with_cutout=OAlgo.BRepAlgoAPI_Cut(wing,prim[-1]).Shape()
        # self.m.display_cut(wing_with_cutout,wing,prim[-1])
        # return wing_with_cutout

    def create_cable_pipe(self):
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(self.wing_shape)
        servo_pos = wing_width * 0.45
        points, x, y = self.list_for_pipe1(servo_pos, zmax, zmin)
        mcp = CabelPipe(points, 0.003)
        L_pipe = []
        L_pipe.append(mcp.get_pipe())
        self.m.display_in_origin(L_pipe[-1], logging.NOTSET)

        points2 = self.list_for_pipe2()
        mcp = CabelPipe(points2, 0.003)
        zL_pipe = []
        zL_pipe.append(mcp.get_pipe())
        zL_pipe.append(OExs.rotate_shape(zL_pipe[-1], gp_OY(), 90))
        zL_pipe.append(OExs.translate_shp(zL_pipe[-1], Ogp.gp_Vec(x, servo_pos, 0.0)))

        L_pipe.append(OAlgo.BRepAlgoAPI_Fuse(L_pipe[-1], zL_pipe[-1]).Shape())
        L_pipe.append(OExs.rotate_shape(L_pipe[-1], gp_OY(), -90))
        x_pos = ((2 / 3) * wing_lenght) + xmin
        z_pos = 0.005
        y_pos = 0.015
        L_pipe.append(OExs.translate_shp(L_pipe[-1], Ogp.gp_Vec(x_pos, y_pos, z_pos)))
        return L_pipe[-1]

    def create_servo_recess(self, lenght, width, height, x_pos, y_pos, z_pos):
        recess = []
        recess.append(OPrim.BRepPrimAPI_MakeBox(lenght, width, height))
        recess.append(OExs.translate_shp(recess[-1]), Ogp.gp_Vec(x_pos, y_pos, z_pos))
        lenght = lenght * 1.1
        width = width * 0.2
        recess.append(OPrim.BRepPrimAPI_MakeBox(lenght, width, height))
        recess.append(OExs.translate_shp(recess[-1]), Ogp.gp_Vec(x_pos, y_pos, z_pos))
        recess.append(OAlgo.BRepAlgoAPI_Fuse(recess[-3], recess[-1]).Shape())
        self.m.display_fuse(recess[-1], recess[-4], recess[-2], logging.NOTSET)
        return recess[-1]

    # def create_hinge_recces(self)

    def create_fuselage(self):
        self.fuselage: TConfig.CCPACSFuselage = self.cpacs_configuration.get_fuselage(1)
        self.fuselage_loft: TGeo.CNamedShape = self.fuselage.get_loft()
        self.fuselage_shape: OTopo.TopoDS_Shape = self.fuselage_loft.shape()
        # self.fuselage_shape=OExs.translate_shp(self.fuselage_shape,Ogp.gp_Vec(0,0,0.003))
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.fuselage_shape)
        claculate_fuselage_dimension(self.fuselage_shape)
        self.fuselage_lenght, self.fuselage_widht, self.fuselage_height = get_dimensions(xmin, ymin, zmin, xmax, ymax,
                                                                                         zmax)
        logstr = f"Fuselage Dimensions lenght={self.fuselage_lenght}, widht={self.fuselage_widht} height={self.fuselage_height}"
        logging.debug(logstr)
        self.m.display_this_shape(self.fuselage_shape, severity=logging.NOTSET, logstr)

    def cut_fuselage_with_wing(self):
        self.cutted_fuselage_shape = OAlgo.BRepAlgoAPI_Cut(self.fuselage_shape, self.complete_wing).Shape()
        self.m.display_this_shape(self.cutted_fuselage_shape, severity=logging.NOTSET, "Cutted Fuselage")

    def hollow_fuselage(self, thickness=0.0004):
        # facesToRemove = TopTools_ListOfShape()
        # Fuselage Hollow, walls for wings #0.01
        # self.fuselage_hollow= OOff.BRepOffsetAPI_MakeThickSolid(self.cutted_fuselage_shape, facesToRemove, 0.04, 0.01).Shape()
        self.fuselage_hollow = create_hollowedsolid(self.fuselage_shape, thickness)
        self.m.display_this_shape(self.fuselage_hollow, severity=logging.NOTSET,
                                  f"Hollow Fuselage- Thickness {thickness}", True)

    def create_cross_rib(self):
        rib_width = 0.0004
        self.mybox = OPrim.BRepPrimAPI_MakeBox(1, 1, 1).Shape()
        box = OPrim.BRepPrimAPI_MakeBox(self.fuselage_lenght * 2, rib_width * 2, self.fuselage_height * 2).Shape()
        self.moved_box = OExs.translate_shp(box, Ogp.gp_Vec(0, -rib_width, -self.fuselage_height))
        # Cut Out for Hardware
        hardware_box_height = self.fuselage_height * 0.4 + (rib_width / 2)
        hardware_box_lenght = self.fuselage_lenght * 0.4
        hardware_box_widht = self.fuselage_widht * 0.8
        hardware_box = OPrim.BRepPrimAPI_MakeBox(hardware_box_lenght, hardware_box_widht, hardware_box_height).Shape()
        self.moved_hardware_box = OExs.translate_shp(hardware_box, Ogp.gp_Vec(0, -hardware_box_widht / 2,
                                                                              -hardware_box_height + (rib_width / 2)))
        self.m.display_this_shape(self.moved_hardware_box, severity=logging.NOTSET, "Hardware Box")
        rib_quantity = 2
        d_angle = 180 / rib_quantity
        for i in range(rib_quantity):
            angle = i * d_angle
            print(i, angle)
            sbox = self.rotate_shape(self.moved_box, Ogp.gp_OX(), angle)
            if i == 0:
                self.rippen = sbox
            else:
                self.rippen = OAlgo.BRepAlgoAPI_Fuse(self.rippen, sbox).Shape()
        self.m.display_this_shape(self.rippen, severity=logging.NOTSET, "Cross Ribs")

    def create_quadrat_rib2(self, rib_width=0.0004, factor=0.3):
        box = OPrim.BRepPrimAPI_MakeBox(self.fuselage_lenght * 2, rib_width * 2, self.fuselage_height * 2).Shape()
        moved_box = OExs.translate_shp(box, Ogp.gp_Vec(0, -rib_width, -self.fuselage_height))
        # self.m.display_this_shape(moved_box, "Moved Box")
        # self.m.display_in_origin(self.moved_box)
        ver_rib = moved_box
        y_pos = self.fuselage_widht * factor
        ver_rib_1 = OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, y_pos, 0.0))
        ver_rib_2 = OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, -y_pos, 0.0))
        hor_rib = rotate_shape(moved_box, Ogp.gp_OX(), 90)
        z_pos = y_pos
        hor_rib_1 = OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, 0.0, z_pos))
        hor_rib_2 = OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, 0.0, -z_pos))
        rippen = ver_rib_1
        rippen = OAlgo.BRepAlgoAPI_Fuse(rippen, ver_rib_2).Shape()
        rippen = OAlgo.BRepAlgoAPI_Fuse(rippen, hor_rib_1).Shape()
        rippen = OAlgo.BRepAlgoAPI_Fuse(rippen, hor_rib_2).Shape()
        self.m.display_this_shape(rippen, severity=logging.NOTSET, "Quadrat Ribs")
        return rippen

    def create_wing_reinforcement_ribs(self):
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        length, width, height = get_dimensions_from_Shape(self.wing_shape)
        box_length, box_width, box_height = length / 2, 0.0004, 2 * height
        box = OPrim.BRepPrimAPI_MakeBox(box_length, box_width, box_height).Shape()
        moved_box = OExs.translate_shp(box, Ogp.gp_Vec(0, -box_width / 2, -box_height / 2))
        rot_box = OExs.rotate_shape(moved_box, Ogp.gp_OY(), 60)
        moved_box = OExs.translate_shp(rot_box, Ogp.gp_Vec(xmin - 0.002, 0, zmax - 0.01))
        f_length, f_width, f_height = get_dimensions_from_Shape(self.fuselage_shape)
        rib_width = f_width * 0.6
        distance = rib_width / 7
        rib = OExs.translate_shp(moved_box, Ogp.gp_Vec(0, -distance * 3, 0))
        for i in range(0, 7):
            movedrib = OExs.translate_shp(rib, Ogp.gp_Vec(0, distance * i, 0))
            if i == 0:
                ribs = movedrib
            else:
                ribs2 = OAlgo.BRepAlgoAPI_Fuse(ribs, movedrib).Shape()
                ribs = ribs2
        box = OPrim.BRepPrimAPI_MakeBox(f_length, f_width, f_height).Shape()
        moved_box = OExs.translate_shp(box, Ogp.gp_Vec(0, -f_width / 2, zmax))
        ribs_cut = OAlgo.BRepAlgoAPI_Cut(ribs, moved_box).Shape()
        self.m.display_cut(ribs_cut, ribs, moved_box, logging.NOTSET)
        return ribs_cut

    def create_quadrat_rib(self, rib_width, y_max, y_min, z_max, z_min):
        rib_lenght = self.fuselage_lenght * 1.2
        rib_height = self.fuselage_height * 1.2
        box = OPrim.BRepPrimAPI_MakeBox(rib_lenght, rib_width, rib_height).Shape()
        moved_box = OExs.translate_shp(box, Ogp.gp_Vec(-rib_lenght * 0.1, -rib_width / 2, -rib_height / 2))
        ver_rib = moved_box
        ver_rib_1 = OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, y_max, 0.0))
        ver_rib_2 = OExs.translate_shp(ver_rib, Ogp.gp_Vec(0.0, y_min, 0.0))
        # berechnen der top stelle des flügels
        self.wing_zmax = get_koordinate(self.wing_shape, "z_max")
        hor_rib = rotate_shape(moved_box, Ogp.gp_OX(), 90)
        hor_rib_1 = OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, 0.0, z_max))
        hor_rib_2 = OExs.translate_shp(hor_rib, Ogp.gp_Vec(0.0, 0.0, z_min))
        interim_rib = ver_rib_1
        interim_rib = OAlgo.BRepAlgoAPI_Fuse(interim_rib, ver_rib_2).Shape()
        interim_rib = OAlgo.BRepAlgoAPI_Fuse(interim_rib, hor_rib_1).Shape()
        quadrat_rib = OAlgo.BRepAlgoAPI_Fuse(interim_rib, hor_rib_2).Shape()
        logstr = f"Quadrat ribs: x_pos=0 y_max={y_max:.3f} y_min={y_min:.3f} z_max={z_max:.3f} z_min={z_min:.3f}"
        self.m.display_fuse(quadrat_rib, interim_rib, hor_rib_2, logging.NOTSET, logstr)
        logging.debug(logstr)
        return quadrat_rib

    def create_cylinder_reinforcemnt(self, radius, y_max, y_min, z_max, z_min):
        cylinder = OPrim.BRepPrimAPI_MakeCylinder(radius, self.fuselage_lenght).Shape()
        cylinder = self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        x_pos = 0
        cylinder_1 = OExs.translate_shp(cylinder, Ogp.gp_Vec(0.0, y_max, z_max))
        cylinder_2 = OExs.translate_shp(cylinder, Ogp.gp_Vec(0.0, y_max, z_min))
        cylinder_3 = OExs.translate_shp(cylinder, Ogp.gp_Vec(0.0, y_min, z_min))
        cylinder_4 = OExs.translate_shp(cylinder, Ogp.gp_Vec(0.0, y_min, z_max))
        interim_cylinders = cylinder_1
        interim_cylinders = OAlgo.BRepAlgoAPI_Fuse(interim_cylinders, cylinder_2).Shape()
        interim_cylinders = OAlgo.BRepAlgoAPI_Fuse(interim_cylinders, cylinder_3).Shape()
        cylinders = OAlgo.BRepAlgoAPI_Fuse(interim_cylinders, cylinder_4).Shape()
        logstr = f"Tunnel for Carbon Reinforcements x_pos=0 y_pos_max={y_max:.3f} y_pos_min={y_min:.3f} z_pos_max={z_max:.3f} z_pos_min={z_min:.3f}"
        self.m.display_fuse(cylinders, interim_cylinders, cylinder_4, logging.NOTSET, logstr)
        logging.debug(logstr)
        return cylinders

    def create_rib_weight_reduction_recces(self, radius=0.01, distance=0.1):
        # testCylinder=OPrim.BRepPrimAPI_MakeCylinder(radius,self.fuselage_widht).Shape()
        # self.m.display_this_shape(testCylinder)
        box = OPrim.BRepPrimAPI_MakeBox(0.001, 0.001, 0.001).Shape()
        cylinder = OPrim.BRepPrimAPI_MakeCylinder(radius, self.fuselage_height).Shape()
        cylinder = self.rotate_shape(cylinder, Ogp.gp_OX(), 90)
        cylinder_pattern = self.create_linear_pattern(cylinder, 8, distance)
        self.m.display_this_shape(cylinder_pattern, severity=logging.NOTSET)
        # self.m.display_in_origin(cylinder_pattern)
        # self.m.display_in_origin(box)
        return cylinder_pattern

    def create_linear_pattern(self, shape, quantity, distance, direction="x"):
        pattern = shape
        logstr = f"Creating a linear pattern of {quantity} x {distance} meters"
        logging.debug(logstr)
        x, y, z = 0.0, 0.0, 0.0
        for i in range(1, quantity):
            if direction == "x":
                x = i * distance
            if direction == "y":
                y = i * distance
            if direction == "z":
                z = i * distance
            moved_shape = OExs.translate_shp(shape, Ogp.gp_Vec(x, y, z))
            newpattern = OAlgo.BRepAlgoAPI_Fuse(pattern, moved_shape).Shape()
            pattern = newpattern
        return pattern

    def create_sharp_ribs(self, rib_width=0.0002, factor=0.3, radius=0.00245):
        y_max = self.fuselage_widht * factor
        y_min = -y_max
        z_max = self.fuselage_height * factor
        z_min = get_koordinate(self.wing_shape, "z_max") + 0.003
        quadrat = self.create_quadrat_rib(rib_width, y_max, y_min, z_max, z_min)
        cylinders = self.create_cylinder_reinforcemnt(radius, y_max, y_min, z_max, z_min)
        reduktion_radius = ((z_max - z_min) * 0.8) / 2
        reduktion_zpos = ((z_max - z_min) / 2) - reduktion_radius + (rib_width / 2)
        logstr = f"y_max= {y_max:.4f} y_min {y_min:.4f} z_max= {z_max:.4f} z_min= {z_min:.4f} radius= {reduktion_radius:.4f} z_pos= {reduktion_zpos:.5f}"
        logging.debug(logstr)
        weight_reduktion_cylinders_hor = self.create_rib_weight_reduction_recces(reduktion_radius, 0.1)
        weight_reduktion_cylinders_hor = OExs.translate_shp(weight_reduktion_cylinders_hor,
                                                            Ogp.gp_Vec(reduktion_radius * 2, self.fuselage_widht / 2,
                                                                       reduktion_zpos))
        rippen_cut_recces = OAlgo.BRepAlgoAPI_Cut(quadrat, weight_reduktion_cylinders_hor).Shape()
        self.m.display_cut(rippen_cut_recces, quadrat, weight_reduktion_cylinders_hor, logging.NOTSET, logstr)
        reduktion_radius = y_max * 0.7
        weight_reduktion_cylinders_ver = self.create_rib_weight_reduction_recces(reduktion_radius, 0.1)
        weight_reduktion_cylinders_ver = OExs.translate_shp(weight_reduktion_cylinders_ver,
                                                            Ogp.gp_Vec(reduktion_radius * 2, self.fuselage_widht / 2,
                                                                       0))
        weight_reduktion_cylinders_ver = OExs.rotate_shape(weight_reduktion_cylinders_ver, Ogp.gp_OX(), 90)
        rippen_cut_recces2 = OAlgo.BRepAlgoAPI_Cut(rippen_cut_recces, weight_reduktion_cylinders_ver).Shape()
        self.m.display_cut(rippen_cut_recces2, rippen_cut_recces, weight_reduktion_cylinders_ver, logging.NOTSET, "Cut")
        hardware_cutout = self.create_hardware_cutout(factor, radius)
        ribs_with_hardware_cutout = OAlgo.BRepAlgoAPI_Cut(rippen_cut_recces2, hardware_cutout).Shape()
        self.m.display_cut(ribs_with_hardware_cutout, rippen_cut_recces2, hardware_cutout, logging.NOTSET)
        wing_reinforcement = self.create_wing_reinforcement_ribs()
        rippen_with_reinforcement = OAlgo.BRepAlgoAPI_Fuse(ribs_with_hardware_cutout, wing_reinforcement).Shape()
        self.m.display_fuse(rippen_with_reinforcement, rippen_cut_recces2, wing_reinforcement, logging.NOTSET)
        self.rippen_cuted = OAlgo.BRepAlgoAPI_Fuse(rippen_with_reinforcement, cylinders).Shape()
        # self.rippen_cuted= OAlgo.BRepAlgoAPI_Fuse(quadrat,cylinders).Shape()
        # self.m.display_this_shape(self.rippen_cuted, "Sharp Rippen")
        logging.debug("Fused ribs and cylinders")
        self.m.display_fuse(self.rippen_cuted, rippen_with_reinforcement, cylinders, logging.NOTSET,
                            "Fused ribs and cylinders")

    def create_hardware_cutout(self, factor, radius):
        hardware_cutout_lenght = self.fuselage_lenght * 0.2
        hardware_cutout_width = self.fuselage_widht * (factor * 2) - (radius * 2)
        hardware_cutout_height = self.fuselage_height / 2
        hardware_x_pos = get_koordinate(self.wing_shape, "x_min")
        box = OPrim.BRepPrimAPI_MakeBox(hardware_cutout_lenght, hardware_cutout_width, hardware_cutout_height).Shape()
        moved_box = OExs.translate_shp(box,
                                       Ogp.gp_Vec(hardware_x_pos, -hardware_cutout_width / 2, -hardware_cutout_height))
        cylinder = BRepPrimAPI_MakeCylinder(hardware_cutout_width / 2, hardware_cutout_height).Shape()
        c1 = OExs.translate_shp(cylinder, Ogp.gp_Vec(hardware_x_pos, 0.0, -hardware_cutout_height))
        hardware_x_pos += hardware_cutout_lenght
        c2 = OExs.translate_shp(cylinder, Ogp.gp_Vec(hardware_x_pos, 0.0, -hardware_cutout_height))
        c_list = [moved_box, c1, c2]
        cutout = fuse_list_of_shapes(c_list)
        return cutout

    def create_thin_star_ribs(self):
        # Cutout for Extra Ribs
        # cylinder= OPrim.BRepPrimAPI_MakeCylinder((fuselage_height*0.8)/2,40).Shape()
        cylinder = OPrim.BRepPrimAPI_MakeCylinder(1.5, 40).Shape()
        cylinder = self.rotate_shape(cylinder, Ogp.gp_OY(), 90)
        self.m.display_this_shape(cylinder, severity=logging.NOTSET, "Cylinder Cutout")
        rib_quantity = 2
        # Extraribs
        d_angle = 180 / (rib_quantity * 2)
        for i in range(rib_quantity * 2):
            angle = i * d_angle
            print(i, angle)
            sbox = self.rotate_shape(self.moved_box, Ogp.gp_OX(), angle)
            if i == 0:
                self.rippen_ver = sbox
            else:
                self.rippen_ver = OAlgo.BRepAlgoAPI_Fuse(self.rippen_ver, sbox).Shape()
        self.m.display_this_shape(self.rippen_ver, severity=logging.NOTSET, "Star ribs")
        self.rippen_ver = OAlgo.BRepAlgoAPI_Cut(self.rippen_ver, cylinder).Shape()
        self.m.display_this_shape(self.rippen_ver, severity=logging.NOTSET, "Starribs with cylinder cutout")

    def reinforcement_tunel_in(self):
        self.reinforcement_tunnel_in = OPrim.BRepPrimAPI_MakeCylinder(0.002, self.fuselage_lenght).Shape()
        self.reinforcement_tunnel_in = self.rotate_shape(self.reinforcement_tunnel_in, Ogp.gp_OY(), 90)

    def reinforcement_tunel_out(self):
        self.reinforcement_tunnel_out = OPrim.BRepPrimAPI_MakeCylinder(0.004, self.fuselage_lenght).Shape()
        self.reinforcement_tunnel_out = self.rotate_shape(self.reinforcement_tunnel_out, Ogp.gp_OY(), 90)
        self.m.display_this_shape(self.reinforcement_tunnel_out, severity=logging.NOTSET, "Reinforcement Tunel")

    def common_fuselage_ribs_ver(self):
        self.rippen_ver = OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, self.rippen_ver).Shape()
        self.m.display_this_shape(self.rippen_ver, severity=logging.NOTSET, "Ribs cut to fuselage shape")

    def cut_ribs_harwarebox(self):
        self.rippen_cuted = OAlgo.BRepAlgoAPI_Cut(self.rippen, self.moved_hardware_box).Shape()
        self.m.display_this_shape(self.rippen_cuted, severity=logging.NOTSET, "Cross Ribs with hardware Box Cutout")

    def fuse_reinforcemt_ribs(self):
        self.rippen_cuted = OAlgo.BRepAlgoAPI_Fuse(self.rippen_cuted, self.reinforcement_tunnel_out).Shape()
        self.m.display_this_shape(self.rippen_cuted, severity=logging.NOTSET, "Ribs with reinforcement tunel")

    def common_fuselage_ribs_cuted(self):
        self.rippen_cuted_form = OAlgo.BRepAlgoAPI_Common(self.fuselage_shape, self.rippen_cuted).Shape()
        self.m.display_common(self.rippen_cuted_form, self.fuselage_shape, self.rippen_cuted, logging.NOTSET,
                              "Cut ribs to fuselage Shape")

    def fuse_ribs(self):
        self.rippen_gesamt = OAlgo.BRepAlgoAPI_Fuse(self.rippen_cuted, self.rippen_ver).Shape()
        self.m.display_this_shape(self.rippen_gesamt, severity=logging.NOTSET, " Fused Ribs")

    def center_mass(self):
        point: Ogp.gp_Pnt = TGeo.get_center_of_mass(self.rippen_cuted)
        print(point.X(), point.Y(), point.Z())
        center_of_mass = OPrim.BRepPrimAPI_MakeSphere(point, 1).Shape()

    def fuse_fuselagehollow_ribs(self):
        print("---------Starting last Fuse: Wait...")
        # self.m.display_in_origin(self.fuselage_hollow, True)
        # self.m.display_in_origin(self.rippen_cuted)
        self.fuselage_done = OAlgo.BRepAlgoAPI_Fuse(self.fuselage_hollow, self.rippen_cuted).Shape()
        # self.m.display_this_shape(self.fuselage_done, "Done")
        self.m.display_fuse(self.fuselage_done, self.fuselage_hollow, self.rippen_cuted, logging.NOTSET)

    def test_fuse(self):
        print("---------Starting Test Fuse: Wait...")
        # self.m.display_in_origin(self.fuselage_hollow, True)
        mybox = OPrim.BRepPrimAPI_MakeBox(self.fuselage_lenght / 10, self.fuselage_widht / 10,
                                          self.fuselage_height / 10).Shape()
        mybox = translate_shp(mybox, gp_Vec(0, self.fuselage_widht / 2, self.fuselage_height / 2))
        self.m.display_in_origin(mybox, logging.NOTSET)
        self.fuselage_done = OAlgo.BRepAlgoAPI_Fuse(self.fuselage_hollow, self.rippen_cuted).Shape()
        self.m.display_this_shape(self.fuselage_done, severity=logging.NOTSET, "Test Fuse")

    def cut_fuselage_ribs(self):
        print("Cutting: fuselage and ribs...")
        # self.m.display_in_origin(self.fuselage_offset, True)
        # self.m.display_in_origin(self.rippen_cuted)
        self.fuselage_with_ribs = OAlgo.BRepAlgoAPI_Cut(self.fuselage_offset, self.rippen_cuted_form).Shape()
        # self.m.display_this_shape(self.fuselage_done, "Done")
        self.m.display_cut(self.fuselage_with_ribs, self.fuselage_offset, self.rippen_cuted_form, logging.NOTSET,
                           "Fuselage with ribs cutout")

    def create_hollow(self, offset=0.001):
        fuselage_offset = OOff.BRepOffsetAPI_MakeOffsetShape(self.fuselage_shape, -offset, 0.0001).Shape()
        self.m.display_this_shape(fuselage_offset, severity=logging.NOTSET)
        self.fuselage_hollow = OAlgo.BRepAlgoAPI_Cut(self.fuselage_shape, fuselage_offset).Shape()
        self.m.display_this_shape(self.fuselage_hollow, severity=logging.NOTSET, "")

    def offset_fuselage(self, offset=0.0008):
        self.fuselage_offset = OOff.BRepOffsetAPI_MakeOffsetShape(self.fuselage_shape, offset, 0.000001).Shape()
        msg = "Fuselage with an offset of " + str(offset) + " meters"
        self.m.display_this_shape(self.fuselage_offset, severity=logging.NOTSET, msg)

    def cut_wings_from_fuselage(self):
        self.fuselage_done = OAlgo.BRepAlgoAPI_Cut(self.fuselage_with_ribs, self.complete_wing).Shape()
        self.m.display_cut(self.fuselage_done, self.fuselage_with_ribs, self.complete_wing, logging.NOTSET, "", True)

    def test1(self):
        self.create_mainwing()
        self.create_fuselage()
        self.offset_fuselage()
        self.create_sharp_ribs()
        self.common_fuselage_ribs_cuted()
        self.cut_fuselage_ribs()
        self.cut_wings_from_fuselage()
        # slicer = ShapeSlicer(self.fuselage_done, 4, "fuselage", False)
        # slicer.slice2()
        # logging.debug("Starting to write STLS")
        # write_stls_srom_list(slicer.parts_list)
        # logging.debug("Finished to write STLS")
        # myZip.zip_stls2()
        logging.debug("Done")
        # self.m.start()

    def slicing_positions(self):
        result = []
        before_wing = get_koordinate(self.wing_shape, "x_min") - 0.0004
        after_wing = get_koordinate(self.wing_shape, "x_max") + 0.0004
        result.append(before_wing)
        result.append(after_wing)
        end_fuselage = get_koordinate(self.fuselage_shape, "x_max")
        split_rear_fuselage = (end_fuselage + after_wing) / 2
        result.append(split_rear_fuselage)
        result.append(end_fuselage)
        return result

    def create_tunnel(self, factor=0.3, radius=0.0024):
        y_max = self.fuselage_widht * factor
        y_min = -y_max
        z_max = self.fuselage_height * factor
        z_min = get_koordinate(self.wing_shape, "z_max") + 0.003
        cylinders = self.create_cylinder_reinforcemnt(radius, y_max, y_min, z_max, z_min)
        cylinders = OAlgo.BRepAlgoAPI_Common(self.fuselage_offset, cylinders).Shape()
        self.fuselage_done2 = OAlgo.BRepAlgoAPI_Fuse(self.fuselage_done, cylinders).Shape()
        self.m.display_fuse(self.fuselage_done2, self.fuselage_done, cylinders, logging.NOTSET)

    def create_hardware_oppening(self, lenght, width, height):
        box = OPrim.BRepPrimAPI_MakeBox().Shape()

    def create_harware_wingcutout_for_hardware(self):
        x, y, z, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        lenght, width, height = get_dimensions_from_Shape(self.complete_wing)
        width = self.fuselage_widht * 0.6
        box = OPrim.BRepPrimAPI_MakeBox(lenght, width, height).Shape()
        box = translate_shp(box, gp_Vec(x, -width / 2, z))
        wing_section = OAlgo.BRepAlgoAPI_Common(self.complete_wing, box).Shape()
        self.m.display_common(wing_section, box, self.complete_wing, logging.NOTSET)
        wing_section_offset = OOff.BRepOffsetAPI_MakeOffsetShape(wing_section, 0.003, 0.0001).Shape()
        self.m.display_this_shape(wing_section_offset, severity=logging.NOTSET)
        self.fuselage_done = OAlgo.BRepAlgoAPI_Cut(self.fuselage_wing_cutout, wing_section_offset).Shape()
        self.m.display_cut(self.fuselage_done, self.fuselage_wing_cutout, wing_section_offset, logging.NOTSET)
        return wing_section_offset

    def create_harware_wingcutout_for_hardware2(self):
        x, y, z, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        lenght, width, height = get_dimensions_from_Shape(self.wing_shape)
        box = OPrim.BRepPrimAPI_MakeBox(lenght, width, height).Shape()
        ypos = self.fuselage_widht * 0.3
        box1 = translate_shp(box, gp_Vec(x, ypos, z))
        ypos = -ypos - width
        box2 = translate_shp(box, gp_Vec(x, ypos, z))
        wing_section1 = OAlgo.BRepAlgoAPI_Cut(self.complete_wing, box1).Shape()
        self.m.display_cut(wing_section1, self.complete_wing, box1, logging.NOTSET)
        wing_section = OAlgo.BRepAlgoAPI_Cut(wing_section1, box2).Shape()
        self.m.display_cut(wing_section, wing_section1, box2, logging.NOTSET)
        wing_section_offset = OOff.BRepOffsetAPI_MakeOffsetShape(wing_section, 0.003, 0.0001).Shape()
        self.m.display_this_shape(wing_section_offset, severity=logging.NOTSET)
        self.fuselage_done = OAlgo.BRepAlgoAPI_Cut(self.fuselage_wing_cutout, wing_section_offset).Shape()
        self.m.display_cut(self.fuselage_done, self.fuselage_wing_cutout, wing_section_offset, logging.NOTSET)
        return wing_section_offset

    def create_harware_wingcutout_for_hardware3(self):
        x, y, z, xmax, ymax, zmax = get_koordinates(self.wing_shape)
        lenght, width, height = get_dimensions_from_Shape(self.wing_shape)
        box = OPrim.BRepPrimAPI_MakeBox(lenght, width, height).Shape()
        ypos = self.fuselage_widht * 0.3
        box1 = translate_shp(box, gp_Vec(x, ypos, z))
        ypos = -ypos - width
        box2 = translate_shp(box, gp_Vec(x, ypos, z))
        wing_section1 = OAlgo.BRepAlgoAPI_Cut(self.complete_wing, box1).Shape()
        self.m.display_cut(wing_section1, self.complete_wing, box1, logging.NOTSET)
        wing_section = OAlgo.BRepAlgoAPI_Cut(wing_section1, box2).Shape()
        self.m.display_cut(wing_section, wing_section1, box2, logging.NOTSET)
        wing_section_offset = OOff.BRepOffsetAPI_MakeOffsetShape(wing_section, 0.003, 0.0001).Shape()
        self.m.display_this_shape(wing_section_offset, severity=logging.NOTSET)
        temp = self.fuselage_offset
        temp = OAlgo.BRepAlgoAPI_Cut(self.fuselage_offset, wing_section_offset).Shape()
        self.m.display_cut(temp, self.fuselage_offset, wing_section_offset, logging.NOTSET)
        self.fuselage_offset = temp
        return wing_section_offset

    def create_fuselage_with_ribs(self):
        self.create_fuselage()
        self.offset_fuselage()
        # a.create_harware_wingcutout_for_hardware3()
        self.create_sharp_ribs()
        self.common_fuselage_ribs_cuted()
        self.cut_fuselage_ribs()
        # self.cut_wings_from_fuselage()
        # self.create_harware_wingcutout_for_hardware2()
        # self.create_tunnel()

    def list_for_pipe1(self, servo_y_pos, zmax, zmin):
        points = []
        y_pos = 0.00
        points.append(Ogp.gp_Pnt(zmax, y_pos, 0.0))
        logging.debug(f"{y_pos=} {zmax=}")
        z = zmin + 0.005
        points.append(Ogp.gp_Pnt(z, y_pos, 0.0))
        logging.debug(f"{y_pos=} {z=}")
        points.append(Ogp.gp_Pnt(z, servo_y_pos, 0.0))
        logging.debug(f"{servo_y_pos=} {z=}")
        return points, z, y_pos

    def list_for_pipe2(self):
        points = []
        y_pos = 0.02
        x_pos = 0.02
        points.append(Ogp.gp_Pnt(x_pos, y_pos, 0.0))
        points.append(Ogp.gp_Pnt(0.0, y_pos, 0.0))
        points.append(Ogp.gp_Pnt(0.0, 0.0, 0.0))
        return points

    def create_pipe(self, wing_shape):
        xmin, ymin, zmin, xmax, ymax, zmax = get_koordinates(wing_shape)
        wing_lenght, wing_width, wing_height = get_dimensions_from_Shape(wing_shape)
        servo_pos = wing_width * 0.45
        points, x, y = self.list_for_pipe1(servo_pos, zmax, zmin)
        mcp = CabelPipe(points, 0.003)
        L_pipe = []
        L_pipe.append(mcp.get_pipe())
        self.m.display_in_origin(L_pipe[-1], logging.NOTSET)

        points2 = self.list_for_pipe2()
        mcp = CabelPipe(points2, 0.003)
        zL_pipe = []
        zL_pipe.append(mcp.get_pipe())
        zL_pipe.append(OExs.rotate_shape(zL_pipe[-1], gp_OY(), 90))
        zL_pipe.append(OExs.translate_shp(zL_pipe[-1], Ogp.gp_Vec(x, servo_pos, 0.0)))

        L_pipe.append(OAlgo.BRepAlgoAPI_Fuse(L_pipe[-1], zL_pipe[-1]).Shape())
        L_pipe.append(OExs.rotate_shape(L_pipe[-1], gp_OY(), -90))
        x_pos = ((2 / 3) * wing_lenght) + xmin
        z_pos = 0.005
        y_pos = 0.015
        L_pipe.append(OExs.translate_shp(L_pipe[-1], Ogp.gp_Vec(x_pos, y_pos, z_pos)))
        return L_pipe[-1]


if __name__ == "__main__":
    a = aircombat_test(True)
    a.test1()
    # a.create_mainwing()

    '''
    a.create_offset_wing()
    a.create_right_wing()
    wing_slicer= ShapeSlicer(a.wing_done,5,"wing")
    pos_list=wing_slicer.slicing_postion_wing(a.wing_shape)
    wing_slicer.slice_with_list_common_y(pos_list)
    #a.create_fuselage_with_ribs()
    

    a.create_fuselage()
    a.offset_fuselage()
    #a.create_harware_wingcutout_for_hardware3() 
    a.create_sharp_ribs() 
    a.common_fuselage_ribs_cuted()
    a.cut_fuselage_ribs()
    a.cut_wings_from_fuselage()
    #a.create_harware_wingcutout_for_hardware2()
    a.create_tunnel()

    slicer=ShapeSlicer(a.fuselage_done2,4,"fuselage")
    #slicer.slice2()
    pos_list=slicer.slicing_positions2(a.wing_shape, a.fuselage_shape)
    slicer.slice_with_list_common(pos_list)
    '''
    # slicer=ShapeSlicer(a.fuselage_done2,4,"fuselage")
    # slicer.slice()
    # write_stls_srom_list(wing_slicer.parts_list,"fuselage")
    # myZip.zip_stls2()

    a.m.start()
