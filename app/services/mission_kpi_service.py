"""Aggregate the seven Mission compliance KPIs (gh-547).

All values come from cached ``assumption_computation_context`` plus the
persisted ``MissionObjective`` and the static list of ``MissionPreset``
rows. **No** AeroBuildup re-run — this service is closed-form on top of
existing data.

Public surface:

- :func:`compute_mission_kpis` — bundle the Ist + Soll polygons for the
  radar chart (added in Task 2.2).

The private ``_kpi_*`` calculators are unit-tested individually so the
aggregator stays a thin orchestration layer.
"""

from __future__ import annotations

import hashlib
import json
import logging
import math
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.core.exceptions import ServiceException
from app.models.aeroplanemodel import AeroplaneModel
from app.schemas.mission_kpi import (
    AxisName,
    MissionAxisKpi,
    MissionKpiSet,
    MissionTargetPolygon,
)

# Module-level import so the symbol exists for both runtime calls and
# `unittest.mock.patch("app.services.mission_kpi_service.compute_field_lengths_for_aeroplane", ...)`.
# Falls back to None on platforms where the field-length service can't be
# loaded (e.g. linux/aarch64 without aerosandbox); _compute_field_length_score
# surfaces that as a warning rather than swallowing it.
try:
    from app.services.field_length_service import (
        compute_field_lengths_for_aeroplane,
    )
except ImportError:  # pragma: no cover — platform-dependent
    compute_field_lengths_for_aeroplane = None  # type: ignore[assignment]


# ----- Helpers --------------------------------------------------------------


def _normalise_score(value: float, lo: float, hi: float) -> float:
    """Map ``value`` to ``0..1`` across ``[lo, hi]``; clip outside.

    Degenerate ranges (``hi <= lo``) collapse to ``0.0`` because there
    is no defensible interpretation of "where in the range" the value
    sits.
    """
    if hi <= lo:
        return 0.0
    score = (value - lo) / (hi - lo)
    return max(0.0, min(1.0, score))


def _missing(
    axis: AxisName,
    lo: float,
    hi: float,
    formula: str,
    warning: str | None = None,
) -> MissionAxisKpi:
    """Build a ``provenance="missing"`` axis (renders as polygon gap).

    When ``warning`` is provided, the user-facing AxisDrawer surfaces it
    as the cause for the axis being unavailable (e.g. *"set t_static_N"*).
    """
    return MissionAxisKpi(
        axis=axis,
        value=None,
        unit=None,
        score_0_1=None,
        range_min=lo,
        range_max=hi,
        provenance="missing",
        formula=formula,
        warning=warning,
    )


def _ctx_get(ctx: dict[str, Any], key: str) -> float | None:
    """Read a strictly-positive numeric value from the context dict.

    Returns ``None`` for missing keys, non-numerics, and non-positive
    values (zero or negative inputs are nonsensical for the physical
    quantities this service consumes).
    """
    v = ctx.get(key)
    if isinstance(v, (int, float)) and v > 0:
        return float(v)
    return None


# ----- Per-axis calculators -------------------------------------------------


