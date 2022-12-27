import logging
import sys
from pathlib import Path

import tigl3.geometry as tgl_geom
from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Compound, TopoDS_CompSolid
from tigl3.configuration import CCPACSConfiguration, CCPACSEnginePositions, CCPACSEnginePosition

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.ConstructionStepNode import ConstructionStepNode, JSONStepNode, ConstructionRootNode
from Airplane.Fuselage.EngineMountFactory import EngineMountFactory
from Extra.BooleanOperationsForLists import BooleanCADOperation, fuse_list_of_shapes

from Extra.ConstructionStepsViewer import *


# === BEGIN: Basic shape operations ===
class Fuse2ShapesCreator(AbstractShapeCreator):
    """
    Fusing shape B with shape A.
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None):
        self.identifier = creator_id
        self.shape_a = shape_a
        self.shape_b = shape_b

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.return_needed_shapes([self.shape_a, self.shape_b], input_shapes, **kwargs)
        shape_list = list(shapes.values())
        logging.info(f"fusing shapes '{list(shapes.keys())[0]}' + '{list(shapes.keys())[1]}' --> '{self.identifier}'")

        fused_shape = BooleanCADOperation.fuse_shapes(shape_list[0], shape_list[1], self.identifier)
        ConstructionStepsViewer.instance().display_fuse(fused_shape, shape_list[0], shape_list[1], logging.INFO)

        return {self.identifier: fused_shape}


class Cut2ShapesCreator(AbstractShapeCreator):
    """
    Cut the subtrahend from the minuend (minuend - subtrahend = new_shape).
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str,
                 minuend: str = None,
                 subtrahend: str = None):
        self.identifier = creator_id
        self.minuend = minuend
        self.subtrahend = subtrahend

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.return_needed_shapes([self.minuend, self.subtrahend], input_shapes, **kwargs)
        shape_list = list(shapes.values())
        logging.info(f"cutting shapes '{list(shapes.keys())[0]}' - '{list(shapes.keys())[1]}' --> '{self.identifier}'")

        from Extra.BooleanOperationsForLists import BooleanCADOperation
        shape__minuend = shape_list[0]
        shape__subtrahend = shape_list[1]
        cut_shape = BooleanCADOperation.cut_shape_from_shape(shape__minuend,
                                                             shape__subtrahend,
                                                             self.identifier)
        ConstructionStepsViewer.instance().display_cut(cut_shape, shape__minuend, shape__subtrahend, logging.INFO)

        return {self.identifier: cut_shape}


class SimpleOffsetShapeCreator(AbstractShapeCreator):
    """
    Creates a simple offset shape from given shape or the take the first input_shape,
    which is bigger(+)/smaller(-) bei the given <offset>[m].
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str,
                 offset: float,
                 shape: str = None,
                 ):
        self.identifier = creator_id
        self.offset = offset
        self.shape = shape

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.return_needed_shapes([self.shape], input_shapes, **kwargs)
        shape_list = list(shapes.values())
        logging.info(f"offset shape '{list(shapes.keys())[0]}' by {self.offset}m --> '{self.identifier}'")

        shape = shape_list[0]

        from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
        from OCC.Core.BRepBuilderAPI import BRepBuilderAPI_MakeSolid

        offset_maker: BRepOffsetAPI_MakeOffsetShape = BRepOffsetAPI_MakeOffsetShape()
        offset_maker.PerformByJoin(shape.shape(), self.offset, self.offset / 100)
        logging.debug(f"{type(offset_maker.Shape())} == {type(OTopo.TopoDS_Shell())}")
        solid_maker = BRepBuilderAPI_MakeSolid(offset_maker.Shape())
        solid_shape = solid_maker.Solid()
        result = TGeo.CNamedShape(solid_shape, f"{shape.name()}_offset")

        msg = f"Fuselage with {str(self.offset)=} meters"
        ConstructionStepsViewer.instance().display_this_shape(result, severity=logging.INFO, msg=msg)

        return {self.identifier: result}


class Intersect2ShapesCreator(AbstractShapeCreator):
    """
    Intersect the sahpe A with shape B (minuend / subtrahend = new_shape).
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None):
        self.identifier = creator_id
        self.shape_a = shape_a
        self.shape_b = shape_b

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.return_needed_shapes([self.shape_a, self.shape_b], input_shapes, **kwargs)
        shape_list = list(shapes.values())
        logging.info(
            f"intersecting shapes '{list(shapes.keys())[0]}' / '{list(shapes.keys())[1]}' --> '{self.identifier}'")

        from Extra.BooleanOperationsForLists import BooleanCADOperation

        shape__a = shape_list[0]
        shape__b = shape_list[1]
        cut_shape = BooleanCADOperation.intersect_shape_with_shape(shape__a,
                                                                   shape__b,
                                                                   self.identifier)
        ConstructionStepsViewer.instance().display_common(cut_shape, shape__a, shape__b, logging.INFO)

        return {self.identifier: cut_shape}


