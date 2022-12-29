import logging
import sys
from pathlib import Path

import tigl3.geometry as tgl_geom
from OCC.Core.TopoDS import TopoDS_Shape, TopoDS_Compound, TopoDS_CompSolid
from tigl3.configuration import CCPACSConfiguration, CCPACSEnginePositions, CCPACSEnginePosition

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.ConstructionStepNode import ConstructionStepNode, JSONStepNode, ConstructionRootNode
from Airplane.Fuselage.EngineMountFactory import EngineMountFactory
from Airplane.aircraft_topology.EngineInformation import EngineInformation
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
        if self.offset > 0:
            ConstructionStepsViewer.instance().display_offset(result, result, shape, severity=logging.INFO, msg=msg)
        else:
            ConstructionStepsViewer.instance().display_offset(result, shape, result, severity=logging.INFO, msg=msg)

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
        export_shapes(list(all_shapes.values()), path, deflection=0.000001)

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
        logging.info(f"exporting step model '{', '.join(all_shapes.keys())}' --> '{self.file_path}'")

        from OCC.Core.STEPControl import STEPControl_AsIs

        for name, shape in all_shapes.items():
            step_writer = self._generateStepWriter()
            t_shape = ScaleRotateTranslateCreator.transform_by(shape=shape, scale=1000.0)
            step_writer.Transfer(t_shape.shape(), STEPControl_AsIs)
            step_path = os.path.join(self.file_path, f"{self.identifier}_{name}.stp")
            step_writer.Write(step_path)

        step_writer = self._generateStepWriter()
        for name, shape in all_shapes.items():
            t_shape = ScaleRotateTranslateCreator.transform_by(shape=shape, scale=1000.0)
            import OCC.Core.IFSelect as IFSelect
            if step_writer.Transfer(t_shape.shape(), STEPControl_AsIs) != IFSelect.IFSelect_RetDone:
                logging.fatal(f"error while exporting '{name}'")
                raise RuntimeError(f"error while exporting '{name}'")

        step_path = os.path.join(self.file_path, f"{self.identifier}.stp")
        logging.debug(f"writing model to '{step_path}'")
        step_writer.Write(step_path)

        return all_shapes

    def _generateStepWriter(self):
        # ===============
        from OCC.Core.STEPControl import STEPControl_Controller, STEPControl_Writer
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
        Interface_Static_SetIVal("write.step.assembly", 0)
        Interface_Static_SetCVal("write.step.unit", "M")
        Interface_Static_SetIVal("write.precision.mode", 0)
        return step_writer


class ExportToStlCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str,
                 mode: str = "binary",  # "binary" od "ascii"
                 linear_deflection: float = 0.0000001,
                 additional_shapes_to_export: list[str] = None):
        self.identifier: str = creator_id
        self.mode = mode
        self.linear_deflection = linear_deflection
        self.additional_shapes_to_export: list[str] = additional_shapes_to_export \
            if additional_shapes_to_export is not None else [None]

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        all_shapes = AbstractShapeCreator.check_if_shapes_are_available(self.additional_shapes_to_export, **kwargs)
        logging.info(f"converting shapes '{', '.join(all_shapes.keys())}' to .STL")

        import stl_exporter.Exporter as Exporter
        stl_exporter = Exporter.Exporter()
        stl_exporter.write_stls_from_list(all_shapes.values(), mode=self.mode, linear_deflection=self.linear_deflection)
        return all_shapes


# === END basic import export operations ===


class EngineMountShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, mount_plate_thickness: float, engine_screw_hole_circle: float,
                 engine_mount_box_length: float, engine_screw_din_diameter: float, engine_screw_length: float,
                 engine_index: int, engine_total_cover_length: float = None, engine_down_thrust_deg: float = None,
                 engine_side_thrust_deg: float = None, cpacs_configuration: CCPACSConfiguration = None):
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
        self.mount_plate_thickness = mount_plate_thickness
        self._cpacs_configuration = cpacs_configuration
        self._engine_information = None

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(f" creating mount for engine '{self.engine_index}' --> '{self.identifier}'")

        self._engine_information = EngineInformation(self.engine_index, self._cpacs_configuration) \
            if self._engine_information is None else self._engine_information
        self.engine_down_thrust_deg = self._engine_information.down_thrust \
            if self.engine_down_thrust_deg is None else self.engine_down_thrust_deg
        self.engine_side_thrust_deg = self._engine_information.side_thrust \
            if self.engine_side_thrust_deg is None else self.engine_side_thrust_deg
        self.engine_total_cover_length = self._engine_information.length if self.engine_total_cover_length is None \
            else self.engine_total_cover_length

        mount = EngineMountFactory.create_engine_mount(engine_total_cover_length=self.engine_total_cover_length,
                                                       engine_mount_box_length=self.engine_mount_box_length,
                                                       engine_down_thrust_deg=self.engine_down_thrust_deg,
                                                       engine_side_thrust_deg=self.engine_side_thrust_deg,
                                                       engine_screw_hole_circle=self.engine_screw_hole_circle,
                                                       engine_screw_din_diameter=self.engine_screw_din_diameter,
                                                       engine_screw_length=self.engine_screw_length,
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


class EngineMountPanelShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, mount_plate_thickness: float, engine_screw_hole_circle: float,
                 engine_mount_box_length: float, fuselage_index: int, engine_index: int,
                 engine_total_cover_length: float = None, engine_side_thrust_deg: float = None,
                 engine_down_thrust_deg: float = None, cpacs_configuration: CCPACSConfiguration = None):
        """

        :param engine_index:
        :param creator_id:
        :param mount_plate_thickness: thickness of the mount backplate
        :param engine_screw_hole_circle: the diameter of the screw circle of the engine mount
        :param engine_total_cover_length: the length of the engine from where it touches the mount to the point which should be outside the cape
        :param engine_mount_box_length: length of the box, the engine is screwd onto. (can be used to give place for a shaft)
        :param engine_down_thrust_deg: down thrust in degree
        :param engine_side_thrust_deg: side thrust in degree
        :param fuselage_index:
        :param cpacs_configuration:
        """
        self.engine_index = engine_index
        self.identifier = creator_id
        self.engine_screw_hole_circle = engine_screw_hole_circle
        self.engine_total_cover_length = engine_total_cover_length
        self.engine_mount_box_length = engine_mount_box_length
        self.engine_down_thrust_deg = engine_down_thrust_deg
        self.engine_side_thrust_deg = engine_side_thrust_deg
        self.fuselage_index = fuselage_index
        self.mount_plate_thickness = mount_plate_thickness
        self._cpacs_configuration = cpacs_configuration
        self._engine_information = None

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(f" creating mount panel for engine '{self.engine_index}' --> '{self.identifier}'")

        self._engine_information = EngineInformation(self.engine_index, self._cpacs_configuration) \
            if self._engine_information is None else self._engine_information

        self.engine_down_thrust_deg = self._engine_information.down_thrust \
            if self.engine_down_thrust_deg is None else self.engine_down_thrust_deg

        self.engine_side_thrust_deg = self._engine_information.side_thrust \
            if self.engine_side_thrust_deg is None else self.engine_side_thrust_deg

        self.engine_total_cover_length = self._engine_information.length if self.engine_total_cover_length is None \
            else self.engine_total_cover_length

        mount_plate = EngineMountFactory.create_back_plate(mount_plate_thickness=self.mount_plate_thickness,
                                                           engine_mount_box_length=self.engine_mount_box_length,
                                                           engine_total_cover_length=self.engine_total_cover_length,
                                                           engine_screw_hole_circle=self.engine_screw_hole_circle,
                                                           engine_position=self._engine_information.position,
                                                           fuselage_index=self.fuselage_index,
                                                           cpacs_configuration=self._cpacs_configuration)

        ConstructionStepsViewer.instance().display_this_shape(mount_plate, logging.INFO, msg=f"{self.identifier}")
        return {str(self.identifier): mount_plate}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class SliceShapesCreator(AbstractShapeCreator):
    """
    Slices the given shape in <number_of_parts> parts along the x-axis. And returns a dictionary with the parts.
    The naming convention for a key is <shape_identifier>[<part_number>], e.g. {"fuselage[0]": <CNamedShape>, "fuselage[1]": <CNamedShape>}
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, number_of_parts: int, shapes_to_slice: list[str] = None):
        self.shapes_to_slice = shapes_to_slice if shapes_to_slice is not None else [None]
        self.identifier = creator_id
        self.number_of_parts = number_of_parts

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.return_needed_shapes(self.shapes_to_slice, input_shapes, **kwargs)
        logging.info(f"slicing shapes '{shapes.keys()}' in {self.number_of_parts} parts")

        from Extra.ShapeSlicer import ShapeSlicer
        parts: dict[str, tgl_geom.CNamedShape] = {}
        for key, shape in shapes.items():
            my_slicer = ShapeSlicer(shape, self.number_of_parts)
            my_slicer.slice_by_cut()
            for i, s in enumerate(my_slicer.parts_list):
                parts[f"{key}[{i}]"] = s
                ConstructionStepsViewer.instance().display_this_shape(s, logging.INFO, msg=f"{key}[{i}]")
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
        logging.info(f"creating engine cape and loft --> '{self.identifier}.cape, {self.identifier}.loft'")

        _engine_information = EngineInformation(self.engine_index, self._cpacs_configuration)

        self.engine_total_cover_length = _engine_information.length \
            if self.engine_total_cover_length is None \
            else self.engine_total_cover_length

        engine_x_offset = _engine_information.position.get_x()

        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        shapes = FuselageFactory.create_engine_cape(cpacs_configuration=self._cpacs_configuration,
                                                    fuselage_index=self.fuselage_index,
                                                    mount_plate_thickness=self.mount_plate_thickness,
                                                    motor_cutout_length=self.engine_total_cover_length + self.engine_mount_box_length + engine_x_offset)
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
        logging.info(f"creating fuselage reinforcement with index {self.fuselage_index}--> '{self.identifier}'")
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
        logging.info(f"creating wing support reinforcement with index {self.fuselage_index} --> '{self.identifier}'")

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
        logging.info(f"creating fuselage electronics cutout with index {self.fuselage_index} --> '{self.identifier}'")

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
        logging.info(f"creating wing attachment bolts --> '{self.identifier}'")

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
        logging.info(f"creating wing loft/hull with index {self.right_main_wing_index} --> '{self.identifier}'")

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


class FullWingShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 right_main_wing_index: int,
                 fuselage_index: int,
                 cpacs_configuration: CCPACSConfiguration = None,
                 ):
        self.fuselage_index = fuselage_index
        self.identifier: str = creator_id
        self.right_main_wing_index = right_main_wing_index
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        logging.info(f"creating wing with index {self.right_main_wing_index} --> '{self.identifier}'")
        right_wing, left_wing, right_aileron, left_aileron = self._create_right_main_wing()

        ConstructionStepsViewer.instance().display_this_shape(
            right_wing, logging.INFO, msg=f"{self.identifier}")
        ConstructionStepsViewer.instance().display_this_shape(
            left_wing, logging.INFO, msg=f"{self.identifier}")
        return {f"{str(self.identifier)}.right": right_wing, f"{str(self.identifier)}.left": left_wing,
                f"{str(self.identifier)}.right_ail": right_aileron, f"{str(self.identifier)}.left_ail": left_aileron}

    def _create_right_main_wing(self):
        """
        Creates the .stl files of the wing describes in the CPACSConfiguration
        :return:
        """
        logging.info("Creating right main wing")
        right_main_wing = self._cpacs_configuration.get_wing(self.right_main_wing_index)
        fuselage = self._cpacs_configuration.get_fuselage(self.fuselage_index)

        from Airplane.Wing.WingFactory import WingFactory
        wing_factory = WingFactory(self._cpacs_configuration, self.right_main_wing_index)
        right_wing, right_aileron = wing_factory.create_wing_with_inbuilt_servo()
        # right_wing = wing_factory.get_shape()

        left_wing = wing_factory.create_mirrored_wing(right_wing)
        left_aileron = wing_factory.create_mirrored_wing(right_aileron)

        return right_wing, left_wing, right_aileron, left_aileron

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value
