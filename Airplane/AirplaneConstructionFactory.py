import inspect
from json import JSONEncoder, JSONDecoder

import abc
from collections.abc import MutableMapping
from collections.abc import Iterable

import tigl3.geometry as tgl_geom
from tigl3.configuration import CCPACSConfiguration

from Airplane import Configuration
from Airplane.Fuselage.EngineMountFactory import EngineMountFactory


class AbstractShapeCreator(metaclass=abc.ABCMeta):
    """
    Base class for shape creating/modifying nodes.
    """

    @property
    @abc.abstractmethod
    def identifier(self):
        """
        This property is abstract and used in the ConstructionStepKnode. The variable, that ist used to hold the
        property should not be private (does not start with an '_'). Otherwise, it will not be de-/serialized.
        :return: identifier as name of this shape. If used several times the shape will be overwritten in future steps.
        """
        pass

    @abc.abstractmethod
    def create_shape(self, input_shapes: Iterable[tgl_geom.CNamedShape], **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        """
        This method will create a shape. The shape can depend on shapes of previous steps. All previous steps
        occur in the kwargs variable. The key are the 'identifier's and the values hold the shapes.
        :param input_shapes: shapes created in the step before
        :param kwargs: the previously created shapes identified by their 'identifier's
        :return: a new shape
        """
        pass


class AbstractConstructionStep(metaclass=abc.ABCMeta):
    """
    This is an interface for a construction Step. A construction step can execute
    """

    @abc.abstractmethod
    def construct(self, input_shapes: Iterable[tgl_geom.CNamedShape], **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        pass


class ConstructionStepNode(AbstractConstructionStep, MutableMapping):
    """
    A node that is a map and holds in itself the following steps in the construction tree
    """

    def __init__(self, creator: AbstractShapeCreator, successors=None):
        """
        :param geometry: the geometry, that is created in this node
        :param successors: all following construction steps
        """
        self.successors = {} if successors is None else successors
        self.creator: AbstractShapeCreator = creator
        self._output_shapes = None

    def __getitem__(self, key: str):
        return self.successors[key]

    def __setitem__(self, key, value):
        self.successors[key] = value

    def __delitem__(self, key):
        del self.successors[key]

    def __len__(self):
        return len(self.successors)

    def __iter__(self):
        return iter(self.successors)

    def append(self, value) -> None:
        """
        Append a ConstructionStepNode to this map.
        :param value: ConstructionStepNode
        """
        self.update({value.creator.identifier: value})

    def construct(self, input_shapes: Iterable[tgl_geom.CNamedShape] = None, **kwargs):
        """
        Executes the construction of all shapes based on the defined workflow structure.
        :param input_shapes: the shapes that have been constructed in the last step
        :param kwargs: holding the shapes of the previous steps as a dict of shape lists (input_shapes is the last entry of this dict)
        :return: a structure based on the identifiers, that represents the workflow
        """
        self._output_shapes: Iterable[tgl_geom.CNamedShape] = self.creator.create_shape(input_shapes=input_shapes, **kwargs)
        kwargs[self.creator.identifier] = self._output_shapes
        output_list: Iterable[tgl_geom.CNamedShape] = []
        for key in self.successors:
            output_list.append(self.successors.get(key).construct(input_shapes=self._output_shapes, **kwargs))
        output_dict = {self.creator.identifier: {"shapes": {s.name(): s for s in self._output_shapes}, "steps": output_list}}
        return output_dict


class GeneralJSONEncoder(JSONEncoder):
    """
    Encodes a construction workflow to json. Each objects type will be identified by their name, found under
    JSON_CLASS_TYPE_ID.
    """
    JSON_CLASS_TYPE_ID = '$TYPE'

    def default(self, o: ConstructionStepNode):
        # only selecting public variables for encoding and not the private ones
        dic = {k: v for k, v in o.__dict__.items() if not k.startswith('_')}
        # adding a field for decoding polymorphism
        dic[GeneralJSONEncoder.JSON_CLASS_TYPE_ID] = o.__class__.__name__
        return dic


class GeneralJSONDecoder(JSONDecoder):
    def __init__(self, *args, **kwargs):
        """
        Constructor can inject keyword args in the objects that are decoded.
        :param args: will be propagated to the JSONDecoder constructor.
        :param kwargs: all keyword arguments will be propagated further to constructors of the classes found in
        the json. The keyword arguments of JSONDecoder can be used as well.
        """
        self.kwargs = kwargs
        import json
        # remove kwargs for JSONDecoder from kwargs for our objects
        init_params = inspect.signature(json.JSONDecoder.__init__).parameters
        intersection = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
        json.JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **intersection)

    def object_hook(self, dic: dict):
        if GeneralJSONEncoder.JSON_CLASS_TYPE_ID not in dic:
            return dic
        import sys

        cls = getattr(sys.modules[__name__], dic[GeneralJSONEncoder.JSON_CLASS_TYPE_ID])
        init_params = inspect.signature(cls.__init__).parameters

        # select the extra parameters found in kwargs
        intersection = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
        # get init_params from dic
        intersection_dict = {k: dic[k] for k in dic.keys() & init_params.keys()}
        # join and create object
        intersection.update(intersection_dict)
        return cls(**intersection)


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

    def create_shape(self, input_shape: tgl_geom.CNamedShape, **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        print(' --> '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()]), "==>", self.identifier, "using",
              self._wing_stuff)
        return "created {id}".format(id=self.identifier)

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


