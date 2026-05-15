"""Design Version Service — snapshot, restore, and diff aeroplane configurations."""

import logging
from typing import Any

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.exceptions import InternalError, NotFoundError
from app.models.aeroplanemodel import (
    AeroplaneModel,
    DesignVersionModel,
    WeightItemModel,
)
from app.models.mission_objective import MissionObjectiveModel
from app.schemas.design_version import (
    DesignVersionCreate,
    DesignVersionDiff,
    DesignVersionRead,
    DesignVersionSummary,
)

logger = logging.getLogger(__name__)


def _get_aeroplane(db: Session, aeroplane_uuid) -> AeroplaneModel:
    aeroplane = db.query(AeroplaneModel).filter(
        AeroplaneModel.uuid == aeroplane_uuid
    ).first()
    if not aeroplane:
        raise NotFoundError(entity="Aeroplane", resource_id=aeroplane_uuid)
    return aeroplane


def _get_version(db: Session, aeroplane: AeroplaneModel, version_id: int) -> DesignVersionModel:
    ver = (
        db.query(DesignVersionModel)
        .filter(DesignVersionModel.aeroplane_id == aeroplane.id, DesignVersionModel.id == version_id)
        .first()
    )
    if ver is None:
        raise NotFoundError(entity="DesignVersion", resource_id=version_id)
    return ver


# ── snapshot helpers ─────────────────────────────────────────────────

def _serialize_wing(wing) -> dict[str, Any]:
    """Serialize a WingModel to a plain dict for snapshot storage."""
    result: dict[str, Any] = {
        "name": wing.name,
        "symmetric": wing.symmetric,
        "x_secs": [],
    }
    for xsec in wing.x_secs:
        xsec_dict: dict[str, Any] = {
            "sort_index": xsec.sort_index,
        }
        # copy scalar columns
        for col in xsec.__table__.columns:
            if col.name not in ("id", "wing_id", "sort_index"):
                xsec_dict[col.name] = getattr(xsec, col.name)
        result["x_secs"].append(xsec_dict)
    return result


def _serialize_fuselage(fuselage) -> dict[str, Any]:
    result: dict[str, Any] = {"name": fuselage.name, "x_secs": []}
    for xsec in fuselage.x_secs:
        xsec_dict: dict[str, Any] = {"sort_index": xsec.sort_index}
        for col in xsec.__table__.columns:
            if col.name not in ("id", "fuselage_id", "sort_index"):
                xsec_dict[col.name] = getattr(xsec, col.name)
        result["x_secs"].append(xsec_dict)
    return result


def _serialize_mission_objective(
    obj: MissionObjectiveModel | None,
) -> dict[str, Any] | None:
    """Serialize the singular MissionObjectiveModel for a design-version snapshot.

    Returns ``None`` when no objective has been persisted for the aeroplane.
    Maps to the new schema (gh-546): the 7-axis performance targets plus
    the field-performance inputs.
    """
    if obj is None:
        return None
    return {
        "mission_type": obj.mission_type,
        "target_cruise_mps": obj.target_cruise_mps,
        "target_stall_safety": obj.target_stall_safety,
        "target_maneuver_n": obj.target_maneuver_n,
        "target_glide_ld": obj.target_glide_ld,
        "target_climb_energy": obj.target_climb_energy,
        "target_wing_loading_n_m2": obj.target_wing_loading_n_m2,
        "target_field_length_m": obj.target_field_length_m,
        "available_runway_m": obj.available_runway_m,
        "runway_type": obj.runway_type,
        "t_static_N": obj.t_static_N,
        "takeoff_mode": obj.takeoff_mode,
    }


def _serialize_weight_items(items: list[WeightItemModel]) -> list[dict[str, Any]]:
    result = []
    for item in items:
        result.append({
            col.name: getattr(item, col.name)
            for col in item.__table__.columns
            if col.name not in ("id", "aeroplane_id")
        })
    return result


def _build_snapshot(aeroplane: AeroplaneModel) -> dict[str, Any]:
    return {
        "name": aeroplane.name,
        "total_mass_kg": aeroplane.total_mass_kg,
        "xyz_ref": aeroplane.xyz_ref,
        "wings": [_serialize_wing(w) for w in aeroplane.wings],
        "fuselages": [_serialize_fuselage(f) for f in aeroplane.fuselages],
        "mission_objective": _serialize_mission_objective(
            getattr(aeroplane, "mission_objective", None)
        ),
        "weight_items": _serialize_weight_items(list(aeroplane.weight_items)),
    }