def _kpi_stall_safety(ctx: dict[str, Any], range_min: float, range_max: float) -> MissionAxisKpi:
    """V_cruise / V_s1 — higher is safer."""
    formula = "V_cruise / V_s1"
    v_cruise = _ctx_get(ctx, "v_cruise_mps")
    v_s1 = _ctx_get(ctx, "v_s1_mps")
    if v_cruise is None or v_s1 is None:
        return _missing("stall_safety", range_min, range_max, formula)
    value = v_cruise / v_s1
    return MissionAxisKpi(
        axis="stall_safety",
        value=value,
        unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _resolve_polar_inputs(
    ctx: dict[str, Any],
) -> tuple[float | None, float | None, float | None, float | None]:
    """gh-681: resolve (ld_max_empirical, cd0, e_oswald, ar) for the clean polar.

    Provenance chain that survives parabolic-fit rejection:
    - ``ld_max_empirical``: ``polar_by_config.clean.ld_max`` (gh-636 empirical
      max(CL/CD) from the AeroBuildup sweep) if positive.
    - ``cd0`` / ``e``: prefer ``polar_by_config.clean`` (post-fit values),
      then fall back to top-level ``ctx['cd0']`` (always-written stability-run
      cd0) and ``ctx['e_oswald']`` (gh-636 AB-Trefftz, populated independently
      of the parabolic fit).
    - ``ar``: ``ctx['aspect_ratio']``.
    """
    polar = ctx.get("polar_by_config", {}).get("clean") if ctx.get("polar_by_config") else None
    ar = ctx.get("aspect_ratio")
    if ar is None or ar <= 0:
        return None, None, None, None

    ld_emp = polar.get("ld_max") if polar else None
    if not isinstance(ld_emp, (int, float)) or ld_emp <= 0:
        ld_emp = None

    cd0 = polar.get("cd0") if polar else None
    if cd0 is None or cd0 <= 0:
        cd0 = ctx.get("cd0")
        if cd0 is None or cd0 <= 0:
            cd0 = None

    e = polar.get("e_oswald") if polar else None
    if e is None or e <= 0:
        e = ctx.get("e_oswald")
        if e is None or e <= 0:
            e = None

    return ld_emp, cd0, e, float(ar)


def _kpi_glide(ctx: dict[str, Any], range_min: float, range_max: float) -> MissionAxisKpi:
    """Maximum lift-to-drag ratio from the clean polar.

    gh-681: prefer empirical (L/D)max from the sweep; if absent, use the
    parabolic-polar formula with cd0/e_oswald via the provenance chain
    that survives fit rejection (see ``_resolve_polar_inputs``).
    """
    formula = "(L/D)_max = 0.5 · √(π · e · AR / C_D0)"
    ld_emp, cd0, e, ar = _resolve_polar_inputs(ctx)
    if ar is None:
        return _missing("glide", range_min, range_max, formula)
    if ld_emp is not None:
        value = float(ld_emp)
    elif cd0 is not None and e is not None:
        value = 0.5 * math.sqrt(math.pi * e * ar / cd0)
    else:
        return _missing("glide", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="glide",
        value=value,
        unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_climb_energy(ctx: dict[str, Any], range_min: float, range_max: float) -> MissionAxisKpi:
    """Climb-energy figure ``(C_L^1.5 / C_D)_max`` — relevant for thermalling and ROC.

    gh-681: uses the same provenance chain as ``_kpi_glide`` for cd0 / e_oswald.
    No empirical equivalent for climb-energy yet (only ld_max is on the polar);
    formula is the only path.
    """
    formula = "(C_L^1.5 / C_D)_max = (3·π·e·AR)^0.75 / (4 · C_D0^0.25)"
    _ld_emp_unused, cd0, e, ar = _resolve_polar_inputs(ctx)
    if ar is None or cd0 is None or e is None:
        return _missing("climb", range_min, range_max, formula)
    # Closed-form maximum of CL^1.5/CD for the parabolic polar
    # CD = CD0 + CL^2/(π·e·AR). Setting d(CL^1.5/CD)/dCL = 0 gives
    # 1.5·CD = 2·k·CL^2 with k = 1/(π·e·AR), so CL*^2 = 3·π·e·AR·CD0
    # and CD* = 4·CD0. Therefore:
    #   (CL^1.5 / CD)_max = (3·π·e·AR)^0.75 / (4 · CD0^0.25)
    value = (3.0 * math.pi * e * ar) ** 0.75 / (4.0 * cd0**0.25)
    return MissionAxisKpi(
        axis="climb",
        value=value,
        unit="-",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_cruise(ctx: dict[str, Any], range_min: float, range_max: float) -> MissionAxisKpi:
    """Cruise speed straight from ``ComputationContext``."""
    formula = "V_cruise (from ComputationContext)"
    v = _ctx_get(ctx, "v_cruise_mps")
    if v is None:
        return _missing("cruise", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="cruise",
        value=v,
        unit="m/s",
        score_0_1=_normalise_score(v, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_maneuver(ctx: dict[str, Any], range_min: float, range_max: float) -> MissionAxisKpi:
    """Maximum positive load factor from the V-n diagram."""
    formula = "n_max from V-n diagram (load factor)"
    n_max = ctx.get("flight_envelope_n_max")
    if not isinstance(n_max, (int, float)) or n_max <= 0:
        return _missing("maneuver", range_min, range_max, formula)
    return MissionAxisKpi(
        axis="maneuver",
        value=float(n_max),
        unit="g",
        score_0_1=_normalise_score(float(n_max), range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


def _kpi_wing_loading(
    ctx: dict[str, Any],
    mass_kg: float | None,
    range_min: float,
    range_max: float,
) -> MissionAxisKpi:
    """Wing loading ``W/S = m·g / S_ref``."""
    formula = "W/S = m·g / S_ref"
    s_ref = _ctx_get(ctx, "s_ref_m2")
    if mass_kg is None or mass_kg <= 0 or s_ref is None:
        return _missing("wing_loading", range_min, range_max, formula)
    value = mass_kg * 9.81 / s_ref
    return MissionAxisKpi(
        axis="wing_loading",
        value=value,
        unit="N/m²",
        score_0_1=_normalise_score(value, range_min, range_max),
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


# ----- Field Friendliness (delegates to field_length_service) ---------------


def _compute_field_length_score(
    aeroplane: AeroplaneModel,
    target_field_length_m: float,
    db: Session | None = None,
) -> tuple[float | None, float | None, str | None]:
    """Return ``(effective_field_length_m, score_0_1, warning)``.

    The score is ``target_field / effective_field`` clipped to ``[0, 1]``:
    a shorter effective field is better. The ``warning`` carries the
    user-facing reason when the score can't be computed (e.g. *"Set
    t_static_N…"*) so the AxisDrawer can surface it — pre-#562 this was
    only visible via the now-removed FieldLengthsPanel.

    Unexpected exceptions (anything other than ``ServiceException``)
    bubble up to the endpoint's logging handler — they indicate real
    bugs, not user-actionable conditions.

    Passing ``db`` is strongly preferred — it keeps the MissionObjective
    lookup in the same session as the caller and is required by tests
    that use a transient SQLite database.
    """
    if compute_field_lengths_for_aeroplane is None:
        return None, None, "Field-length service unavailable on this platform"

    try:
        result = compute_field_lengths_for_aeroplane(aeroplane, db=db)
    except ImportError as exc:
        # Surfaces if the service does a lazy aerosandbox import at call time.
        logger.warning("field_length_service ImportError at call site: %s", exc)
        return None, None, "Field-length service unavailable on this platform"
    except ServiceException as exc:
        # User-actionable: missing t_static_N, missing s_ref_m2, etc.
        logger.info("field_friendliness KPI unavailable: %s", exc.message)
        return None, None, exc.message

    eff = max(result.get("s_to_50ft_m", 0), result.get("s_ldg_50ft_m", 0))
    if eff <= 0:
        return None, None, "Computed effective field length is zero"
    score = max(0.0, min(1.0, target_field_length_m / eff))
    return float(eff), float(score), None


def _kpi_field_friendliness(
    aeroplane: AeroplaneModel,
    target_field_length_m: float,
    range_min: float,
    range_max: float,
    db: Session | None = None,
) -> MissionAxisKpi:
    """Field friendliness — composite take-off + landing field length score."""
    formula = "max(s_TO_50ft, s_LDG_50ft); score = target / effective"
    eff, score, warning = _compute_field_length_score(aeroplane, target_field_length_m, db=db)
    if eff is None or score is None:
        return _missing("field_friendliness", range_min, range_max, formula, warning=warning)
    return MissionAxisKpi(
        axis="field_friendliness",
        value=eff,
        unit="m",
        score_0_1=score,
        range_min=range_min,
        range_max=range_max,
        provenance="computed",
        formula=formula,
    )


# ----- Aggregator -----------------------------------------------------------


def _hash_context(ctx: dict[str, Any]) -> str:
    """Stable 64-char SHA-256 of the context dict for cache validation."""
    blob = json.dumps(ctx, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(blob).hexdigest()


def compute_mission_kpis(
    db: Session,
    aeroplane_id: int,
    active_mission_ids: list[str],
) -> MissionKpiSet:
    """Bundle Ist + multi-mission Soll polygons for the spider chart.

    The first id in ``active_mission_ids`` is the *primary* (active)
    mission — its ``axis_ranges`` drive the Ist normalisation and its
    id is echoed back as ``active_mission_id``. Additional ids
    contribute extra ``MissionTargetPolygon`` overlays only.

    Unknown mission ids are silently dropped. An empty list defaults
    to ``[objective.mission_type]``.
    """
    # Local import to avoid a circular dependency on app.services.* at module load.
    from app.services.mission_objective_service import (
        get_mission_objective,
        list_mission_presets,
    )

    aeroplane = db.query(AeroplaneModel).filter_by(id=aeroplane_id).one()
    ctx: dict[str, Any] = aeroplane.assumption_computation_context or {}
    objective = get_mission_objective(db, aeroplane_id)
    presets = {p.id: p for p in list_mission_presets(db)}

    if not active_mission_ids:
        active_mission_ids = [objective.mission_type]

    # Pick the primary mission preset for Ist axis ranges; fall back to
    # the "trainer" preset when the active id is unknown so we always
    # have *some* ranges to normalise against.
    primary_preset = presets.get(active_mission_ids[0])
    if primary_preset is None:
        primary_preset = presets.get("trainer")
    if primary_preset is None:
        # No presets at all — a missing Alembic seed or empty table. Fail
        # loudly with a 500 instead of returning a degenerate empty radar
        # payload that clients can't render or interpret. Don't log the
        # user-controlled mission id directly (S5145 log-injection); the
        # client gets the value back via the RuntimeError message.
        logger.error(
            "mission_presets table is empty or missing the requested mission id "
            "and 'trainer' fallback — cannot compute KPIs. Ensure Alembic "
            "migration + seed have run."
        )
        raise RuntimeError(
            f"No mission preset found for '{active_mission_ids[0]}' and no "
            "'trainer' fallback. Verify mission_presets table is seeded."
        )
    rng = primary_preset.axis_ranges

    # Mass for W/S: first try cached context, then the AeroplaneModel column.
    mass = ctx.get("mass_kg")
    if not isinstance(mass, (int, float)) or mass <= 0:
        mass = aeroplane.total_mass_kg if aeroplane.total_mass_kg else None

    ist: dict[AxisName, MissionAxisKpi] = {
        "stall_safety": _kpi_stall_safety(ctx, *rng["stall_safety"]),
        "glide": _kpi_glide(ctx, *rng["glide"]),
        "climb": _kpi_climb_energy(ctx, *rng["climb"]),
        "cruise": _kpi_cruise(ctx, *rng["cruise"]),
        "maneuver": _kpi_maneuver(ctx, *rng["maneuver"]),
        "wing_loading": _kpi_wing_loading(ctx, mass, *rng["wing_loading"]),
        "field_friendliness": _kpi_field_friendliness(
            aeroplane,
            objective.target_field_length_m,
            *rng["field_friendliness"],
            db=db,
        ),
    }

    # Build target polygons (Soll for each active mission preset)
    targets: list[MissionTargetPolygon] = []
    for mid in active_mission_ids:
        preset = presets.get(mid)
        if preset is None:
            continue
        targets.append(
            MissionTargetPolygon(
                mission_id=preset.id,
                label=preset.label,
                scores_0_1=preset.target_polygon,
            )
        )

    return MissionKpiSet(
        aeroplane_uuid=str(aeroplane.uuid),
        ist_polygon=ist,
        target_polygons=targets,
        active_mission_id=active_mission_ids[0],
        computed_at=datetime.now(timezone.utc).isoformat(),
        context_hash=_hash_context(ctx),
    )