class ScaleRotateTranslateCreator(AbstractShapeCreator):
    """
    Scale, rotate (x,y,z) and then translate the shape.
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str,
                 shape_id: str,
                 scale: float = 1.0,
                 rot_x: float = .0,
                 rot_y: float = .0,
                 rot_z: float = .0,
                 trans_x: float = .0,
                 trans_y: float = .0,
                 trans_z: float = .0):
        self.identifier = creator_id
        self.shape_id = shape_id
        self.trans_x = trans_x
        self.trans_y = trans_y
        self.trans_z = trans_z
        self.rot_x = rot_x
        self.rot_y = rot_y
        self.rot_z = rot_z
        self.scale = scale

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.return_needed_shapes([self.shape_id], input_shapes, **kwargs)
        shape_list = list(shapes.values())
        shape = shape_list[0]
        logging.info(
            f"scale {self.scale}, rotate ({self.rot_x}, {self.rot_y}, {self.rot_z}) and translate ({self.trans_x}, {self.trans_y}, {self.trans_z}) '{list(shapes.keys())[0]}' --> '{self.identifier}'")
        trans_shape = self.transform_by(shape,
                                        trans_x=self.trans_x,
                                        trans_y=self.trans_y,
                                        trans_z=self.trans_z,
                                        rot_x=self.rot_x,
                                        rot_y=self.rot_y,
                                        rot_z=self.rot_z,
                                        scale=self.scale)
        trans_shape.set_name(self.identifier)
        ConstructionStepsViewer.instance().display_this_shape(trans_shape, severity=logging.INFO)

        return {self.identifier: trans_shape}

    @classmethod
    def transform_by(cls, shape: tgl_geom.CNamedShape,
                     scale: float = 1.0,
                     rot_x: float = .0,
                     rot_y: float = .0,
                     rot_z: float = .0,
                     trans_x: float = .0,
                     trans_y: float = .0,
                     trans_z: float = .0
                     ) -> tgl_geom.CNamedShape:

        trafo = tgl_geom.CTiglTransformation()
        trafo.add_scaling(scale, scale, scale)
        trafo.add_rotation_x(rot_x)
        trafo.add_rotation_y(rot_y)
        trafo.add_rotation_z(rot_z)
        trafo.add_translation(trans_x, trans_y, trans_z)

        try:
            topods: TopoDS_Shape = shape.shape()
            topods_trans: TopoDS_Shape = trafo.transform(topods)
            trans_shape = tgl_geom.CNamedShape(topods_trans, f"{shape.name()}_transformed")
        except RuntimeError as err:
            logging.fatal(f"could not tansform shape '{shape.name()}' got error: {err}")
            return shape

        return trans_shape


        # trafo = tgl_geom.CTiglTransformation()
        # trafo.add_scaling(scale, scale, scale)
        # trafo.add_rotation_x(rot_x)
        # trafo.add_rotation_y(rot_y)
        # trafo.add_rotation_z(rot_z)
        # trafo.add_translation(trans_x, trans_y, trans_z)
        # topods = trafo.transform(shape.shape())
        # return tgl_geom.CNamedShape(topods, f"{shape.name()}_transformed")


# === END basic shape operations ===


class IgesImportCreator(AbstractShapeCreator):
    """
    Import an iges file as a shape.
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, iges_file: str,
                 trans_x: float = .0,
                 trans_y: float = .0,
                 trans_z: float = .0,
                 rot_x: float = .0,
                 rot_y: float = .0,
                 rot_z: float = .0,
                 scale: float = 1.0
                 ):
        self.identifier = creator_id
        self.iges_file = iges_file
        self.trans_x = trans_x
        self.trans_y = trans_y
        self.trans_z = trans_z
        self.rot_x = rot_x
        self.rot_y = rot_y
        self.rot_z = rot_z
        self.scale = scale

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(f"importing iges model '{self.iges_file}' --> '{self.identifier}'")

        from OCC.Extend.DataExchange import read_iges_file
        topods: list[TopoDS_Shape] = read_iges_file(self.iges_file,
                                                    return_as_shapes=True,
                                                    verbosity=True,
                                                    visible_only=True)
        topo = fuse_list_of_shapes(topods) if len(topods) > 1 else topods[0]

        shape = tgl_geom.CNamedShape(topo, self.identifier)

        trans_shape = ScaleRotateTranslateCreator.transform_by(shape,
                                                 scale=self.scale,
                                                 rot_x=self.rot_x,
                                                 rot_y=self.rot_y,
                                                 rot_z=self.rot_z,
                                                 trans_x=self.trans_x,
                                                 trans_y=self.trans_y,
                                                 trans_z=self.trans_z)

        # ConstructionStepsViewer.instance().display_this_shape(trans_shape, severity=logging.INFO)

        return {self.identifier: trans_shape}

    def _iges_importer(self, path_) -> TopoDS_Shape:

        from OCC.Extend.DataExchange import read_iges_file
        shapes = read_iges_file(path_, return_as_shapes=True, verbosity=False, visible_only=True)
        return shapes


