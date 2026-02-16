from typing import Any

from pydantic import BaseModel


class CreateAeroplaneResponse(BaseModel):
    id: str


class OperationStatusResponse(BaseModel):
    status: str
    operation: str


class StaticUrlResponse(BaseModel):
    url: str


class CadTaskAcceptedResponse(BaseModel):
    aeroplane_id: str
    href: str


class CadTaskStatusResponse(BaseModel):
    aeroplane_id: str
    href: str
    status: str
    message: str | None = None
    result: dict[str, Any] | None = None


class ZipAssetResponse(BaseModel):
    url: str
    filename: str
    mime_type: str


class AirplaneConfigurationResponse(BaseModel):
    name: str
    total_mass_kg: float
    wings: list[dict[str, Any]]
    fuselages: list[dict[str, Any]] | None = None
