import inspect
from json import JSONEncoder, JSONDecoder

from cad_designer.airplane.ConstructionRootNode import ConstructionRootNode
from cad_designer.airplane.ConstructionStepNode import ConstructionStepNode
from cad_designer.airplane.creator import *
import cad_designer.cq_plugins


# even though this imports may not be referenced directly
# they are needed as we use inspection, where they are called

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


def _coerce_params(cls, params: dict) -> dict:
    """Coerce JSON values to match __init__ type annotations.

    Prevents TypeError when JSON stores numeric values as strings
    (e.g. "0.1" instead of 0.1). Handles NewType wrappers (ShapeId, CreatorId).
    """
    try:
        hints = {k: v for k, v in cls.__init__.__annotations__.items() if k != "return"}
    except AttributeError:
        return params
    coerced = {}
    for key, value in params.items():
        if value is None or key not in hints:
            coerced[key] = value
            continue
        hint = hints[key]
        try:
            # Unwrap NewType (ShapeId → str, CreatorId → str)
            target = getattr(hint, "__supertype__", None) or hint
            if target is float and not isinstance(value, float):
                coerced[key] = float(value)
            elif target is int and not isinstance(value, int):
                coerced[key] = int(value)
            elif target is bool and not isinstance(value, bool):
                coerced[key] = bool(value)
            elif target is str and not isinstance(value, str):
                coerced[key] = str(value)
            else:
                coerced[key] = value
        except (ValueError, TypeError):
            coerced[key] = value
    return coerced


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
        intersection_dict = _coerce_params(cls, intersection_dict)
        return cls(**intersection_dict)
