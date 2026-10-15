"""Canon-model types (ARCHITECTURE ch. 8.9): the interpreted canon the kernel runs on.

Every field mirrors the canon README section "Machine-readable fields" one to one, normalised as
ch. 8.9 says. All models are frozen, reject unknown fields and carry their invariants themselves:
they are canon-model types, not input types.
"""

from typing import Annotated, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

__all__ = ["Default", "Quantity", "QuantityRole", "QuantityType"]

# Numbers in the model are finite (a model with NaN would not survive its JSON form).
FiniteNumber = Annotated[float, Field(strict=True, allow_inf_nan=False)]

QuantityRole = Literal["input", "target", "derived", "output"]
QuantityType = Literal["scalar", "airplane", "curve", "polar", "curve_pair"]

# The canon's unit symbols after normalisation (ch. 8.9 stage 2); ``1`` is dimensionless and also
# stands for the not-a-number ``airplane`` types. A new unit is a model change.
Unit = Literal[
    "1",
    "m",
    "m^2",
    "kg",
    "s",
    "deg",
    "deg/s",
    "m/s",
    "m/s^2",
    "1/s",
    "1/rad",
    "1/rad^2",
    "N",
    "N/m^2",
    "Pa",
    "kg/m^3",
    "W",
    "V",
    "A",
    "ohm",
    "Wh",
    "Wh/kg",
    "rpm/V",
]

_MODEL_CONFIG = ConfigDict(extra="forbid", frozen=True)


class Default(BaseModel):
    """A value the canon states for a quantity, with its source.

    Attributes:
        value: The value, in the quantity's unit.
        source: Citation of where the value comes from (ADR 0028).
    """

    model_config = _MODEL_CONFIG

    value: FiniteNumber
    source: str = Field(min_length=1)


class Quantity(BaseModel):
    """A quantity of the canon vocabulary.

    Attributes:
        symbol: The quantity's symbol.
        unit: The unit of its values; ``1`` is dimensionless.
        role: ``input`` and ``target`` are supplied by the caller, ``derived`` and ``output`` computed.
        type: The kind of value.
        uncertainty: ``interval`` where the producer declares method worlds.
        default: The stated default, only where the canon states one.
        positive: Whether the quantity is strictly greater than zero by its definition.
    """

    model_config = _MODEL_CONFIG

    symbol: str = Field(min_length=1)
    unit: Unit
    role: QuantityRole
    type: QuantityType
    uncertainty: Literal["interval"] | None = None
    default: Default | None = None
    positive: bool = False

    @model_validator(mode="after")
    def _check_positive(self) -> Self:
        """Allow ``positive`` only on supplied quantities, and only with a positive default."""
        if not self.positive:
            return self
        if self.role not in ("input", "target"):
            msg = f"positive is only allowed on role input or target, not {self.role}"
            raise ValueError(msg)
        if self.default is not None and self.default.value <= 0:
            msg = f"default {self.default.value} of a positive quantity must be > 0"
            raise ValueError(msg)
        return self
