"""The one seam from a stored aeroplane to the kernel's input (gh-1282 slice 2, ADR 0030).

A stored aeroplane becomes an ``AircraftInput`` of the kernel in three steps, each reusing what the
application already has:

1. The geometry document is the application's own (``aeroplane_service.get_aeroplane_schema``, the
   document of ``GET /aeroplanes/{id}``, AIRPLANE-GEOMETRY.md). This module adds only what that
   document leaves out: ``total_mass_kg``, the spars in metres (the database keeps millimetres,
   ``wing_service._convert_spare_to_meters``) and each airfoil reference resolved to its inline
   contour (the kernel loads no files). A reference the application cannot resolve to a file is
   passed on unchanged: the kernel accepts a NACA designation and reports any other string as
   ``unresolved_airfoil`` at its input path.
2. The mass is the ``mass`` design assumption with its active source (estimate or calculated), the
   value the application computes with (``_load_effective_mass_kg``), and nothing else: without the
   assumption no mass is passed and the kernel reports it missing where a result needs it.
   Flap deflections are not taken from the aircraft; the kernel takes them from the canon's
   ``defaults.yaml`` unless the caller passes them, as for the reference fleet.
3. The kernel's input model parses the document. Whatever does not convert is a ``ValidationError``
   whose ``input_errors`` name each offending item by its input path, in the kernel's notation
   (``airplane.wings["Main Wing"].x_secs[2].chord``), never a silent default (ADR 0020).
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from aero_kernel.reference_fleet import read_selig_coordinates
from aero_kernel.schema import AircraftInput
from pydantic import ValidationError as PydanticValidationError
from pydantic_core import ErrorDetails
from sqlalchemy.orm import Session

from app import schemas
from app.core.exceptions import ValidationError
from app.models.aeroplanemodel import AeroplaneModel
from app.services import aeroplane_service
from app.services.create_wing_configuration import _resolve_airfoil_reference
from app.services.operating_point_generator_service import _load_effective_mass_kg
from app.services.wing_service import _convert_spare_to_meters

MASS_SLUG = "aircraft-mass"
AIRPLANE_PATH = "airplane"

# The members of the document that are maps by name (format ch. 3): the next path element is a key.
_NAMED_MAPS = ("wings", "fuselages")


def input_path(location: Sequence[int | str]) -> str:
    """Write a validation error location in the kernel's input path notation.

    A list index is ``[i]``, a key of a map by name is ``["name"]`` (JSON-escaped), every other
    element a ``.field``: ``("airplane", "wings", "Main", "x_secs", 2, "chord")`` becomes
    ``airplane.wings["Main"].x_secs[2].chord``.

    Args:
        location: The location of a pydantic error, starting at the input's root field.

    Returns:
        The dotted path.
    """
    path = ""
    after_named_map = False
    for element in location:
        if isinstance(element, int):
            path += f"[{element}]"
        elif after_named_map:
            path += '["' + element.replace("\\", "\\\\").replace('"', '\\"') + '"]'
        else:
            path += f".{element}" if path else element
        after_named_map = (
            isinstance(element, str) and not after_named_map and element in _NAMED_MAPS
        )
    return path


def _input_error(path: str, message: str) -> dict[str, str]:
    """One conversion failure: where it is and what is wrong."""
    return {"code": "invalid_input", "input_path": path, "message": message}


def _rejected(errors: list[dict[str, str]]) -> ValidationError:
    """The error of a stored aeroplane that does not convert, its first item in the message."""
    first = errors[0]
    return ValidationError(
        f"The stored aeroplane cannot be given to the kernel: {first['input_path']}: "
        f"{first['message']}",
        {"input_errors": errors},
    )


def _errors_at(prefix: Sequence[int | str], exc: PydanticValidationError) -> list[dict[str, str]]:
    """The items of a pydantic error, each at its input path below ``prefix``."""
    details: list[ErrorDetails] = exc.errors(include_url=False, include_context=False)
    return [_input_error(input_path([*prefix, *d["loc"]]), d["msg"]) for d in details]


def _located_schema_errors(aeroplane: AeroplaneModel) -> list[dict[str, str]]:
    """Which stored wing or fuselage the application's own document refuses, and where.

    Diagnostic only: run after ``get_aeroplane_schema`` failed, it validates each body on its own
    with the same schemas, so the error names the body.
    """
    errors: list[dict[str, str]] = []
    bodies = [("wings", wing, schemas.AsbWingSchema) for wing in aeroplane.wings or []] + [
        ("fuselages", body, schemas.FuselageSchema) for body in aeroplane.fuselages or []
    ]
    for group, body, schema in bodies:
        try:
            schema.model_validate(body, from_attributes=True)
        except PydanticValidationError as exc:
            errors += _errors_at((AIRPLANE_PATH, group, body.name), exc)
    return errors


def _spares_in_metres(plane: schemas.AeroplaneSchema) -> None:
    """Give the spars of every wing in metres, as the format has them (the database keeps mm)."""
    for wing in (plane.wings or {}).values():
        for x_sec in wing.x_secs:
            if x_sec.spare_list:
                x_sec.spare_list = [_convert_spare_to_meters(s) for s in x_sec.spare_list]


def _inline_airfoil(reference: str) -> str | dict[str, list[list[float]]]:
    """The contour of an airfoil reference the application resolves to a file, else the reference."""
    resolved = Path(_resolve_airfoil_reference(reference))
    if not resolved.is_file():
        return reference
    return {"coordinates": read_selig_coordinates(resolved)}


def geometry_document(aeroplane: AeroplaneModel, db: Session) -> dict[str, Any]:
    """The geometry document of a stored aeroplane, with inline airfoils and spars in metres.

    Args:
        aeroplane: The stored aeroplane.
        db: The session it was loaded in.

    Returns:
        The document as JSON data, ready for the kernel's input model.

    Raises:
        ValidationError: If the application's own document refuses a stored body; ``input_errors``
            names each item by its input path.
    """
    try:
        plane = aeroplane_service.get_aeroplane_schema(db, aeroplane.uuid)
    except PydanticValidationError as exc:
        raise _rejected(_located_schema_errors(aeroplane) or _errors_at((AIRPLANE_PATH,), exc))
    _spares_in_metres(plane)
    document: dict[str, Any] = plane.model_dump(mode="json", exclude_none=True)
    if aeroplane.total_mass_kg is not None:
        document["total_mass_kg"] = aeroplane.total_mass_kg
    for wing in document.get("wings", {}).values():
        for x_sec in wing["x_secs"]:
            x_sec["airfoil"] = _inline_airfoil(x_sec["airfoil"])
    return document


def effective_mass_kg(db: Session, aeroplane: AeroplaneModel) -> float | None:
    """The ``mass`` design assumption with its active source, or ``None`` without the assumption."""
    return _load_effective_mass_kg(db, aeroplane.id, None)


def kernel_input(document: dict[str, Any], values: dict[str, float]) -> AircraftInput:
    """Parse a geometry document and the input values as the kernel's input.

    Args:
        document: The geometry document as JSON data.
        values: Input values by canon slug.

    Returns:
        The kernel's input.

    Raises:
        ValidationError: If the document does not parse; ``input_errors`` names each item by its
            input path.
    """
    try:
        return AircraftInput.model_validate({"airplane": document, "values": values})
    except PydanticValidationError as exc:
        raise _rejected(_errors_at((), exc)) from exc


def stored_aircraft_input(
    db: Session, aeroplane_uuid: Any, values: dict[str, float]
) -> AircraftInput:
    """The kernel input of a stored aeroplane: its document, its mass, the caller's values over it.

    Args:
        db: The session.
        aeroplane_uuid: The aeroplane's id.
        values: The caller's input values by canon slug; they replace the aircraft's own.

    Returns:
        The kernel's input.

    Raises:
        NotFoundError: If no aeroplane has this id.
        ValidationError: If the stored aeroplane does not convert; ``input_errors`` names each
            item by its input path.
    """
    aeroplane = aeroplane_service.get_aeroplane_by_uuid(db, aeroplane_uuid)
    document = geometry_document(aeroplane, db)
    mass = effective_mass_kg(db, aeroplane)
    own = {} if mass is None else {MASS_SLUG: mass}
    return kernel_input(document, {**own, **values})
