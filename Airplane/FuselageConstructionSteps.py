import tigl3.geometry as tgl_geom
from tigl3.configuration import CCPACSConfiguration, CCPACSEnginePositions, CCPACSEnginePosition

from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.Fuselage.EngineMountFactory import EngineMountFactory
from Extra.BooleanOperationsForLists import BooleanCADOperation

from Extra.ConstructionStepsViewer import *


class LoadJsonCreator(AbstractShapeCreator):
    """
    Loading a construction workflow from json, and returns all created shapes.
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str,
                 json_file_path: str = None,
                 shapes_needed: list[str] = None,
                 enable_display: bool = True,
                 **kwargs):
        self.identifier = creator_id
        self.json_file_path = json_file_path
        self.shapes_needed = shapes_needed
        self.enable_display = enable_display
        self._to_be_injected = kwargs

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.check_if_shapes_are_available(self.shapes_needed, **kwargs)

        import json
        from Airplane.GeneralJSONEncoderDecoder import GeneralJSONDecoder
        _json_file = open(self.json_file_path)
        constructor = json.load(_json_file,
                                cls=GeneralJSONDecoder,
                                **self._to_be_injected)
        _json_file.close()

        # if self.enable_display:
        #     ConstructionStepsViewer.instance().display_fuse(fused_shape,
        #                                                     shapes[self.shape_a],
        #                                                     shapes[self.shape_b])

        # build on basis of deserialized json
        return constructor.construct()


# === BEGIN: Basic shape operations ===
class Fuse2ShapesCreator(AbstractShapeCreator):
    """
    Fusing two shapes into one.
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None,
                 enable_display: bool = True):
        self.identifier = creator_id
        self.shape_a = shape_a
        self.shape_b = shape_b
        self.enable_display = enable_display

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.check_if_shapes_are_available([self.shape_a, self.shape_b], **kwargs)

        fused_shape = BooleanCADOperation.fuse_shapes(
            shapes[self.shape_a], shapes[self.shape_b], self.identifier)

        if self.enable_display:
            ConstructionStepsViewer.instance().display_fuse(fused_shape,
                                                            shapes[self.shape_a],
                                                            shapes[self.shape_b])

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
                 subtrahend: str = None,
                 enable_display: bool = True):
        self.identifier = creator_id
        self.minuend = minuend
        self.subtrahend = subtrahend
        self.enable_display = enable_display

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.check_if_shapes_are_available([self.minuend, self.subtrahend], **kwargs)

        from Extra.BooleanOperationsForLists import BooleanCADOperation

        shape__minuend = shapes.get(self.minuend)
        shape__subtrahend = shapes.get(self.subtrahend)
        cut_shape = BooleanCADOperation.cut_shape_from_shape(shape__minuend,
                                                             shape__subtrahend,
                                                             self.identifier)
        if self.enable_display:
            ConstructionStepsViewer.instance().display_cut(cut_shape,
                                                           shape__minuend,
                                                           shape__subtrahend)

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
                 enable_display: bool = True):
        self.identifier = creator_id
        self.offset = offset
        self.shape = shape
        self.enable_display = enable_display

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        if self.shape is None:
            shape = list(input_shapes.values())[0]
        else:
            shapes = AbstractShapeCreator.check_if_shapes_are_available([self.shape], **kwargs)
            shape = shapes[self.shape]

        from OCC.Core.BRepOffsetAPI import BRepOffsetAPI_MakeOffsetShape
        offset_maker: BRepOffsetAPI_MakeOffsetShape = BRepOffsetAPI_MakeOffsetShape()
        offset_maker.PerformBySimple(shape.shape(), self.offset)
        result = TGeo.CNamedShape(offset_maker.Shape(), f"{shape.name()}_offset")

        if self.enable_display:
            msg = f"Fuselage with {str(self.offset)=} meters"
            ConstructionStepsViewer.instance().display_this_shape(result, msg)

        return {self.identifier: shape}


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

    def __init__(self, creator_id: str, shape_a: str = None, shape_b: str = None,
                 enable_display: bool = True):
        self.identifier = creator_id
        self.shape_a = shape_a
        self.shape_b = shape_b
        self.enable_display = enable_display

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        shapes = AbstractShapeCreator.check_if_shapes_are_available([self.shape_a, self.shape_b], **kwargs)

        from Extra.BooleanOperationsForLists import BooleanCADOperation

        shape__a = shapes.get(self.shape_a)
        shape__b = shapes.get(self.shape_b)
        cut_shape = BooleanCADOperation.intersect_shape_with_shape(shape__a,
                                                                   shape__b,
                                                                   self.identifier)
        if self.enable_display:
            ConstructionStepsViewer.instance().display_common(cut_shape,
                                                              shape__a,
                                                              shape__b)

        return {self.identifier: cut_shape}

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
        print('--> '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()]), "==>", self.identifier)
        _engine_mount_factory = EngineMountFactory(cpacs_configuration=self._cpacs_configuration,
                                                   fuselage_index=self.fuselage_index)
        return {str(self.identifier): _engine_mount_factory.create_engine_mount(
            plate_thickness=self.mount_plate_thickness)}

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
                parts["{}[{}]".format(self.identifier, i)] = s
        return parts


class ExportToStlCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, additional_shapes_to_export: list[str]=None):
        self.identifier: str = creator_id
        self.additional_shapes_to_export: list[str] = additional_shapes_to_export

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        all_shapes = AbstractShapeCreator.check_if_shapes_are_available(self.additional_shapes_to_export, **kwargs)
        all_shapes.update(input_shapes)

        import stl_exporter.Exporter as Exporter
        stl_exporter = Exporter.Exporter()
        stl_exporter.write_stls_from_list(all_shapes.values())
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
        shape = FuselageFactory.create_engine_cape(cpacs_configuration=self._cpacs_configuration,
                                                   fuselage_index=self.fuselage_index,
                                                   motor_cutout_length=2*engine_length+ self.mount_plate_thickness)
        return {"{}.cape".format(self.identifier): shape[0], "{}.loft".format(self.identifier): shape[1]}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class FuselageReinforcementShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 right_main_wing_index: int,
                 rib_width: float,
                 ribcage_factor: float,
                 reinforcement_pipes_radius: float,
                 cpacs_configuration: CCPACSConfiguration = None
                 ):
        self.identifier: str = creator_id
        self.fuselage_index = fuselage_index
        self.right_main_wing_index = right_main_wing_index
        self.rib_width = rib_width
        self.ribcage_factor = ribcage_factor
        self.reinforcement_pipes_radius = reinforcement_pipes_radius
        self._cpacs_configuration = cpacs_configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        from Airplane.Fuselage.FuselageRibFactory import FuselageRibFactory
        from Airplane.ReinforcementPipeFactory import ReinforcementePipeFactory

        rib_factory = FuselageRibFactory(self._cpacs_configuration.get_wing(self.right_main_wing_index),
                                         self._cpacs_configuration.get_fuselage(self.fuselage_index))
        reinforcement_pipe_factory = ReinforcementePipeFactory(
            self._cpacs_configuration.get_wing(self.right_main_wing_index),
            self._cpacs_configuration.get_fuselage(self.fuselage_index))

        shape__fuselage_reinforcement = FuselageFactory.create_fuselage_reinforcement(
            cpacs_configuration=self._cpacs_configuration,
            fuselage_index=self.fuselage_index,
            reinforcement_pipe_factory=reinforcement_pipe_factory,
            reinforcement_pipes_radius=self.reinforcement_pipes_radius,
            rib_factory=rib_factory,
            rib_width=self.rib_width,
            ribcage_factor=self.ribcage_factor,
            right_main_wing_index=self.right_main_wing_index)

        return {str(self.identifier): shape__fuselage_reinforcement}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class FuselageWingSupportShapeCreator(AbstractShapeCreator):
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
        from Airplane.Fuselage.FuselageRibFactory import FuselageRibFactory

        rib_factory = FuselageRibFactory(self._cpacs_configuration.get_wing(self.right_main_wing_index),
                                         self._cpacs_configuration.get_fuselage(self.fuselage_index))

        shape__wing_support = FuselageFactory.create_wing_support_shape(self._cpacs_configuration,
                                                                        rib_factory,
                                                                        self.fuselage_index,
                                                                        self.right_main_wing_index)

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
                 enable_display: bool = True):
        self.identifier: str = creator_id
        self.right_main_wing_index = right_main_wing_index
        self._cpacs_configuration = cpacs_configuration
        self.enable_display = enable_display

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        complete_wing = BooleanCADOperation.fuse_shapes(
            self._cpacs_configuration.get_wing(self.right_main_wing_index).get_loft(),
            self._cpacs_configuration.get_wing(self.right_main_wing_index).get_mirrored_loft(),
            self.identifier)

        if self.enable_display:
            ConstructionStepsViewer.instance().display_fuse(
                complete_wing,
                self._cpacs_configuration.get_wing(self.right_main_wing_index).get_loft(),
                self._cpacs_configuration.get_wing(self.right_main_wing_index).get_mirrored_loft())

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

    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.ConstructionStepsViewer import ConstructionStepsViewer
    from tigl3.configuration import CCPACSConfiguration, CCPACSConfigurationManager_get_instance
    shapeDisplay = ConstructionStepsViewer.instance(True, 1)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance()\
        .get_configuration(tigl_h._handle.value)

    # defining the shape creators
    shape_slicer_node = ConstructionStepNode(
        SliceShapesCreator("fuselage_slicer", number_of_parts=5))
    engine_mount_node = ConstructionStepNode(
        EngineMountShapeCreator("engine_mount",
                                fuselage_index=1,
                                mount_plate_thickness=0.005))
    shape_stl_export_node = ConstructionStepNode(
        ExportToStlCreator("stl_exporter",
                           additional_shapes_to_export=["engine_mount", "engine_cape.cape"]))
    engine_cape_node = ConstructionStepNode(
        EngineCapeShapeCreator("engine_cape",
                               engine_index=1,
                               fuselage_index=1,
                               mount_plate_thickness=0.005))
    fuselage_reinforcement_node = ConstructionStepNode(
        FuselageReinforcementShapeCreator("fuselage_reinforcement",
                                          fuselage_index=1,
                                          right_main_wing_index=1,
                                          ribcage_factor=0.5,
                                          rib_width=0.002,
                                          reinforcement_pipes_radius=0.003))
    wing_support_node = ConstructionStepNode(
        FuselageWingSupportShapeCreator("wing_support",
                                        fuselage_index=1,
                                        right_main_wing_index=1))
    fuse_reinforcement_wing_sup_node = ConstructionStepNode(
        Fuse2ShapesCreator("reinforcement",
                           shape_a="fuselage_reinforcement",
                           shape_b="wing_support"))
    electronics_access_node = ConstructionStepNode(
        FuselageElectronicsAccessCutOutShapeCreator("electronics_cutout",
                                                    fuselage_index=1,
                                                    ribcage_factor=0.5,
                                                    right_main_wing_index=1,
                                                    wing_position=None))
    reinforcement_node = ConstructionStepNode(
        Cut2ShapesCreator("reinforcement",
                          minuend="reinforcement",
                          subtrahend="electronics_cutout"))
    internal_structure_node = ConstructionStepNode(
        Intersect2ShapesCreator("internal_structure",
                                shape_a="engine_cape.loft",
                                shape_b="reinforcement"))
    offset_fuselage_node = ConstructionStepNode(
        SimpleOffsetShapeCreator("offset_fuselage",
                                 shape="engine_cape.loft",
                                 offset=0.004))
    reinforced_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("reinforced_fuselage",
                          minuend="offset_fuselage",
                          subtrahend="internal_structure"))
    full_wing_loft_node = ConstructionStepNode(
        FullWingLoftShapeCreator("wings",
                                 right_main_wing_index=1))
    cut_wing_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("fuselage_wo_wings",
                          minuend="reinforced_fuselage",
                          subtrahend="wings"))
    wing_attachment_bolt_node = ConstructionStepNode(
        WingAttachmentBoltHolesShapeCreator("attachment_bolts",
                                            fuselage_index=1,
                                            right_main_wing_index=1))
    cut_bolts_from_fuselage_node = ConstructionStepNode(
        Cut2ShapesCreator("final_fuselage",
                          minuend="fuselage_wo_wings",
                          subtrahend="attachment_bolts"))

    # ============
    full_wing_file_path = "full_wing.json"
    full_wing_file = open(full_wing_file_path, "w")
    json.dump(fp=full_wing_file, obj=full_wing_loft_node, indent=4, cls=GeneralJSONEncoder)
    full_wing_file.close()

    json_load_node = ConstructionStepNode(
        LoadJsonCreator("load_json",
                        json_file_path=full_wing_file_path,
                        cpacs_configuration=ccpacs_configuration))

    json_load_node.construct()
    #shapeDisplay.start()
    # =============

    # linking the map
    engine_cape_node.append(engine_mount_node)
    engine_mount_node.append(fuselage_reinforcement_node)
    fuselage_reinforcement_node.append(wing_support_node)
    wing_support_node.append(fuse_reinforcement_wing_sup_node)
    fuse_reinforcement_wing_sup_node.append(electronics_access_node)
    electronics_access_node.append(reinforcement_node)
    reinforcement_node.append(internal_structure_node)
    internal_structure_node.append(offset_fuselage_node)
    offset_fuselage_node.append(reinforced_fuselage_node)
    reinforced_fuselage_node.append(json_load_node)
    json_load_node.append(cut_wing_from_fuselage_node)
    cut_wing_from_fuselage_node.append(wing_attachment_bolt_node)
    wing_attachment_bolt_node.append(cut_bolts_from_fuselage_node)
    cut_bolts_from_fuselage_node.append(shape_slicer_node)
    shape_slicer_node.append(shape_stl_export_node)

    # dump to a json string
    json_data: str = json.dumps(engine_cape_node, indent=4, cls=GeneralJSONEncoder)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap = json.loads(json_data, cls=GeneralJSONDecoder,
                       cpacs_configuration=ccpacs_configuration)

    # dump again to check
    print(json.dumps(myMap, indent=4, cls=GeneralJSONEncoder))

    # build on basis of deserialized json
    structure = myMap.construct()

    from pprint import pprint
    pprint(structure)

    shapeDisplay.start()

    pass