class StepImportCreator(AbstractShapeCreator):
    """
    Import an iges file as a shape.
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, step_file: str,
                 trans_x: float = .0,
                 trans_y: float = .0,
                 trans_z: float = .0,
                 rot_x: float = .0,
                 rot_y: float = .0,
                 rot_z: float = .0,
                 scale: float = 1.0
                 ):
        self.identifier = creator_id
        self.step_file = step_file
        self.trans_x = trans_x
        self.trans_y = trans_y
        self.trans_z = trans_z
        self.rot_x = rot_x
        self.rot_y = rot_y
        self.rot_z = rot_z
        self.scale = scale

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(f"importing step model '{self.step_file}' --> '{self.identifier}'")

        topods = self._step_importer(self.step_file)
        shape = tgl_geom.CNamedShape(topods, self.identifier)
        trans_shape = ScaleRotateTranslateCreator.transform_by(shape,
                                                 scale=self.scale,
                                                 rot_x=self.rot_x,
                                                 rot_y=self.rot_y,
                                                 rot_z=self.rot_z,
                                                 trans_x=self.trans_x,
                                                 trans_y=self.trans_y,
                                                 trans_z=self.trans_z)

        ConstructionStepsViewer.instance().display_this_shape(trans_shape, severity=logging.INFO)

        return {self.identifier: trans_shape}

    def _step_importer(self, path_) -> TopoDS_Shape:

        from OCC.Extend.DataExchange import read_step_file
        shapes = read_step_file(path_)
        return shapes


class ExportToIgesCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str] = None):
        self.identifier: str = creator_id
        self.file_path: str = file_path
        self.shapes_to_export: list[str] = shapes_to_export

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        all_shapes = AbstractShapeCreator.check_if_shapes_are_available(self.shapes_to_export, **kwargs)
        logging.info(f"exporting iges model '{self.identifier}' --> '{self.file_path}'")

        from tigl3.import_export_helper import export_shapes
        path = os.path.join(self.file_path, f"{self.identifier}.igs")
        export_shapes(list(all_shapes.values()), path, deflection=0.0001)

        return all_shapes


class ExportToStepCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, file_path: str, shapes_to_export: list[str] = None):
        self.identifier: str = creator_id
        self.file_path: str = file_path
        self.shapes_to_export: list[str] = shapes_to_export

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        all_shapes = AbstractShapeCreator.check_if_shapes_are_available(self.shapes_to_export, **kwargs)
        logging.info(f"exporting step model '{self.identifier}' --> '{self.file_path}'")

        # ===============
        from OCC.Core.STEPControl import STEPControl_Controller, STEPControl_Writer, STEPControl_AsIs

        st = STEPControl_Controller()
        st.Init()

        step_writer = STEPControl_Writer()
        dd = step_writer.WS().TransferWriter().FinderProcess()
        from OCC.Core.Interface import Interface_Static_SetCVal, Interface_Static_SetIVal

        # defines the version of schema used for the output STEP file:
        # 1 or AP214CD (default): AP214, CD version (dated 26 November 1996),
        # 2 or AP214DIS: AP214, DIS version (dated 15 September 1998).
        # 3 or AP203: AP203, possibly with modular extensions (depending on data written to a file).
        # 4 or AP214IS: AP214, IS version (dated 2002)
        # 5 or AP242DIS: AP242, DIS version.
        Interface_Static_SetCVal("write.step.schema", "AP214CD")

        # 0 (Off) : (default) writes STEP files without assemblies.
        # 1 (On) : writes all shapes in the form of STEP assemblies.
        # 2 (Auto) : writes shapes having a structure of (possibly nested) TopoDS_Compounds in the form of STEP
        #    assemblies, single shapes are written without assembly structures.
        Interface_Static_SetIVal("write.step.assembly", 0)  #

        Interface_Static_SetCVal("write.step.unit", "MM")

        Interface_Static_SetIVal("write.precision.mode", 1)

        for shape in all_shapes.values():
            t_shape = ScaleRotateTranslateCreator.transform_by(shape=shape, scale=1000.0)
            return_status = step_writer.Transfer(t_shape.shape(), STEPControl_AsIs)
        step_path = os.path.join(self.file_path, f"{self.identifier}.stp")
        step_writer.Write(step_path)
        # ===============

        return all_shapes


class ExportToStlCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str,
                 mode: str = "binary",  # "binary" od "ascii"
                 linear_deflection: float = 0.00001,
                 additional_shapes_to_export: list[str] = None):
        self.identifier: str = creator_id
        self.mode = mode
        self.linear_deflection = linear_deflection
        self.additional_shapes_to_export: list[str] = additional_shapes_to_export

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        all_shapes = AbstractShapeCreator.check_if_shapes_are_available(self.additional_shapes_to_export, **kwargs)
        all_shapes.update(input_shapes)

        import stl_exporter.Exporter as Exporter
        stl_exporter = Exporter.Exporter()
        stl_exporter.write_stls_from_list(all_shapes.values(), mode=self.mode, linear_deflection=self.linear_deflection)
        return all_shapes


# === END basic import export operations ===


class EngineMountShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, mount_plate_thickness: float, engine_screw_hole_circle: float,
                 engine_total_cover_length: float, engine_mount_box_length: float, engine_down_thrust_deg: float,
                 engine_side_thrust_deg: float, engine_screw_din_diameter: float, engine_screw_length: float,
                 fuselage_index: int, engine_index: int, cpacs_configuration: CCPACSConfiguration = None):
        """

        :param engine_index:
        :param creator_id:
        :param mount_plate_thickness: thickness of the mount backplate
        :param engine_screw_hole_circle: the diameter of the screw circle of the engine mount
        :param engine_total_cover_length: the length of the engine from where it touches the mount to the point which should be outside the cape
        :param engine_mount_box_length: length of the box, the engine is screwd onto. (can be used to give place for a shaft)
        :param engine_down_thrust_deg: down thrust in degree
        :param engine_side_thrust_deg: side thrust in degree
        :param engine_screw_din_diameter: diameter of the screws used to fix the engine (e.g. 4 for M4)
        :param engine_screw_length: length of the screws used to fix the engine
        :param fuselage_index:
        :param cpacs_configuration:
        """
        self.engine_index = engine_index
        self.engine_screw_length = engine_screw_length
        self.identifier = creator_id
        self.engine_screw_hole_circle = engine_screw_hole_circle
        self.engine_total_cover_length = engine_total_cover_length
        self.engine_mount_box_length = engine_mount_box_length
        self.engine_down_thrust_deg = engine_down_thrust_deg
        self.engine_side_thrust_deg = engine_side_thrust_deg
        self.engine_screw_din_diameter = engine_screw_din_diameter
        self.fuselage_index = fuselage_index
        self.mount_plate_thickness = mount_plate_thickness
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        _engine_mount_factory = EngineMountFactory()
        mount = _engine_mount_factory.create_engine_mount(mount_plate_thickness=self.mount_plate_thickness,
                                                          engine_screw_hole_circle=self.engine_screw_hole_circle,
                                                          engine_total_cover_length=self.engine_total_cover_length,
                                                          engine_mount_box_length=self.engine_mount_box_length,
                                                          engine_down_thrust_deg=self.engine_down_thrust_deg,
                                                          engine_side_thrust_deg=self.engine_side_thrust_deg,
                                                          engine_screw_din_diameter=self.engine_screw_din_diameter,
                                                          engine_screw_length=self.engine_screw_length,
                                                          fuselage_index=self.fuselage_index,
                                                          engine_index=self.engine_index,
                                                          cpacs_configuration=self._cpacs_configuration)
        ConstructionStepsViewer.instance().display_this_shape(mount, logging.INFO, msg=f"{self.identifier}")
        return {str(self.identifier): mount}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class SliceShapesCreator(AbstractShapeCreator):
    """
    Slices the given shape in <number_of_parts> parts along the x-axis. And returns a dictionary with the parts.
    The naming convention for a key is <identifier>[<part_number>], e.g. {"fuselage[0]": <CNamedShape>, "fuselage[1]": <CNamedShape>}
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, number_of_parts: int):
        self.identifier = creator_id
        self.number_of_parts = number_of_parts

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        from Extra.ShapeSlicer import ShapeSlicer
        parts: dict[str, tgl_geom.CNamedShape] = {}
        for shape in input_shapes.values():
            my_slicer = ShapeSlicer(shape, self.number_of_parts)
            my_slicer.slice_by_cut()
            for i, s in enumerate(my_slicer.parts_list):
                parts[f"{self.identifier}[{i}]"] = s
                ConstructionStepsViewer.instance().display_this_shape(s, logging.INFO, msg=f"{self.identifier}[{i}]")
        return parts