# !!! no function yet only example
class FuseShapesCreator(AbstractShapeCreator):
    """
    This class shows an example on how you can use a list of shapes, that have been created in previous steps.
    """

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, shapes_to_fuse=None):
        self.identifier = creator_id
        self.shapes_to_fuse = shapes_to_fuse

    def _check_if_shapes_are_available(self, **kwargs):
        """
        Check if the shapes, that are needed, have been created before and are available in kwargs.
        :param kwargs:
        :return:
        """
        shapes = {}
        if self.shapes_to_fuse is not None:
            shapes = {k: kwargs[k] for k in kwargs.keys() & self.shapes_to_fuse}
            missing = {(k if k not in kwargs.keys() else None) for k in self.shapes_to_fuse}  # check what is missing
            missing = [i for i in missing if i is not None]  # remove all Nones
            if len(missing) > 0:
                raise KeyError('shapes are missing for fusing: {}'.format(missing))
        return shapes

    def create_shape(self, input_shapes: Iterable[tgl_geom.CNamedShape], **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        shapes = self._check_if_shapes_are_available(**kwargs)

        print('--> '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()]), "==>", self.identifier, ': ',
              ', '.join(['{}={!r}'.format(k, v) for k, v in shapes.items()]))
        return "created {id}".format(id=self.identifier)


