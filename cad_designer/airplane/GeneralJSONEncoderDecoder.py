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


def _resolve_base_type(hint) -> type | None:
    """Resolve a type hint to its base Python type (float, int, bool, str).

    Handles: plain types, NewType wrappers, string annotations,
    Annotated types (e.g. Annotated[float, Field(...)]), and
    pydantic constrained types (confloat, etc.).
    """
    import typing

    # If hint is a string (from `from __future__ import annotations`),
    # try to identify the base type from the string
    if isinstance(hint, str):
        hint_lower = hint.lower()
        if hint_lower == "float" or hint_lower.startswith("confloat"):
            return float
        if hint_lower == "int" or hint_lower.startswith("nonnegativeint") or hint_lower.startswith("conint"):
            return int
        if hint_lower == "bool":
            return bool
        if hint_lower == "str":
            return str
        if hint_lower in ("creatorid", "shapeid"):
            return str
        # Annotated[float, ...] or Factor (which is confloat)
        if "factor" in hint_lower:
            return float
        if hint_lower.startswith("annotated["):
            # Extract base type from "Annotated[float, ...]"
            inner = hint_lower.split("[", 1)[1].split(",", 1)[0].strip()
            if inner == "float":
                return float
            if inner == "int":
                return int
            if inner == "str":
                return str
            if inner == "bool":
                return bool
        return None

    # Unwrap NewType
    supertype = getattr(hint, "__supertype__", None)
    if supertype:
        return supertype

    # Unwrap Annotated
    origin = getattr(hint, "__origin__", None)
    if origin is not None:
        # typing.Annotated has __origin__ = the base type (in Python 3.11+)
        # For Annotated[float, ...], __args__[0] is float
        args = getattr(hint, "__args__", None)
        if args:
            return _resolve_base_type(args[0])

    if hint in (float, int, bool, str):
        return hint

    return None


def _normalize_numeric_string(value) -> str:
    """Normalize a numeric string to use '.' as decimal separator.

    Handles common locale formats:
    - "0,1"         → "0.1"       (comma as decimal)
    - "1.234,56"    → "1234.56"   (German: dot=thousands, comma=decimal)
    - "1,234.56"    → "1234.56"   (English: comma=thousands, dot=decimal)
    - "1234"        → "1234"      (no separator)
    """
    s = str(value).strip()
    has_dot = "." in s
    has_comma = "," in s

    if has_dot and has_comma:
        # Both present: the LAST separator is the decimal
        dot_pos = s.rfind(".")
        comma_pos = s.rfind(",")
        if comma_pos > dot_pos:
            # "1.234,56" → German format: dot is thousands, comma is decimal
            s = s.replace(".", "").replace(",", ".")
        else:
            # "1,234.56" → English format: comma is thousands, dot is decimal
            s = s.replace(",", "")
    elif has_comma and not has_dot:
        # Only comma: treat as decimal separator
        s = s.replace(",", ".")

    return s


def _coerce_params(cls, params: dict) -> dict:
    """Coerce JSON values to match __init__ type annotations.

    Prevents TypeError when JSON stores numeric values as strings
    (e.g. "0.1" instead of 0.1). Handles NewType wrappers, string
    annotations from `from __future__ import annotations`, and
    Annotated types.
    """
    try:
        raw_hints = {k: v for k, v in cls.__init__.__annotations__.items() if k != "return"}
    except AttributeError:
        return params
    coerced = {}
    for key, value in params.items():
        if value is None or key not in raw_hints:
            coerced[key] = value
            continue
        target = _resolve_base_type(raw_hints[key])
        if target is None:
            coerced[key] = value
            continue
        try:
            if target is float and not isinstance(value, float):
                coerced[key] = float(_normalize_numeric_string(value))
            elif target is int and not isinstance(value, (int, bool)):
                coerced[key] = int(float(_normalize_numeric_string(value)))
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