class EngineCapeShapeCreator(AbstractShapeCreator):
    """
    Creates an engine cape <identifier>.cape and fuselage loft without the cape <identifier>.loft, by cutting the cape
    of the full fuselage loft.
    """

    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 engine_index: int,
                 engine_total_cover_length: float,
                 engine_mount_box_length: float,
                 mount_plate_thickness: float,
                 cpacs_configuration: CCPACSConfiguration = None):
        self.identifier = creator_id
        self.fuselage_index = fuselage_index
        self.mount_plate_thickness = mount_plate_thickness
        self.engine_total_cover_length = engine_total_cover_length
        self.engine_mount_box_length = engine_mount_box_length
        self.engine_index = engine_index
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        engine_positions: CCPACSEnginePositions = self._cpacs_configuration.get_engine_positions()
        engine_position: CCPACSEnginePosition = engine_positions.get_engine_position(self.engine_index)
        engine_position_transformation: tgl_geom.CCPACSTransformation = engine_position.get_transformation()
        engine_scaling: tgl_geom.CTiglPoint = engine_position_transformation.get_scaling()
        engine_length = engine_scaling.x

        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        shapes = FuselageFactory.create_engine_cape(cpacs_configuration=self._cpacs_configuration,
                                                    fuselage_index=self.fuselage_index,
                                                    mount_plate_thickness=self.mount_plate_thickness,
                                                    motor_cutout_length=self.engine_total_cover_length
                                                                        + self.engine_mount_box_length)
        ConstructionStepsViewer.instance().display_slice_x(shapes, logging.INFO, name=f"{self.identifier}")

        return {f"{self.identifier}.cape": shapes[0], f"{self.identifier}.loft": shapes[1]}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class FuselageReinforcementShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 fuselage_loft: str,
                 right_main_wing_index: int,
                 rib_width: float,
                 ribcage_factor: float,
                 reinforcement_pipes_radius: float,
                 cpacs_configuration: CCPACSConfiguration = None
                 ):
        self.identifier: str = creator_id
        self.fuselage_index = fuselage_index
        self.fuselage_loft = fuselage_loft
        self.right_main_wing_index = right_main_wing_index
        self.rib_width = rib_width
        self.ribcage_factor = ribcage_factor
        self.reinforcement_pipes_radius = reinforcement_pipes_radius
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        all_shapes = AbstractShapeCreator.check_if_shapes_are_available([self.fuselage_loft], **kwargs)

        shape__fuselage_reinforcement = FuselageFactory.create_fuselage_reinforcement(
            cpacs_configuration=self._cpacs_configuration,
            fuselage_index=self.fuselage_index,
            reinforcement_pipes_radius=self.reinforcement_pipes_radius,
            rib_width=self.rib_width,
            ribcage_factor=self.ribcage_factor,
            right_main_wing_index=self.right_main_wing_index,
            fuselage_loft=all_shapes[self.fuselage_loft])

        ConstructionStepsViewer.instance().display_this_shape(
            shape__fuselage_reinforcement, logging.INFO, msg=f"{self.identifier}")

        return {str(self.identifier): shape__fuselage_reinforcement}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class FuselageWingSupportShapeCreator(AbstractShapeCreator):
    """
    Creates wing support by using vertical cube shaped ribs.

    TODO: should be improved to ribs that form a trapezoid 50° angles, so printing will be easier.
         /-----\
        /_______\
    """

    def __init__(self, creator_id: str, fuselage_index: int, right_main_wing_index: int, rib_quantity: int,
                 rib_width: float, rib_height_factor: float, cpacs_configuration: CCPACSConfiguration = None):
        self.identifier: str = creator_id
        self.fuselage_index: int = fuselage_index
        self.right_main_wing_index: int = right_main_wing_index
        self.rib_quantity: int = rib_quantity
        self.rib_width: float = rib_width
        self.rib_height_factor: float = rib_height_factor
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        from Airplane.Fuselage.FuselageFactory import FuselageFactory

        shape__wing_support = FuselageFactory.create_wing_support_shape(self._cpacs_configuration, self.fuselage_index,
                                                                        self.right_main_wing_index, self.rib_quantity,
                                                                        self.rib_width, self.rib_height_factor)
        ConstructionStepsViewer.instance().display_this_shape(
            shape__wing_support, logging.INFO, msg=f"{self.identifier}")
        return {str(self.identifier): shape__wing_support}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class FuselageElectronicsAccessCutOutShapeCreator(AbstractShapeCreator):
    """
    Creates a cutout shape for creating the access to the electronics depending on the wing position ('top',
    'middle', 'bottom')
    """

    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 ribcage_factor: float,
                 right_main_wing_index: int,
                 wing_position: str = None,
                 cpacs_configuration: CCPACSConfiguration = None
                 ):
        self.identifier: str = creator_id
        self.fuselage_index = fuselage_index
        self.right_main_wing_index = right_main_wing_index
        self._cpacs_configuration = cpacs_configuration
        self.ribcage_factor = ribcage_factor
        self.wing_position = wing_position

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        shape__hardware_cutout = FuselageFactory.create_hardware_cutout(cpacs_configuration=self._cpacs_configuration,
                                                                        fuselage_index=self.fuselage_index,
                                                                        ribcage_factor=self.ribcage_factor,
                                                                        right_main_wing_index=self.right_main_wing_index,
                                                                        position=self.wing_position)
        ConstructionStepsViewer.instance().display_this_shape(
            shape__hardware_cutout, logging.INFO, msg=f"{self.identifier}")
        return {str(self.identifier): shape__hardware_cutout}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class WingAttachmentBoltHolesShapeCreator(AbstractShapeCreator):
    """
    Create two bolts along the roll-axis through the fuselage,
    to hold some rubber band.
    """

    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 right_main_wing_index: int,
                 cpacs_configuration: CCPACSConfiguration = None
                 ):
        self.identifier: str = creator_id
        self.fuselage_index = fuselage_index
        self.right_main_wing_index = right_main_wing_index
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        overlap_dimensions = FuselageFactory.overlap_fuselage_wing_dimensions(self._cpacs_configuration,
                                                                              self.fuselage_index,
                                                                              self.right_main_wing_index)
        from Airplane.Fuselage.FuselageCutouts import FuselageCutouts
        shape__bolt_holes = FuselageCutouts.create_bolt_hole(overlap_dimensions)
        ConstructionStepsViewer.instance().display_this_shape(
            shape__bolt_holes, logging.INFO, msg=f"{self.identifier}")
        return {str(self.identifier): shape__bolt_holes}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class FullWingLoftShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 right_main_wing_index: int,
                 cpacs_configuration: CCPACSConfiguration = None,
                 ):
        self.identifier: str = creator_id
        self.right_main_wing_index = right_main_wing_index
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        complete_wing = BooleanCADOperation.fuse_shapes(
            self._cpacs_configuration.get_wing(self.right_main_wing_index).get_loft(),
            self._cpacs_configuration.get_wing(self.right_main_wing_index).get_mirrored_loft(),
            self.identifier)

        ConstructionStepsViewer.instance().display_fuse(complete_wing, self._cpacs_configuration.get_wing(
            self.right_main_wing_index).get_loft(), self._cpacs_configuration.get_wing(
            self.right_main_wing_index).get_mirrored_loft(), logging.INFO)
        ConstructionStepsViewer.instance().display_this_shape(
            complete_wing, logging.INFO, msg=f"{self.identifier}")
        return {str(self.identifier): complete_wing}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


