"""CRUD + preset lookup for Mission Objectives (gh-546)."""

from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.mission_objective import MissionObjectiveModel
from app.models.mission_preset import MissionPresetModel
from app.schemas.mission_objective import MissionObjective, MissionPreset


def _default_objective() -> MissionObjective:
    """Build a fresh MissionObjective with system defaults.

    Returned as a new instance per call so callers cannot accidentally
    mutate a shared singleton.
    """
    return MissionObjective(
        mission_type="trainer",
        target_cruise_mps=18.0,
        target_stall_safety=1.8,
        target_maneuver_n=3.0,
        target_glide_ld=12.0,
        target_climb_energy=22.0,
        target_wing_loading_n_m2=412.0,
        target_field_length_m=50.0,
        available_runway_m=50.0,
        runway_type="grass",
        t_static_N=18.0,
        takeoff_mode="runway",
    )


def get_mission_objective(db: Session, aeroplane_id: int) -> MissionObjective:
    """Return the persisted MissionObjective for an aeroplane, or the default."""
    row = (
        db.query(MissionObjectiveModel)
        .filter(MissionObjectiveModel.aeroplane_id == aeroplane_id)
        .one_or_none()
    )
    if row is None:
        return _default_objective()
    return MissionObjective.model_validate(row, from_attributes=True)


def upsert_mission_objective(
    db: Session, aeroplane_id: int, payload: MissionObjective
) -> MissionObjective:
    """Create or update the MissionObjective for an aeroplane.

    When the mission_type changes (including the first create), the preset's
    suggested_estimates are auto-applied to design_assumptions.estimate_value
    via :func:`_apply_preset_estimates` (gh-549). Only estimate_value is
    touched — calculated_value, calculated_source, and active_source remain
    owned by assumption_compute_service / AeroBuildup.
    """
    row = (
        db.query(MissionObjectiveModel)
        .filter(MissionObjectiveModel.aeroplane_id == aeroplane_id)
        .one_or_none()
    )
    old_mission_type = row.mission_type if row else None
    if row is None:
        row = MissionObjectiveModel(aeroplane_id=aeroplane_id)
        db.add(row)
    for field, value in payload.model_dump().items():
        setattr(row, field, value)
    db.flush()

    # Auto-apply preset estimates when mission_type changes (incl. first create)
    if old_mission_type != payload.mission_type:
        _apply_preset_estimates(db, aeroplane_id, payload.mission_type)

    db.refresh(row)
    return MissionObjective.model_validate(row, from_attributes=True)


def _apply_preset_estimates(db: Session, aeroplane_id: int, mission_type: str) -> None:
    """Write the preset's suggested_estimates to design_assumptions.estimate_value.

    Never touches calculated_value or active_source — those remain owned by
    assumption_compute_service / AeroBuildup. Silent no-op for unknown
    mission_type; KPI service is responsible for raising on bad ids.
    """
    from app.models.aeroplanemodel import DesignAssumptionModel

    preset = (
        db.query(MissionPresetModel).filter_by(id=mission_type).one_or_none()
    )
    if preset is None:
        return
    estimates: dict = preset.suggested_estimates
    for param_name, value in estimates.items():
        a_row = (
            db.query(DesignAssumptionModel)
            .filter_by(aeroplane_id=aeroplane_id, parameter_name=param_name)
            .one_or_none()
        )
        if a_row is None:
            a_row = DesignAssumptionModel(
                aeroplane_id=aeroplane_id, parameter_name=param_name
            )
            db.add(a_row)
        a_row.estimate_value = value
    db.flush()


def list_mission_presets(db: Session) -> list[MissionPreset]:
    """Return the seeded mission-preset library."""
    rows = db.query(MissionPresetModel).all()
    return [
        MissionPreset(
            id=row.id,
            label=row.label,
            description=row.description,
            target_polygon=row.target_polygon,
            axis_ranges={k: tuple(v) for k, v in row.axis_ranges.items()},
            suggested_estimates=row.suggested_estimates,
        )
        for row in rows
    ]


def seed_mission_presets(db: Session) -> None:
    """Idempotently insert any missing seed presets into mission_presets.

    Used both at app startup (parallels seed_default_types) and in test
    fixtures that create their schema via Base.metadata.create_all instead
    of running Alembic migrations.
    """
    from app.services.mission_preset_seed import SEED_PRESETS

    existing_ids = {row.id for row in db.query(MissionPresetModel.id).all()}
    for preset in SEED_PRESETS:
        if preset.id in existing_ids:
            continue
        db.add(
            MissionPresetModel(
                id=preset.id,
                label=preset.label,
                description=preset.description,
                target_polygon=preset.target_polygon,
                axis_ranges={k: list(v) for k, v in preset.axis_ranges.items()},
                suggested_estimates=preset.suggested_estimates.model_dump(),
            )
        )
    db.flush()
