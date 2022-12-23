import logging
import sys

import tigl3.geometry as tgl_geom
from tigl3.configuration import CCPACSConfiguration, CCPACSEnginePositions, CCPACSEnginePosition

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.ConstructionStepNode import ConstructionStepNode, JSONStepNode, ConstructionRootNode
from Airplane.Fuselage.EngineMountFactory import EngineMountFactory
from Extra.BooleanOperationsForLists import BooleanCADOperation

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
    Cut the subtrahend from the minuend (minuend - subtrahend = new_shape).
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
        logging.info(f"intersecting shapes '{list(shapes.keys())[0]}' / '{list(shapes.keys())[1]}' --> '{self.identifier}'")

        from Extra.BooleanOperationsForLists import BooleanCADOperation

        shape__a = shape_list[0]
        shape__b = shape_list[1]
        cut_shape = BooleanCADOperation.intersect_shape_with_shape(shape__a,
                                                                   shape__b,
                                                                   self.identifier)
        ConstructionStepsViewer.instance().display_common(cut_shape, shape__a, shape__b, logging.INFO)

        return {self.identifier: cut_shape}


class IgesImportCreator(AbstractShapeCreator):
    """
    Cut the subtrahend from the minuend (minuend - subtrahend = new_shape).
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

        topods = self._iges_importer(self.iges_file)
        shape = tgl_geom.CNamedShape(topods, f"{self.identifier}")

        trafo = tgl_geom.CTiglTransformation()
        trafo.add_scaling(self.scale, self.scale, self.scale)
        trafo.add_rotation_x(self.rot_x)
        trafo.add_rotation_y(self.rot_y)
        trafo.add_rotation_z(self.rot_z)
        trafo.add_translation(self.trans_x, self.trans_y, self.trans_z)


        trans_shape = trafo.transform(shape)

        ConstructionStepsViewer.instance().display_this_shape(trans_shape, severity=logging.INFO)

        return {self.identifier: trans_shape}

    def _iges_importer(self, path_):
        from OCC.Extend.DataExchange import read_iges_file
        # return read_iges_file(filename=self.iges_file, return_as_shapes=True)
        from OCC.Core.IFSelect import IFSelect_RetDone, IFSelect_ItemsByEntity
        from OCC.Core.IGESControl import IGESControl_Reader
        iges_reader = IGESControl_Reader()
        status = iges_reader.ReadFile(path_)

        if status == IFSelect_RetDone:  # check status
            failsonly = False
            iges_reader.PrintCheckLoad(failsonly, IFSelect_ItemsByEntity)
            iges_reader.PrintCheckTransfer(failsonly, IFSelect_ItemsByEntity)
            ok = iges_reader.TransferRoots()
            aResShape = iges_reader.Shape(1)
            return aResShape
        else:
            raise AssertionError("could not import IGES file: {0}".format(path_))
# === END basic shape operations ===


class EngineMountShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 mount_plate_thickness: float,
                 fuselage_index: int,
                 cpacs_configuration: CCPACSConfiguration = None):
        self.identifier = creator_id
        self.fuselage_index = fuselage_index
        self.mount_plate_thickness = mount_plate_thickness
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        _engine_mount_factory = EngineMountFactory(cpacs_configuration=self._cpacs_configuration,
                                                   fuselage_index=self.fuselage_index)
        mount = _engine_mount_factory.create_engine_mount(plate_thickness=self.mount_plate_thickness)
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


class ExportToIgesCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, shapes_to_export: list[str] = None):
        self.identifier: str = creator_id
        self.shapes_to_export: list[str] = shapes_to_export

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        all_shapes = AbstractShapeCreator.check_if_shapes_are_available(self.shapes_to_export, **kwargs)

        import stl_exporter.Exporter as Exporter
        from tigl3.import_export_helper import export_shapes
        export_shapes(list(all_shapes.values()), f"{self.identifier}.igs", deflection=0.0001)
        return all_shapes


class EngineCapeShapeCreator(AbstractShapeCreator):
    """
    Creates an engine cape <identifier>.cape and fuselage loft without the cape <identifier>.loft, by cutting the cape
    of the full fuselage loft.
    """
    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 engine_index: int,
                 mount_plate_thickness: float,
                 cpacs_configuration: CCPACSConfiguration = None):
        self.identifier = creator_id
        self.fuselage_index = fuselage_index
        self.mount_plate_thickness = mount_plate_thickness
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
                                                    motor_cutout_length=2*engine_length+ self.mount_plate_thickness)
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
    def __init__(self, creator_id: str, fuselage_index: int, right_main_wing_index: int, rib_quantity: int,
                 rib_width: float, rib_height_factor: float, cpacs_configuration: CCPACSConfiguration = None):
        self.identifier: str = creator_id
        self.fuselage_index = fuselage_index
        self.right_main_wing_index = right_main_wing_index
        self.rib_quantity = rib_quantity
        self.rib_width = rib_width
        self.rib_height_factor = rib_height_factor
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
                        level=logging.INFO, stream=sys.stdout)
    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance
    shapeDisplay = ConstructionStepsViewer.instance(dev=True, distance=1, log=False)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance()\
        .get_configuration(tigl_h._handle.value)

    # ============
    full_wing_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("wings",
                                 right_main_wing_index=1))

    full_wing_file_path = "full_wing.json"
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
        Cut2ShapesCreator("rudder_with_slot",
                          #minuend="rudder",
                          subtrahend="elevator"))
    full_rudder_loft_node.append(cut_rudder_from_elevator_node)
    # "rudder" - "elevator" -> "rudder_with_slot"

    elevator_slicer_node = ConstructionStepNode(
        SliceShapesCreator("elevators", number_of_parts=2))
    full_elevator_loft_node.append(elevator_slicer_node)
    # "elevator" -> "elevators[0]", "elevators[1]"

    engine_mount_node = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount",
                                fuselage_index=1,
                                mount_plate_thickness=0.005))
    root_node.append(engine_mount_node)
    # -> "engine_mount"

    engine_cape_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape",
                               engine_index=1,
                               fuselage_index=1,
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
                          iges_file="servo.iges",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=.0,
                          rot_y=90.0,
                          rot_z=-90.0+3.4,
                          scale=0.001))
    fuselage_reinforcement_node.append(servo_shape_import)
    # -> "servo"

    fuse_servo_with_fuselage = ConstructionStepNode(
        Fuse2ShapesCreator("reinforcement3",
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
        Fuse2ShapesCreator("reinforcement0",
                           shape_a="reinforcement3",
                           #shape_b="wing_support"
                           ))
    wing_support_node.append(fuse_reinforcement_wing_sup_node)
    # "reinforcement3" + "wing_support" -> "reinforcement0"

    full_elevator_support_loft_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("elevator_support",
                                        fuselage_index=1,
                                        right_main_wing_index=2,
                                        rib_quantity=12,
                                        rib_width=0.0004,
                                        rib_height_factor=20))
    fuse_reinforcement_wing_sup_node.append(full_elevator_support_loft_node)
    # -> "elevator_support"

    fuse_reinforcement_elevator_sup_node = ConstructionStepNode(
        Fuse2ShapesCreator("reinforcement1",
                           shape_a="reinforcement0",
                           #shape_b="elevator_support"
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
        Cut2ShapesCreator("reinforcement2",
                          minuend="reinforcement1",
                          #subtrahend="electronics_cutout"
                          ))
    electronics_access_node.append(reinforcement_node)
    # "reinforcement1" - "electronics_cutout" -> "reinforcement2"

    internal_structure_node = ConstructionStepNode(
        Intersect2ShapesCreator("internal_structure",
                                shape_a="engine_cape.loft",
                                #shape_b="reinforcement2"
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
                          #minuend="offset_fuselage",
                          subtrahend="internal_structure"))
    offset_fuselage_node.append(reinforced_fuselage_node)
    # "offset_fuselage" - "internal_structure" -> "reinforced_fuselage",

    load_create_fullwing_from_json = JSONStepNode(json_file_path="full_wing.json",
                                                  cpacs_configuration=ccpacs_configuration)
    reinforced_fuselage_node.append(load_create_fullwing_from_json)
    # -> "wings"

    cut_wing_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_wo_wings",
                          minuend="reinforced_fuselage",
                          #subtrahend="wings"
                          ))
    load_create_fullwing_from_json.append(cut_wing_from_fuselage_node)
    # "reinforced_fuselage" - "wings" -> "fuselage_wo_wings"

    cut_elevator_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_wo_elevator",
                          #minuend="fuselage_wo_wings",
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
                          #subtrahend="attachment_bolts"
                          ))
    wing_attachment_bolt_node.append(cut_bolts_from_fuselage_node)
    # "fuselage_wo_elevator" - "attachment_bolts" -> "final_fuselage"

    stamp_shape_import = ConstructionStepNode(
        IgesImportCreator("servo_stamp",
                          iges_file="servo_stamp.iges",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=.0,
                          rot_y=90.0,
                          rot_z=-90.0+3.4,
                          scale=0.001))
    cut_bolts_from_fuselage_node.append(stamp_shape_import)
    # -> "servo_stamp"

    cut_servo_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          #subtrahend="servo_stamp"
                          ))
    stamp_shape_import.append(cut_servo_from_fuselage_node)
    # "final_fuselage" - "servo_stamp" -> "final_fuselage"

    fuse_servo_with_final_fuselage_node = ConstructionStepNode(
        Fuse2ShapesCreator("final_fuselage",
                           shape_a="final_fuselage",
                           #shape_b="servo_stamp"
                           ))
    stamp_shape_import.append(fuse_servo_with_final_fuselage_node)
    # "final_fuselage" + "servo_stamp" -> "final_fuselage"

    stamp_fill_shape_import = ConstructionStepNode(
        IgesImportCreator("servo_stamp_fill",
                          iges_file="servo_stamp_fill.iges",
                          trans_x=0.67,
                          trans_y=-0.02066,
                          trans_z=.0,
                          rot_x=.0,
                          rot_y=90.0,
                          rot_z=-90.0+3.4,
                          scale=0.001))
    fuse_servo_with_final_fuselage_node.append(stamp_fill_shape_import)
    # -> "servo_stamp"

    cut_servo_fill_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="final_fuselage",
                          #subtrahend="servo_stamp_fill"
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
                                                        "rudder_with_slot"]))
    shape_slicer_node.append(shape_stl_export_node)
    # "fuselage_slicer[0] .. [4]", "engine_mount", "engine_cape.cape",
    # "elevators[0]", "elevators[1]", "rudder_with_slot" -> *

    shape_iges_export_node = ConstructionStepNode(
        ExportToIgesCreator("aircombat",
                            shapes_to_export=[#"engine_mount",
                                              "engine_cape.cape",
                                              "elevator",
                                              "final_fuselage",
                                              "rudder_with_slot"]))
    root_node.append(shape_iges_export_node)
    # "engine_mount", "engine_cape.cape", "elevator", "final_fuselage", "rudder_with_slot" ->


    # dump to a json string
    json_data: str = json.dumps(root_node, indent=4, cls=GeneralJSONEncoder)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap: ConstructionStepNode = json.loads(json_data, cls=GeneralJSONDecoder,
                                             cpacs_configuration=ccpacs_configuration)

    # dump again to check
    print(json.dumps(myMap, indent=2, cls=GeneralJSONEncoder))

    # build on basis of deserialized json
    structure = myMap.create_shape()

    from pprint import pprint
    pprint(structure)

    shapeDisplay.start()

    pass