if __name__ == "__main__":
    CPACS_FILE_NAME = "aircombat_v14"
    NUMBER_OF_CUTS = 5
    import logging
    import Extra.tigl_extractor as tg
    import json
    from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder

    logging.basicConfig(format='%(levelname)s:%(module)s:%(filename)s(%(lineno)d):%(funcName)s(): %(message)s',
                        level=logging.DEBUG, stream=sys.stdout)
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance

    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance() \
        .get_configuration(tigl_h._handle.value)

    # ============
    full_wing_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("wings",
                                 right_main_wing_index=1))

    full_wing_file_path = "../components/constructions/full_wing.json"
    full_wing_file = open(full_wing_file_path, "w")
    json.dump(fp=full_wing_file, obj=full_wing_loft_node, indent=4, cls=GeneralJSONEncoder)
    full_wing_file.close()

    # =============
    # defining as simple root node
    root_node = ConstructionRootNode(creator_id="root")

    full_elevator_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("elevator",
                                 right_main_wing_index=2))
    root_node.append(full_elevator_loft_node)
    # -> "elevator"

    full_rudder_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("rudder",
                                 right_main_wing_index=3))
    full_elevator_loft_node.append(full_rudder_loft_node)
    # -> "rudder"

    cut_rudder_from_elevator_node = ConstructionStepNode(
        Cut2ShapesCreator("rudder",
                          # minuend="rudder",
                          subtrahend="elevator"))
    full_rudder_loft_node.append(cut_rudder_from_elevator_node)
    # "rudder" - "elevator" -> "rudder_with_slot"

    elevator_slicer_node = ConstructionStepNode(
        SliceShapesCreator("elevators", number_of_parts=2))
    full_elevator_loft_node.append(elevator_slicer_node)
    # "elevator" -> "elevators[0]", "elevators[1]"

    engine_mount_node = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount",
                                mount_plate_thickness=0.005,
                                engine_screw_hole_circle=0.042,
                                engine_total_cover_length=0.0452,
                                engine_mount_box_length=0.0133*2.5,  # 0.0133,
                                engine_down_thrust_deg=None,
                                engine_side_thrust_deg=None,
                                engine_screw_din_diameter=0.0032,
                                engine_screw_length=0.016,
                                fuselage_index=1,
                                engine_index=1))
    root_node.append(engine_mount_node)
    # -> "engine_mount"

    brushless_shape_import = ConstructionStepNode(
        IgesImportCreator("brushless",
                          iges_file="../components/brushless/DPower_AL3542-5_AL3542-7_AL35-09_v2.iges",
                          trans_x=.0,
                          trans_y=.0,
                          trans_z=.0,
                          rot_x=.0,
                          rot_y=-2.5,
                          rot_z=-2.5,
                          scale=0.001))
    root_node.append(brushless_shape_import)

    engine_cape_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape",
                               engine_index=1,
                               fuselage_index=1,
                               engine_total_cover_length=0.0452,
                               engine_mount_box_length=0.0133 * 2.5,
                               mount_plate_thickness=0.005))
    root_node.append(engine_cape_node)
    # -> "engine_cape.cape", "engine_cape.loft"

    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement",
                                          fuselage_index=1,
                                          fuselage_loft="engine_cape.loft",
                                          right_main_wing_index=1,
                                          ribcage_factor=0.5,
                                          rib_width=0.001,
                                          reinforcement_pipes_radius=0.002))
    engine_cape_node.append(fuselage_reinforcement_node)
    # "engine_cape.loft" -> "fuselage_reinforcement"

    servo_shape_import = ConstructionStepNode(
        IgesImportCreator("servo",
                          iges_file="../components/servos/unknown/Servo.iges",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=.0,
                          rot_y=90.0,
                          rot_z=-90.0 + 3.4,
                          scale=0.001))
    fuselage_reinforcement_node.append(servo_shape_import)
    # -> "servo"

    servo_model_import = ConstructionStepNode(
        StepImportCreator("servo_model",
                          step_file="../components/servos/AS215BBMG v4.step",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=90.0,
                          rot_y=0.0,
                          rot_z=3.4,
                          scale=0.001))
    root_node.append(servo_model_import)
    # -> "servo"

    fuse_servo_with_fuselage = ConstructionStepNode(
        Fuse2ShapesCreator("fuselage_reinforcement",
                           shape_a="fuselage_reinforcement",
                           # shape_b="servo"
                           ))
    servo_shape_import.append(fuse_servo_with_fuselage)
    # "fuselage_reinforcement" + "servo" -> "reinforcement3"

    wing_support_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("wing_support",
                                        fuselage_index=1,
                                        right_main_wing_index=1,
                                        rib_quantity=6,
                                        rib_width=0.0008,
                                        rib_height_factor=1))
    fuse_servo_with_fuselage.append(wing_support_node)
    # -> "wing_support"

    fuse_reinforcement_wing_sup_node = ConstructionStepNode(
        Fuse2ShapesCreator("fuselage_reinforcement",
                           shape_a="fuselage_reinforcement",
                           # shape_b="wing_support"
                           ))
    wing_support_node.append(fuse_reinforcement_wing_sup_node)
    # "reinforcement3" + "wing_support" -> "reinforcement0"

    full_elevator_support_loft_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("elevator_support",
                                        fuselage_index=1,
                                        right_main_wing_index=2,
                                        rib_quantity=8,
                                        rib_width=0.0004,
                                        rib_height_factor=20))
    fuse_reinforcement_wing_sup_node.append(full_elevator_support_loft_node)
    # -> "elevator_support"

    fuse_reinforcement_elevator_sup_node = ConstructionStepNode(
        Fuse2ShapesCreator("fuselage_reinforcement",
                           shape_a="fuselage_reinforcement",
                           # shape_b="elevator_support"
                           ))
    full_elevator_support_loft_node.append(fuse_reinforcement_elevator_sup_node)
    # "reinforcement0 + "elevator_support" -> "reinforcement1"

    electronics_access_node = ConstructionStepNode(
        FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout",
                                                    fuselage_index=1,
                                                    ribcage_factor=0.5,
                                                    right_main_wing_index=1,
                                                    wing_position=None))
    fuse_reinforcement_elevator_sup_node.append(electronics_access_node)
    # -> "electronics_cutout"

    reinforcement_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_reinforcement",
                          minuend="fuselage_reinforcement",
                          # subtrahend="electronics_cutout"
                          ))
    electronics_access_node.append(reinforcement_node)
    # "reinforcement1" - "electronics_cutout" -> "reinforcement2"

    holes_in_engine_mount = ConstructionStepNode(
        Cut2ShapesCreator("engine_mount",
                          minuend="engine_mount"))
    reinforcement_node.append(holes_in_engine_mount)

    internal_structure_node = ConstructionStepNode(
        Intersect2ShapesCreator("internal_structure",
                                shape_a="engine_cape.loft",
                                # shape_b="reinforcement2"
                                ))
    reinforcement_node.append(internal_structure_node)
    # "engine_cape.loft" / "reinforcement2" -> "internal_structure"

    offset_fuselage_node = ConstructionStepNode(
        SimpleOffsetShapeCreator("offset_fuselage",
                                 shape="engine_cape.loft",
                                 offset=0.0008))
    internal_structure_node.append(offset_fuselage_node)
    # "engine_cape.loft" -> "offset_fuselage"

    reinforced_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("reinforced_fuselage",
                          # minuend="offset_fuselage",
                          subtrahend="internal_structure"))
    offset_fuselage_node.append(reinforced_fuselage_node)
    # "offset_fuselage" - "internal_structure" -> "reinforced_fuselage",

    load_create_fullwing_from_json = JSONStepNode(json_file_path="../components/constructions/full_wing.json",
                                                  cpacs_configuration=ccpacs_configuration)
    reinforced_fuselage_node.append(load_create_fullwing_from_json)
    # -> "wings"

    cut_wing_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_wo_wings",
                          minuend="reinforced_fuselage",
                          # subtrahend="wings"
                          ))
    load_create_fullwing_from_json.append(cut_wing_from_fuselage_node)
    # "reinforced_fuselage" - "wings" -> "fuselage_wo_wings"

    cut_elevator_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_wo_elevator",
                          # minuend="fuselage_wo_wings",
                          subtrahend="elevator"))
    cut_wing_from_fuselage_node.append(cut_elevator_from_fuselage_node)
    # "fuselage_wo_wings" - "elevator" -> "fuselage_wo_elevator"

    wing_attachment_bolt_node = ConstructionStepNode(
        WingAttachmentBoltHolesShapeCreator("attachment_bolts",
                                            fuselage_index=1,
                                            right_main_wing_index=1))
    cut_elevator_from_fuselage_node.append(wing_attachment_bolt_node)
    # -> "attachment_bolts"

    cut_bolts_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="fuselage_wo_elevator",
                          # subtrahend="attachment_bolts"
                          ))
    wing_attachment_bolt_node.append(cut_bolts_from_fuselage_node)
    # "fuselage_wo_elevator" - "attachment_bolts" -> "final_fuselage"

    stamp_shape_import = ConstructionStepNode(
        IgesImportCreator("servo_stamp",
                          iges_file="../components/servos/unknown/servo_stamp.iges",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=.0,
                          rot_y=90.0,
                          rot_z=-90.0 + 3.4,
                          scale=0.001))
    cut_bolts_from_fuselage_node.append(stamp_shape_import)
    # -> "servo_stamp"

    cut_servo_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          # subtrahend="servo_stamp"
                          ))
    stamp_shape_import.append(cut_servo_from_fuselage_node)
    # "final_fuselage" - "servo_stamp" -> "final_fuselage"

    fuse_servo_with_final_fuselage_node = ConstructionStepNode(
        Fuse2ShapesCreator("final_fuselage",
                           shape_a="final_fuselage",
                           # shape_b="servo_stamp"
                           ))
    stamp_shape_import.append(fuse_servo_with_final_fuselage_node)
    # "final_fuselage" + "servo_stamp" -> "final_fuselage"

    stamp_fill_shape_import = ConstructionStepNode(
        IgesImportCreator("servo_stamp_fill",
                          iges_file="../components/servos/unknown/servo_stamp_fill.iges",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=.0,
                          rot_y=90.0,
                          rot_z=-90.0 + 3.4,
                          scale=0.001))
    fuse_servo_with_final_fuselage_node.append(stamp_fill_shape_import)
    # -> "servo_stamp"

    cut_servo_fill_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          # subtrahend="servo_stamp_fill"
                          ))
    stamp_fill_shape_import.append(cut_servo_fill_from_fuselage_node)
    # "final_fuselage" - "servo_stamp" -> "final_fuselage"

    shape_slicer_node = ConstructionStepNode(
        SliceShapesCreator("fuselage_slicer", number_of_parts=5))
    cut_servo_fill_from_fuselage_node.append(shape_slicer_node)
    # "final_fuselage" -> "fuselage_slicer[0] .. [4]"

    shape_stl_export_node = ConstructionStepNode(
        ExportToStlCreator("stl_exporter",
                           additional_shapes_to_export=["engine_mount",
                                                        "engine_cape.cape",
                                                        "elevators[0]",
                                                        "elevators[1]",
                                                        "rudder"]))
    shape_slicer_node.append(shape_stl_export_node)
    # "fuselage_slicer[0] .. [4]", "engine_mount", "engine_cape.cape",
    # "elevators[0]", "elevators[1]", "rudder_with_slot" -> *

    shape_iges_export_node = ConstructionStepNode(
        ExportToIgesCreator("aircombat",
                            file_path="../exports",
                            shapes_to_export=[#"engine_mount",
                                              "brushless",
                                              "engine_cape.cape",
                                              "elevator",
                                              "final_fuselage",
                                              "rudder",
                                              "servo_model"
                                              ]))
    # root_node.append(shape_iges_export_node)
    # "engine_cape.cape", "elevator", "final_fuselage", "rudder_with_slot" ->

    mount_step_export_node = ConstructionStepNode(
        ExportToStepCreator(Path(CPACS_FILE_NAME).stem,
                            file_path="../exports",
                            shapes_to_export=["engine_mount",
                                              "brushless",
                                              "engine_cape.cape",
                                              "elevator",
                                              "final_fuselage",
                                              "rudder",
                                              "servo_model"]))
    root_node.append(mount_step_export_node)
    # "engine_mount", "engine_cape.cape", "elevator", "final_fuselage", "rudder_with_slot" ->

    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             cpacs_configuration=ccpacs_configuration)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))
    try:
        # build on basis of deserialized json
        structure = myMap.create_shape()
        from pprint import pprint

        pprint(structure)
    except Exception as err:
        logging.fatal(f"{err.with_traceback()}")

    shapeDisplay.start()

    pass
