import inspect
from json import JSONEncoder, JSONDecoder

from Airplane.FuselageConstructionSteps import ConstructionStepNode
from Airplane.FuselageConstructionSteps import *

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
        # remove kwargs for JSONDecoder from kwargs for our objects
        init_params = inspect.signature(JSONDecoder.__init__).parameters
        intersection = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
        JSONDecoder.__init__(self, object_hook=self.object_hook, *args, **intersection)

    def object_hook(self, dic: dict):
        if GeneralJSONEncoder.JSON_CLASS_TYPE_ID not in dic:
            return dic
        import sys

        cls = getattr(sys.modules[__name__], dic[GeneralJSONEncoder.JSON_CLASS_TYPE_ID])
        init_params = inspect.signature(cls.__init__).parameters

        if "kwargs" in init_params.keys():
            intersection_dict = dic
            intersection_dict.update(self.kwargs)
        else:
            # select the extra parameters found in kwargs
            intersection = {k: self.kwargs[k] for k in self.kwargs.keys() & init_params.keys()}
            # get init_params from dic
            intersection_dict ={k: dic[k] for k in dic.keys() & init_params.keys()}
            # join and create object
            intersection_dict.update(intersection)
        return cls(**intersection_dict)