class FuselageShapeCreator(AbstractShapeCreator):
    def __init__(self, creator_id: str,
                 fuselage_index: int,
                 right_main_wing_index: int,
                 ribcage_factor: float,
                 plate_thickness: float,
                 rib_width: float,
                 reinforcement_pipes_radius: float,
                 cpacs_configuration: CCPACSConfiguration = None,
                 tigl_handel=None):
        self.identifier = creator_id
        self.fuselage_index = fuselage_index
        self.right_main_wing_index = right_main_wing_index
        self.ribcage_factor = ribcage_factor
        self.plate_thickness = plate_thickness
        self.rib_width = rib_width
        self.reinforcement_pipes_radius = reinforcement_pipes_radius
        self._tigl_handel = tigl_handel
        self._configuration = configuration
        self._cpacs_configuration = cpacs_configuration
        self._configuration = configuration

    def create_shape(self, input_shapes: Iterable[tgl_geom.CNamedShape], **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        print('--> '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()]), "==>", self.identifier)
        from Airplane.Fuselage.FuselageFactory import FuselageFactory
        fuselage_factory = FuselageFactory(cpacs_configuration=self._cpacs_configuration,
                                           fuselage_index=self.fuselage_index,
                                           right_main_wing_index=self.right_main_wing_index)
        fuselage_factory.create_fuselage_with_sharp_ribs(
            ribcage_factor=self.ribcage_factor,
            plate_thickness=self.plate_thickness,
            rib_width=self.rib_width,
            reinforcement_pipes_radius=self.reinforcement_pipes_radius)
        return [fuselage_factory.get_shape()]

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

    def create_shape(self, input_shapes: Iterable[tgl_geom.CNamedShape], **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        print('--> '.join(['{}={!r}'.format(k, v) for k, v in kwargs.items()]), "==>", self.identifier)
        _engine_mount_factory = EngineMountFactory(cpacs_configuration=self._cpacs_configuration,
                                                   fuselage_index=self.fuselage_index)
        return [_engine_mount_factory.create_engine_mount(plate_thickness=self.mount_plate_thickness)]

    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value


class SliceShapesCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, number_of_cuts: int):
        self.identifier = creator_id
        self.number_of_cuts = number_of_cuts

    def create_shape(self, input_shapes: Iterable[tgl_geom.CNamedShape], **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        from Extra.ShapeSlicer import ShapeSlicer
        parts = []
        for shape in input_shapes:
            my_slicer = ShapeSlicer(shape, self.number_of_cuts)
            my_slicer.slice_by_cut()
            parts.extend(my_slicer.parts_list)
        return parts


class ExportToStlCreator(AbstractShapeCreator):
    @property
    def identifier(self):
        return self.creator_id

    @identifier.setter
    def identifier(self, value):
        self.creator_id = value

    def __init__(self, creator_id: str, additional_shapes_to_export: Iterable[str]=None):
        self.identifier = creator_id
        self.additional_shapes_to_export = additional_shapes_to_export

    def _check_if_shapes_are_available(self, **kwargs):
        """
        Check if the shapes, that are needed, have been created before and are available in kwargs.
        :param kwargs:
        :return:
        """
        shapes = {}
        if self.additional_shapes_to_export is not None:
            shapes = {k: kwargs[k] for k in kwargs.keys() & self.additional_shapes_to_export}
            missing = {(k if k not in kwargs.keys() else None) for k in self.additional_shapes_to_export}  # check what is missing
            missing = [i for i in missing if i is not None]  # remove all Nones
            if len(missing) > 0:
                raise KeyError('shapes are missing for fusing: {}'.format(missing))
        return shapes

    def create_shape(self, input_shapes: Iterable[tgl_geom.CNamedShape], **kwargs) -> Iterable[tgl_geom.CNamedShape]:
        shapes = self._check_if_shapes_are_available(**kwargs)
        all_shapes = [*shapes.values()]
        all_shapes = [item for sublist in all_shapes for item in sublist]
        all_shapes.extend(input_shapes)

        import stl_exporter.Exporter as Exporter
        stl_exporter = Exporter.Exporter()
        stl_exporter.write_stls_from_list(all_shapes)
        return all_shapes


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
    cpacs_configuration: CCPACSConfiguration = CCPACSConfigurationManager_get_instance().get_configuration(tigl_h._handle.value)

    configuration = Configuration(tigl_h)

    # defining the shape creators
    shapeSlicer = SliceShapesCreator("fuselage_slicer", number_of_cuts=5)
    engineMount = EngineMountShapeCreator("engine_mount", fuselage_index=1, mount_plate_thickness=0.005)
    fuselage0 = FuselageShapeCreator("fuselage",
                                     fuselage_index=1,
                                     right_main_wing_index=1,
                                     ribcage_factor=0.5,
                                     plate_thickness=0.005,
                                     rib_width=0.002,
                                     reinforcement_pipes_radius=0.003)
    shapeStlExport = ExportToStlCreator("stl_exporter", additional_shapes_to_export=["engine_mount"])

    # building up the workflow
    fuselageNode = ConstructionStepNode(fuselage0)
    engineMountNode = ConstructionStepNode(engineMount)
    shapeSlicerMountNode = ConstructionStepNode(shapeSlicer)
    shapeStlExportNode = ConstructionStepNode(shapeStlExport)

    # linking the map
    fuselageNode.append(shapeSlicerMountNode)
    engineMountNode.append(fuselageNode)
    shapeSlicerMountNode.append(shapeStlExportNode)

    import json

    # dump to a json string
    json_data: str = json.dumps(engineMountNode, indent=4, cls=GeneralJSONEncoder)

    # load the string
    # tigl_handel is parameter which is not in the json file, but needed by the constructor of a creator class
    myMap = json.loads(json_data, cls=GeneralJSONDecoder,
                       cpacs_configuration=cpacs_configuration,
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
