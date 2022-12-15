import tigl3.geometry as tgl_geom
from tigl3.configuration import CCPACSConfiguration, CCPACSEnginePositions, CCPACSEnginePosition

from Airplane import Configuration
from Airplane.AbstractShapeCreator import AbstractShapeCreator
from Airplane.ConstructionStepNode import ConstructionStepNode
from Airplane.Fuselage.EngineMountFactory import EngineMountFactory
from Airplane.GeneralJSONEncoderDecoder import GeneralJSONEncoder, GeneralJSONDecoder
from Extra.BooleanOperationsForLists import BooleanCADOperation


# !!! no function yet only example
class WingServoMountCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str, width: float, height: float, length: float, tigl_handel=None, wing_stuff=None):
        """
        Example where wing_stuff is injected during the json decoding by the decoder object
        :param creator_id:
        :param width:
        :param height:
        :param length:
        :param tigl_handel:
        :param wing_stuff:
        """
        self.identifier = creator_id
        self.width = width
        self.height = height
        self.length = length

        self._tigl_handel = tigl_handel
        self._wing_stuff = wing_stuff

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        print(' --> '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()]), "==>", self.identifier, "using",
              self._wing_stuff)
        return "created {id}".format(id=self.identifier)

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


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
            myDisplay.instance().display_fuse(fused_shape,
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
            myDisplay.instance().display_cut(cut_shape,
                                             shape__minuend,
                                             shape__subtrahend)

        return {self.identifier: cut_shape}


class Intersect2ShapesCreator(AbstractShapeCreator):
    """
    Intersect (common) two shapes into one.
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

        shape = BooleanCADOperation.intersect_shape_with_shape(
            shapes[self.shape_a], shapes[self.shape_b], self.identifier)

        if self.enable_display:
            myDisplay.instance().display_common(shape,
                                                shapes[self.shape_a],
                                                shapes[self.shape_b])

        return {self.identifier: shape}


class FuselageShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 right_main_wing_index: int,
                 ribcage_factor: float,
                 fuselage_reinforcement_shape_id: str,
                 fuselage_base_shape_id: str = None,
                 cpacs_configuration: CCPACSConfiguration = None,
                 tigl_handel=None):
        self.identifier: str = creator_id
        self.fuselage_reinforcement_shape_id = fuselage_reinforcement_shape_id
        self.fuselage_base_shape_id = fuselage_base_shape_id
        self.fuselage_index = fuselage_index
        self.right_main_wing_index = right_main_wing_index
        self.ribcage_factor = ribcage_factor
        self._tigl_handel = tigl_handel
        self._configuration = configuration
        self._cpacs_configuration = cpacs_configuration
        self._configuration = configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        check = [self.fuselage_reinforcement_shape_id, self.fuselage_base_shape_id] \
            if self.fuselage_base_shape_id is not None else [self.fuselage_reinforcement_shape_id]
        AbstractShapeCreator.check_if_shapes_are_available(check, **kwargs)

        named_fuselage_loft = kwargs.get(self.fuselage_base_shape_id)\
            if self.fuselage_base_shape_id is not None \
            else ccpacs_configuration.get_fuselage(self.fuselage_index).get_loft()

        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        shape = FuselageFactory.create_fuselage_with_sharp_ribs(
            cpacs_configuration=ccpacs_configuration,
            shape__fuselage_loft=named_fuselage_loft,
            shape__fuselage_reinforcement_wing_support=kwargs[self.fuselage_reinforcement_shape_id],
            fuselage_index=self.fuselage_index,
            right_main_wing_index=self.right_main_wing_index,
            ribcage_factor=self.ribcage_factor)
        return {str(self.identifier): shape}

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


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
                 cpacs_configuration: CCPACSConfiguration = None,
                 tigl_handel=None):
        self.identifier = creator_id
        self.fuselage_index = fuselage_index
        self.mount_plate_thickness = mount_plate_thickness
        self.engine_index = engine_index
        self._tigl_handel = tigl_handel
        self._configuration = configuration
        self._cpacs_configuration = cpacs_configuration
        self._configuration = configuration

    def create_shape(self, input_shapes: dict[str, tgl_geom.CNamedShape], **kwargs) -> dict[str, tgl_geom.CNamedShape]:
        print('--> '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()]), "==>", self.identifier)

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




if __name__ == "__main__":
    CPACS_FILE_NAME = "aircombat_v14"
    NUMBER_OF_CUTS = 5
    import logging
    import Extra.tigl_extractor as tg

    logging.info(f"Start test for Fuselage Factory with CPACS file {CPACS_FILE_NAME}")

    from Extra.mydisplay import myDisplay
    from tigl3.configuration import CCPACSConfiguration, \
        CCPACSConfigurationManager_get_instance
    shapeDisplay = myDisplay.instance(True, 5)

    tigl_h = tg.get_tigl_handler(CPACS_FILE_NAME)
    ccpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance().get_configuration(tigl_h._handle.value)

    configuration = Configuration(tigl_h)

    # defining the shape creators
    shapeSlicer = SliceShapesCreator("fuselage_slicer", number_of_parts=5)
    engineMount = EngineMountShapeCreator("engine_mount",
                                          fuselage_index=1,
                                          mount_plate_thickness=0.005)
    fuselage = FuselageShapeCreator("fuselage",
                                    fuselage_base_shape_id="engine_cape.loft",
                                    fuselage_index=1,
                                    fuselage_reinforcement_shape_id="fuselage_reinforcement",
                                    right_main_wing_index=1,
                                    ribcage_factor=0.5)
    shapeStlExport = ExportToStlCreator("stl_exporter",
                                        additional_shapes_to_export=["engine_mount", "engine_cape.cape"])
    engineCape = EngineCapeShapeCreator("engine_cape",
                                        engine_index=1,
                                        fuselage_index=1,
                                        mount_plate_thickness=0.005)
    fuselage_reinforcement = FuselageReinforcementShapeCreator("fuselage_reinforcement",
                                                               fuselage_index=1,
                                                               right_main_wing_index=1,
                                                               ribcage_factor=0.5,
                                                               rib_width=0.002,
                                                               reinforcement_pipes_radius=0.003)
    wing_support = FuselageWingSupportShapeCreator("wing_support",
                                                   fuselage_index=1,
                                                   right_main_wing_index=1)
    fuse_reinforcement_wing_sup = Fuse2ShapesCreator("reinforcement",
                                                     shape_a="fuselage_reinforcement",
                                                     shape_b="wing_support")

    # building up the workflow
    fuselageNode = ConstructionStepNode(fuselage)
    engineMountNode = ConstructionStepNode(engineMount)
    shapeSlicerMountNode = ConstructionStepNode(shapeSlicer)
    shapeStlExportNode = ConstructionStepNode(shapeStlExport)
    engineCapeNode = ConstructionStepNode(engineCape)
    fuselageReinforcementNode = ConstructionStepNode(fuselage_reinforcement)
    wingSupportNode = ConstructionStepNode(wing_support)
    reinforcementNode = ConstructionStepNode(fuse_reinforcement_wing_sup)

    # linking the map
    engineCapeNode.append(engineMountNode)
    engineMountNode.append(fuselageReinforcementNode)
    fuselageReinforcementNode.append(wingSupportNode)
    wingSupportNode.append(reinforcementNode)
    reinforcementNode.append(fuselageNode)
    fuselageNode.append(shapeSlicerMountNode)
    shapeSlicerMountNode.append(shapeStlExportNode)

    import json

    # dump to a json string
    json_data: str = json.dumps(engineCapeNode, indent=4, cls=GeneralJSONEncoder)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap = json.loads(json_data, cls=GeneralJSONDecoder,
                       cpacs_configuration=ccpacs_configuration,
                       tigl_handel=tigl_h,
                       wing_stuff="wing_stuff is okay")

    # dump again to check
    print(json.dumps(myMap, indent=4, cls=GeneralJSONEncoder))

    # build on basis of deserialized json
    structure = myMap.construct()

    from pprint import pprint
    pprint(structure)

    shapeDisplay.start()

    pass
