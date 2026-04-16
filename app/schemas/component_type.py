"""Pydantic schemas for the Component Types (gh#83)."""
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator
# Silence Pydantic's "schema shadows BaseModel attribute" warning — we do use
# the field deliberately (it's the canonical JSON name for property-lists).
import warnings
warnings.filterwarnings(
    "ignore",
    message=r'Field name "schema"',
    category=UserWarning,
)


PropertyType = Literal["number", "string", "boolean", "enum"]

# Property names must be snake_case — the UI uses them as form-field keys and
# the backend stores them as JSON keys. Leading underscore is not allowed.
_SNAKE_CASE = r"^[a-z][a-z0-9_]*$"


class PropertyDefinition(BaseModel):
    """Single property inside a ComponentType's schema."""

    name: str = Field(..., pattern=_SNAKE_CASE, min_length=1,
                      description="snake_case identifier used as key in component.specs")
    label: str = Field(..., min_length=1, description="Display name in the UI")
    type: PropertyType = Field(..., description="Data type")
    unit: Optional[str] = Field(None, description="Unit suffix for number inputs (kg/m³, mm, …)")
    required: bool = Field(False, description="True → must be present in specs")
    description: Optional[str] = Field(None)

    # Number-specific
    min: Optional[float] = Field(None)
    max: Optional[float] = Field(None)

    # Enum-specific
    options: Optional[list[str]] = Field(None)

    # Any type
    default: Optional[Any] = Field(None)

    @model_validator(mode="after")
    def _check_type_specific_fields(self) -> "PropertyDefinition":
        if self.type == "enum":
            if not self.options or len(self.options) == 0:
                raise ValueError("enum properties require a non-empty `options` list")
        if self.type != "number" and (self.min is not None or self.max is not None):
            # min/max are only meaningful for number; silently drop for others
            # instead of rejecting so the UI can keep them in state during
            # type switches.
            pass
        return self


class ComponentTypeWrite(BaseModel):
    """Payload for POST / PUT of a ComponentType."""

    name: str = Field(..., pattern=_SNAKE_CASE, min_length=1)
    label: str = Field(..., min_length=1)
    description: Optional[str] = None
    schema: list[PropertyDefinition] = Field(default_factory=list)

    @field_validator("schema")
    @classmethod
    def _unique_property_names(cls, v: list[PropertyDefinition]) -> list[PropertyDefinition]:
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            raise ValueError("property names must be unique within a schema")
        return v


class ComponentTypeRead(ComponentTypeWrite):
    model_config = ConfigDict(from_attributes=True)

    id: int
    deletable: bool
    reference_count: int = Field(0, description="Number of components using this type")
    created_at: datetime
    updated_at: datetime