# ── CRUD ─────────────────────────────────────────────────────────────

def list_versions(db: Session, aeroplane_uuid) -> list[DesignVersionSummary]:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    rows = (
        db.query(DesignVersionModel)
        .filter(DesignVersionModel.aeroplane_id == aeroplane.id)
        .all()
    )
    return [
        DesignVersionSummary(
            id=v.id,
            label=v.label,
            description=v.description,
            parent_version_id=v.parent_version_id,
            created_at=v.created_at,
        )
        for v in rows
    ]


def create_version(
    db: Session, aeroplane_uuid, data: DesignVersionCreate
) -> DesignVersionSummary:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        snapshot = _build_snapshot(aeroplane)
        ver = DesignVersionModel(
            aeroplane_id=aeroplane.id,
            label=data.label,
            description=data.description,
            snapshot=snapshot,
        )
        db.add(ver)
        db.flush()
        db.refresh(ver)
        return DesignVersionSummary(
            id=ver.id,
            label=ver.label,
            description=ver.description,
            parent_version_id=ver.parent_version_id,
            created_at=ver.created_at,
        )
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in create_version: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def get_version(db: Session, aeroplane_uuid, version_id: int) -> DesignVersionRead:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    ver = _get_version(db, aeroplane, version_id)
    return DesignVersionRead(
        id=ver.id,
        label=ver.label,
        description=ver.description,
        parent_version_id=ver.parent_version_id,
        created_at=ver.created_at,
        snapshot=ver.snapshot,
    )


def delete_version(db: Session, aeroplane_uuid, version_id: int) -> None:
    try:
        aeroplane = _get_aeroplane(db, aeroplane_uuid)
        ver = _get_version(db, aeroplane, version_id)
        db.delete(ver)
        db.flush()
    except NotFoundError:
        raise
    except SQLAlchemyError as exc:
        logger.error("DB error in delete_version: %s", exc)
        raise InternalError(message=f"Database error: {exc}") from exc


def diff_versions(
    db: Session, aeroplane_uuid, version_a_id: int, version_b_id: int
) -> DesignVersionDiff:
    aeroplane = _get_aeroplane(db, aeroplane_uuid)
    ver_a = _get_version(db, aeroplane, version_a_id)
    ver_b = _get_version(db, aeroplane, version_b_id)
    changes = _compute_diff(ver_a.snapshot, ver_b.snapshot)
    return DesignVersionDiff(
        version_a=version_a_id,
        version_b=version_b_id,
        changes=changes,
    )


# ── diff engine ──────────────────────────────────────────────────────

def _compute_diff(
    snap_a: dict[str, Any], snap_b: dict[str, Any], prefix: str = ""
) -> list[dict[str, Any]]:
    """Recursive structural diff between two snapshot dicts."""
    changes: list[dict[str, Any]] = []

    all_keys = set(snap_a.keys()) | set(snap_b.keys())
    for key in sorted(all_keys):
        path = f"{prefix}.{key}" if prefix else key
        val_a = snap_a.get(key)
        val_b = snap_b.get(key)

        if val_a == val_b:
            continue

        if val_a is None and val_b is not None:
            changes.append({"path": path, "type": "added", "value": val_b})
        elif val_a is not None and val_b is None:
            changes.append({"path": path, "type": "removed", "value": val_a})
        elif isinstance(val_a, dict) and isinstance(val_b, dict):
            changes.extend(_compute_diff(val_a, val_b, path))
        elif isinstance(val_a, list) and isinstance(val_b, list):
            changes.extend(_diff_lists(val_a, val_b, path))
        else:
            changes.append({"path": path, "type": "changed", "old": val_a, "new": val_b})

    return changes


def _diff_lists(
    list_a: list, list_b: list, path: str
) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    max_len = max(len(list_a), len(list_b))
    for i in range(max_len):
        item_path = f"{path}[{i}]"
        if i >= len(list_a):
            changes.append({"path": item_path, "type": "added", "value": list_b[i]})
        elif i >= len(list_b):
            changes.append({"path": item_path, "type": "removed", "value": list_a[i]})
        elif isinstance(list_a[i], dict) and isinstance(list_b[i], dict):
            changes.extend(_compute_diff(list_a[i], list_b[i], item_path))
        elif list_a[i] != list_b[i]:
            changes.append({"path": item_path, "type": "changed", "old": list_a[i], "new": list_b[i]})
    return changes
