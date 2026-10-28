"""Wing roles (gh-1187): the one place that knows which wing is the main wing.

``surface_type`` is explicit, required user data. Nothing here infers a role from a name
or an area (ADR 0021); the one-time proposal for pre-existing rows lives only in the
Alembic migration ``d90a2284bf83`` and reaches this module as ``surface_type_inferred``.
"""

import logging
from collections import Counter
from typing import Iterable, Optional

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError, ValidationDomainError
from app.models.aeroplanemodel import AeroplaneModel, WingModel
from app.schemas.aeroplaneschema import SurfaceType
from app.schemas.design_warning import DesignWarning

logger = logging.getLogger(__name__)

SURFACE_TYPE_INFERRED_CODE = "SURFACE_TYPE_INFERRED"

# surface_type values that count as a horizontal / vertical stabiliser (a V-tail is both).
HORIZONTAL_TAIL_TYPES = frozenset({SurfaceType.HORIZONTAL_TAIL, SurfaceType.V_TAIL})
VERTICAL_TAIL_TYPES = frozenset({SurfaceType.VERTICAL_TAIL, SurfaceType.V_TAIL})


def wing_surface_type(wing) -> Optional[SurfaceType]:
    """Return a wing's role as an enum member, or None when it carries none."""
    value = getattr(wing, "surface_type", None)
    if value is None:
        return None
    return SurfaceType(getattr(value, "value", value))


def wings_of_type(wings: Iterable, *types: SurfaceType) -> list:
    """Return the wings whose role is one of ``types``, in the given order."""
    wanted = set(types)
    return [w for w in wings if wing_surface_type(w) in wanted]


def find_main_wing(wings: Iterable):
    """Return the main wing of ``wings``, or None when there is none."""
    mains = wings_of_type(wings, SurfaceType.MAIN_WING)
    return mains[0] if mains else None


def assert_one_main_wing(wing_types: Iterable[SurfaceType | str | None]) -> None:
    """Raise ``ValidationDomainError`` unless exactly one wing is the main wing.

    An aeroplane without wings is fine; one with wings needs exactly one ``main_wing``
    (it supplies S_ref, b_ref and c_MAC). Biplanes are out of scope.
    """
    types = [getattr(t, "value", t) for t in wing_types]
    if not types:
        return
    count = Counter(types)[SurfaceType.MAIN_WING.value]
    if count != 1:
        raise ValidationDomainError(
            message=f"The aeroplane needs exactly one wing with surface_type 'main_wing', found {count}.",
            details={"main_wing_count": count, "surface_types": types},
        )


def _other_main_wing(plane: AeroplaneModel, wing_name: str) -> Optional[WingModel]:
    others = [w for w in plane.wings if w.name != wing_name]
    return find_main_wing(others)


def check_surface_type_change(
    plane: AeroplaneModel,
    wing_name: str,
    new_type: SurfaceType,
    former_main_becomes: Optional[SurfaceType] = None,
) -> Optional[WingModel]:
    """Validate giving ``wing_name`` the role ``new_type`` (a new wing or a retype).

    Returns the former main wing that has to change to ``former_main_becomes`` (a swap), or
    None. Raises ``ValidationDomainError`` when the change would leave the aeroplane with
    two main wings, or with wings but no main wing.
    """
    current = next((w for w in plane.wings if w.name == wing_name), None)
    other_main = _other_main_wing(plane, wing_name)
    if new_type == SurfaceType.MAIN_WING and other_main is not None:
        if former_main_becomes is None or former_main_becomes == SurfaceType.MAIN_WING:
            raise ValidationDomainError(
                message=(
                    f"The aeroplane already has the main wing {other_main.name!r}; "
                    "pass former_main_becomes to swap the roles."
                ),
                details={"main_wing": other_main.name, "wing_name": wing_name},
            )
        return other_main
    is_only_main = (
        current is not None
        and wing_surface_type(current) == SurfaceType.MAIN_WING
        and other_main is None
    )
    if is_only_main and new_type != SurfaceType.MAIN_WING:
        raise ValidationDomainError(
            message=f"{wing_name!r} is the only main wing; make another wing the main wing first.",
            details={"wing_name": wing_name, "requested_surface_type": new_type.value},
        )
    return None


def check_wing_deletion(plane: AeroplaneModel, wing_name: str) -> None:
    """Reject deleting the only main wing while other wings remain."""
    wing = next((w for w in plane.wings if w.name == wing_name), None)
    if wing is None or wing_surface_type(wing) != SurfaceType.MAIN_WING:
        return
    if len(plane.wings) > 1:
        raise ValidationDomainError(
            message=f"{wing_name!r} is the only main wing; make another wing the main wing first.",
            details={"wing_name": wing_name},
        )


def resolve_wing_write(
    plane: AeroplaneModel,
    wing_name: str,
    new_type: SurfaceType,
    former_main_becomes: Optional[SurfaceType] = None,
) -> bool:
    """Validate a wing write (create or replace) and return the ``surface_type_inferred`` flag.

    The flag survives a write that keeps the proposed role (saving geometry must not confirm
    it silently); a different role is the user's own decision and clears it.
    """
    check_surface_type_change(plane, wing_name, new_type, former_main_becomes)
    current = next((w for w in plane.wings if w.name == wing_name), None)
    if current is None:
        return False
    return bool(current.surface_type_inferred) and wing_surface_type(current) == new_type


def set_wing_surface_type(
    db: Session,
    plane: AeroplaneModel,
    wing_name: str,
    new_type: SurfaceType,
    former_main_becomes: Optional[SurfaceType] = None,
) -> None:
    """Set a wing's role and mark it confirmed (also the way to confirm a proposed value)."""
    wing = next((w for w in plane.wings if w.name == wing_name), None)
    if wing is None:
        raise NotFoundError(
            message="Wing not found",
            details={"wing_name": wing_name, "aeroplane_id": str(plane.uuid)},
        )
    try:
        former = check_surface_type_change(plane, wing_name, new_type, former_main_becomes)
        if former is not None and former_main_becomes is not None:
            former.surface_type = former_main_becomes.value
            former.surface_type_inferred = False
        wing.surface_type = new_type.value
        wing.surface_type_inferred = False
        db.flush()
    except SQLAlchemyError as exc:
        logger.error("Database error when setting surface_type: %s", exc)
        raise InternalError(message=f"Database error: {exc}")


def surface_type_warnings(wings: Iterable) -> list[DesignWarning]:
    """Declare every surface_type that is only a migration proposal (ADR 0020).

    ``warning`` severity: the number is usable but a wrong role (e.g. the wrong main wing)
    changes S_ref and everything normalised by it, so it stays visible until confirmed.
    """
    warnings = []
    for wing in wings:
        if not getattr(wing, "surface_type_inferred", False):
            continue
        role = wing_surface_type(wing)
        role_name = role.value if role is not None else None
        warnings.append(
            DesignWarning(
                code=SURFACE_TYPE_INFERRED_CODE,
                category="substituted_assumption",
                severity="warning",
                message=(
                    f"The role of wing {wing.name!r} ({role_name}) was proposed from its name and "
                    "size when the roles were introduced, not chosen by you. Confirm or correct "
                    "it in the wing editor."
                ),
                context={"wing": wing.name, "surface_type": role_name},
            )
        )
    return warnings
