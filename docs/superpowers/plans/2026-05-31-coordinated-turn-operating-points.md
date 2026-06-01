# Coordinated Turn Operating Points Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add correctly-computed coordinated-turn operating points (real body-rate kinematics) as the default 20/40/60° turns, plus an "add-turn" endpoint for arbitrary bank angles, with a stall-in-turn feasibility guard.

**Architecture:** A pure `turn_kinematics()` helper computes load factor + body rates from bank angle and speed. The existing AeroBuildup/Opti trim (`operating_point_generator_service`) is taught to set those body rates (today hard-coded to zero) so the trim captures `C_lr`/`C_nr`/`C_mq`. The default-target list replaces `turn_n2` with `turn_20/40/60`; a new `add_turn_operating_point` service + endpoint reuses the same trim for any bank.

**Tech Stack:** Python 3.11, FastAPI, Pydantic v2, SQLAlchemy, AeroSandbox (AeroBuildup), pytest. Issue #806, branch `feat/gh-806-turn-operating-points`.

**Reference:** Design spec `docs/superpowers/specs/2026-05-31-coordinated-turn-operating-points-design.md`.

---

### Task 1: `turn_kinematics` helper (pure module)

**Files:**
- Create: `app/services/turn_kinematics.py`
- Test: `app/tests/test_turn_kinematics.py`

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_turn_kinematics.py
"""gh-806: coordinated-turn kinematics (load factor + body rates from bank angle)."""

import math

import pytest

from app.services.turn_kinematics import TurnKinematics, turn_kinematics

G = 9.81


class TestLoadFactor:
    @pytest.mark.parametrize(
        "bank_deg, n_expected",
        [(20.0, 1.0642), (40.0, 1.3054), (60.0, 2.0)],
    )
    def test_load_factor(self, bank_deg, n_expected):
        tk = turn_kinematics(bank_deg=bank_deg, velocity=20.0)
        assert tk.n == pytest.approx(n_expected, abs=1e-3)
        assert tk.cl_factor == pytest.approx(tk.n)


class TestBodyRates:
    def test_rates_match_turn_rate(self):
        v = 25.0
        bank = 45.0
        tk = turn_kinematics(bank_deg=bank, velocity=v)
        psi_dot = G * math.tan(math.radians(bank)) / v
        assert tk.psi_dot == pytest.approx(psi_dot)
        # v1 uses theta=0 -> p=0, q=psi_dot*sin(phi), r=psi_dot*cos(phi)
        assert tk.p == pytest.approx(0.0)
        assert tk.q == pytest.approx(psi_dot * math.sin(math.radians(bank)))
        assert tk.r == pytest.approx(psi_dot * math.cos(math.radians(bank)))
        # sqrt(q^2 + r^2) == psi_dot
        assert math.hypot(tk.q, tk.r) == pytest.approx(psi_dot)

    def test_r_dominates_and_increases_with_bank(self):
        v = 20.0
        r20 = turn_kinematics(20.0, v).r
        r40 = turn_kinematics(40.0, v).r
        r60 = turn_kinematics(60.0, v).r
        assert 0 < r20 < r40 < r60

    def test_returns_dataclass(self):
        tk = turn_kinematics(30.0, 20.0)
        assert isinstance(tk, TurnKinematics)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_turn_kinematics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.services.turn_kinematics'`

- [ ] **Step 3: Write minimal implementation**

```python
# app/services/turn_kinematics.py
"""gh-806: steady coordinated level-turn kinematics.

Pure functions, no I/O. Convention: right turn (phi > 0); mirror lateral signs for
a left turn. Body rates are DIMENSIONAL (rad/s) — AeroBuildup / the AVL pipeline
non-dimensionalize internally. v1 uses theta=0 (p=0); the alpha_deg hook lets a later
refinement recompute with the solved angle of attack.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

_G = 9.81


@dataclass(frozen=True)
class TurnKinematics:
    n: float          # load factor = 1/cos(phi)
    psi_dot: float    # heading rate (rad/s)
    p: float          # body roll rate (rad/s)
    q: float          # body pitch rate (rad/s)
    r: float          # body yaw rate (rad/s)
    cl_factor: float  # CL_turn / CL_1g == n


def turn_kinematics(bank_deg: float, velocity: float, alpha_deg: float = 0.0) -> TurnKinematics:
    """Body-axis kinematics of a steady coordinated level turn at bank ``bank_deg``."""
    phi = math.radians(bank_deg)
    theta = math.radians(alpha_deg)
    cos_phi = math.cos(phi)
    n = 1.0 / cos_phi if abs(cos_phi) > 1e-9 else float("inf")
    v = max(float(velocity), 1e-6)
    psi_dot = _G * math.tan(phi) / v
    p = -psi_dot * math.sin(theta)
    q = psi_dot * math.cos(theta) * math.sin(phi)
    r = psi_dot * math.cos(theta) * cos_phi
    return TurnKinematics(n=n, psi_dot=psi_dot, p=p, q=q, r=r, cl_factor=n)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_turn_kinematics.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/turn_kinematics.py app/tests/test_turn_kinematics.py
git commit -m "feat(gh-806): turn_kinematics helper (load factor + body rates)"
```

---

### Task 2: Feed body rates into the turn trim

The trim must SEE the rates (so `C_lr`/`C_nr` enter) AND the persisted point must STORE
them. Two injection points share one helper.

**Files:**
- Modify: `app/services/operating_point_generator_service.py`
  - `_solve_trim_candidate_with_opti` OperatingPoint (currently `p=0.0, q=0.0, r=0.0`, ~line 600-608)
  - `_trim_or_estimate_point` TrimmedPoint construction (currently `p=0.0, q=0.0, r=0.0`, ~line 893-895)
- Test: `app/tests/test_turn_op_rates.py`

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_turn_op_rates.py
"""gh-806: a turn target's body rates are derived from its bank angle."""

import math

from app.services.operating_point_generator_service import _op_turn_rates


def test_no_bank_means_zero_rates():
    assert _op_turn_rates({"name": "cruise", "n_target": 1.0}, velocity=20.0) == (0.0, 0.0, 0.0)


def test_turn_target_has_nonzero_rates():
    p, q, r = _op_turn_rates({"name": "turn_40", "bank_deg": 40.0}, velocity=25.0)
    psi_dot = 9.81 * math.tan(math.radians(40.0)) / 25.0
    assert p == 0.0
    assert q > 0.0 and r > 0.0
    assert r == round(psi_dot * math.cos(math.radians(40.0)), 6)
    assert math.hypot(q, r) == round(psi_dot, 6) or abs(math.hypot(q, r) - psi_dot) < 1e-6
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_turn_op_rates.py -q`
Expected: FAIL — `ImportError: cannot import name '_op_turn_rates'`

- [ ] **Step 3: Add the helper and wire both injection points**

Add this helper near the top of `operating_point_generator_service.py` (after the imports / `TrimmedPoint`):

```python
def _op_turn_rates(target: dict, velocity: float) -> tuple[float, float, float]:
    """Body rates (p, q, r) in rad/s for a turn target, or zeros for non-turns.

    A turn target carries ``bank_deg``; kinematics come from
    :func:`app.services.turn_kinematics.turn_kinematics`.
    """
    bank_deg = target.get("bank_deg")
    if bank_deg is None:
        return (0.0, 0.0, 0.0)
    from app.services.turn_kinematics import turn_kinematics

    tk = turn_kinematics(bank_deg=float(bank_deg), velocity=float(velocity))
    return (round(tk.p, 6), round(tk.q, 6), round(tk.r, 6))
```

In `_solve_trim_candidate_with_opti`, replace the OperatingPoint rate args (the
`p=0.0, q=0.0, r=0.0` at ~line 600-608) with:

```python
        _p, _q, _r = _op_turn_rates(target, velocity_mps)
        op = asb.OperatingPoint(
            velocity=float(velocity_mps),
            alpha=alpha_deg,
            beta=float(beta_target_deg),
            p=_p,
            q=_q,
            r=_r,
            atmosphere=asb.Atmosphere(altitude=altitude_m),
        )
```

In `_trim_or_estimate_point`, replace the TrimmedPoint rate args (the
`p=0.0, q=0.0, r=0.0` at ~line 893-895) with:

```python
        p=_tp_rates[0],
        q=_tp_rates[1],
        r=_tp_rates[2],
```

and compute `_tp_rates` just above the `return TrimmedPoint(` using the FINAL velocity
(after any grid fallback):

```python
    _tp_rates = _op_turn_rates(target, velocity)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_turn_op_rates.py -q`
Expected: PASS (2 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/operating_point_generator_service.py app/tests/test_turn_op_rates.py
git commit -m "feat(gh-806): derive turn body rates from bank angle in trim + stored OP"
```

---

### Task 3: Default set — replace turn_n2 with turn_20/40/60

**Files:**
- Modify: `app/services/operating_point_generator_service.py`
  - `_build_target_definitions` (the `turn_n2` dict, ~line 442-449)
  - `_required_capabilities_for_target` (~line 506-513)
  - `_validate_target_capability` (~line 519-523)
  - `_solve_trim_candidate_with_opti` turn-only control vars & objective (the
    `target["name"] == "turn_n2"` checks at ~line 570, 574, 623)
- Modify: `app/services/trim_enrichment_service.py`
  - `ANALYSIS_GOALS` (~line 47) and `summaries` map in `generate_result_summary` (~line 365)
- Test: `app/tests/test_turn_default_targets.py`

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_turn_default_targets.py
"""gh-806: default target set has three coordinated turns at 20/40/60 deg."""

import math

from app.services.operating_point_generator_service import (
    _build_target_definitions,
    _required_capabilities_for_target,
)

_PROFILE = {
    "goals": {"cruise_speed_mps": 20.0},
    "environment": {"altitude_m": 0.0},
}
_REFS = {"vs_clean": 12.0, "vs_to": 11.0, "vs_ldg": 10.0, "provenance": "polar"}


def _targets():
    return {t["name"]: t for t in _build_target_definitions(_PROFILE, _REFS)}


def test_turn_n2_replaced_by_three_banks():
    names = _targets()
    assert "turn_n2" not in names
    for bank in (20, 40, 60):
        assert f"turn_{bank}" in names


def test_turn_targets_carry_bank_and_load_factor():
    t = _targets()["turn_40"]
    assert t["bank_deg"] == 40.0
    assert t["n_target"] == round(1.0 / math.cos(math.radians(40.0)), 4)


def test_turn_targets_need_roll_or_yaw_control():
    assert _required_capabilities_for_target("turn_20") == {"has_roll_control|has_yaw_control"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_turn_default_targets.py -q`
Expected: FAIL — `assert 'turn_20' in names` (only `turn_n2` exists)

- [ ] **Step 3: Implement the replacement**

In `_build_target_definitions`, delete the single `turn_n2` dict (~line 442-449) and
insert three turn dicts (drop the old `target_turn_n`-based n; compute per bank):

```python
        *[
            {
                "name": f"turn_{bank}",
                "config": "clean",
                "velocity": max(cruise, 1.3 * refs["vs_clean"]),
                "altitude": altitude,
                "beta_target_deg": 0.0,
                "bank_deg": float(bank),
                "n_target": round(1.0 / math.cos(math.radians(bank)), 4),
            }
            for bank in (20, 40, 60)
        ],
```

In `_required_capabilities_for_target`, change the turn check:

```python
    if target_name.startswith("turn_"):
        return {"has_roll_control|has_yaw_control"}
```

In `_validate_target_capability`, change the turn check:

```python
    if target_name.startswith("turn_"):
        if capabilities.get("has_roll_control") or capabilities.get("has_yaw_control"):
            return True, ""
        return False, "has_roll_control|has_yaw_control"
```

In `_solve_trim_candidate_with_opti`, change the three `target["name"] == "turn_n2"`
comparisons (~line 570, 574, 623) to `target["name"].startswith("turn_")`. For the
line-574 set membership, replace `target["name"] in {"turn_n2", "dutch_role_start"}`
with `(target["name"].startswith("turn_") or target["name"] == "dutch_role_start")`.

In `app/services/trim_enrichment_service.py`, in `ANALYSIS_GOALS` replace the `turn_n2`
entry with:

```python
    "turn_20": "How much aileron + rudder for a coordinated 20 deg-bank turn?",
    "turn_40": "How much aileron + rudder for a coordinated 40 deg-bank turn?",
    "turn_60": "How much aileron + rudder for a coordinated 60 deg-bank turn?",
```

and in `generate_result_summary`'s `summaries` dict replace the `turn_n2` line with:

```python
        "turn_20": f"20 deg-bank turn trim at {alpha_str}{pitch_reserve_str}",
        "turn_40": f"40 deg-bank turn trim at {alpha_str}{pitch_reserve_str}",
        "turn_60": f"60 deg-bank turn trim at {alpha_str}{pitch_reserve_str}",
```

Confirm `import math` is present at the top of `operating_point_generator_service.py`
(it is — used already).

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_turn_default_targets.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Update any existing tests that reference `turn_n2`**

Run: `grep -rln "turn_n2" app/tests/`
For each hit, update the expectation to `turn_20`/`turn_40`/`turn_60` (the contract
changed: one turn became three). Do NOT weaken assertions — adjust names/counts.

Run: `poetry run pytest app/tests/test_operating_point_generator_service.py app/tests/test_operating_point_generator_service_extended.py app/tests/test_trim_enrichment.py -q`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/operating_point_generator_service.py app/services/trim_enrichment_service.py app/tests/
git commit -m "feat(gh-806): default set turns at 20/40/60 deg with real kinematics"
```

---

### Task 4: Stall-in-turn feasibility guard

**Files:**
- Modify: `app/services/operating_point_generator_service.py` (new helper + call it in the
  generate loop after `_trim_or_estimate_point`, ~line 1026-1033)
- Test: `app/tests/test_turn_feasibility_guard.py`

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_turn_feasibility_guard.py
"""gh-806: a turn whose required CL exceeds CL_max is flagged, not silently trimmed."""

from app.schemas.aeroanalysisschema import OperatingPointStatus
from app.services.operating_point_generator_service import _apply_turn_feasibility


class _Pt:
    def __init__(self):
        self.warnings = []
        self.status = OperatingPointStatus.TRIMMED


def test_low_speed_high_bank_flagged():
    pt = _Pt()
    # vs_clean=12, n(60)=2 -> vs_turn=12*sqrt(2)=16.97; V=14 < that -> infeasible
    _apply_turn_feasibility(pt, bank_deg=60.0, velocity=14.0, vs_clean=12.0)
    assert pt.status == OperatingPointStatus.LIMIT_REACHED
    assert any("STALL_IN_TURN" in w for w in pt.warnings)


def test_adequate_speed_not_flagged():
    pt = _Pt()
    _apply_turn_feasibility(pt, bank_deg=60.0, velocity=25.0, vs_clean=12.0)
    assert pt.status == OperatingPointStatus.TRIMMED
    assert not any("STALL_IN_TURN" in w for w in pt.warnings)


def test_non_turn_noop():
    pt = _Pt()
    _apply_turn_feasibility(pt, bank_deg=None, velocity=14.0, vs_clean=12.0)
    assert pt.status == OperatingPointStatus.TRIMMED
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_turn_feasibility_guard.py -q`
Expected: FAIL — `ImportError: cannot import name '_apply_turn_feasibility'`

- [ ] **Step 3: Implement the guard**

Add to `operating_point_generator_service.py`:

```python
def _apply_turn_feasibility(point, bank_deg, velocity: float, vs_clean: float) -> None:
    """Flag a turn point as stall-limited when V < vs_clean * sqrt(n) (mutates point)."""
    if bank_deg is None or vs_clean <= 0:
        return
    from app.services.turn_kinematics import turn_kinematics

    n = turn_kinematics(bank_deg=float(bank_deg), velocity=float(velocity)).n
    v_stall_turn = vs_clean * (n ** 0.5)
    if velocity < v_stall_turn:
        msg = (
            f"STALL_IN_TURN: required CL at {bank_deg:.0f} deg bank (n={n:.2f}) exceeds "
            f"CL_max — V={velocity:.1f} < V_stall_turn={v_stall_turn:.1f} m/s"
        )
        if msg not in point.warnings:
            point.warnings.append(msg)
        point.status = OperatingPointStatus.LIMIT_REACHED
```

Call it in `generate_default_set_for_aircraft` immediately after `_trim_or_estimate_point`
returns `point` (~line 1033), before enrichment:

```python
            _apply_turn_feasibility(
                point, target.get("bank_deg"), point.velocity, refs.get("vs_clean", 0.0)
            )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_turn_feasibility_guard.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add app/services/operating_point_generator_service.py app/tests/test_turn_feasibility_guard.py
git commit -m "feat(gh-806): stall-in-turn feasibility guard"
```

---

### Task 5: Add-turn request schema + service

**Files:**
- Modify: `app/schemas/aeroanalysisschema.py` (new `AddTurnRequest`)
- Create: `app/services/add_turn_service.py`
- Test: `app/tests/test_add_turn_service.py`

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_add_turn_service.py
"""gh-806: add-turn service creates a single trimmed coordinated-turn OP."""

import math

import pytest

from app.schemas.aeroanalysisschema import AddTurnRequest


class TestAddTurnRequest:
    def test_defaults(self):
        req = AddTurnRequest(bank_angle_deg=30.0)
        assert req.bank_angle_deg == 30.0
        assert req.velocity is None and req.altitude is None and req.name is None

    @pytest.mark.parametrize("bad", [0.0, -5.0, 90.0, 95.0])
    def test_bank_bounds(self, bad):
        with pytest.raises(Exception):
            AddTurnRequest(bank_angle_deg=bad)


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_add_turn_creates_op(client_and_db):
    from app.services.add_turn_service import add_turn_operating_point
    from app.tests.conftest import seed_smoke_conventional_ttail

    _client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        op = add_turn_operating_point(
            session, aeroplane.uuid, AddTurnRequest(bank_angle_deg=30.0)
        )
        session.flush()
        assert op.name == "turn_30"
        # body rates populated from kinematics (r dominant, nonzero)
        assert op.r is not None and abs(op.r) > 0.0
        assert op.aircraft_id == aeroplane.id
    finally:
        session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_add_turn_service.py -q`
Expected: FAIL — `ImportError: cannot import name 'AddTurnRequest'`

- [ ] **Step 3: Add the schema**

In `app/schemas/aeroanalysisschema.py` add:

```python
class AddTurnRequest(BaseModel):
    """Request to add a coordinated-turn operating point at a given bank angle."""

    bank_angle_deg: float = Field(..., gt=0.0, lt=90.0, description="Turn bank angle (deg)")
    velocity: Optional[float] = Field(
        None, gt=0.0, description="TAS (m/s); default = representative turn speed"
    )
    altitude: Optional[float] = Field(None, ge=0.0, description="Altitude (m); default 0")
    name: Optional[str] = Field(None, description="OP name; default 'turn_{bank}'")
```

- [ ] **Step 4: Implement the service**

```python
# app/services/add_turn_service.py
"""gh-806: add a single coordinated-turn operating point for an aircraft."""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from app.models.analysismodels import OperatingPointModel
from app.schemas.aeroanalysisschema import AddTurnRequest

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def add_turn_operating_point(
    db: "Session", aircraft_uuid, request: AddTurnRequest
) -> OperatingPointModel:
    """Build, trim, and persist one coordinated-turn OP at ``request.bank_angle_deg``."""
    from app.converters.model_schema_converters import (
        aeroplane_model_to_aeroplane_schema_async,
        aeroplane_schema_to_asb_airplane_async,
    )
    from app.services.operating_point_generator_service import (
        _apply_turn_feasibility,
        _detect_control_capabilities,
        _estimate_reference_speeds,
        _get_aircraft_or_raise,
        _load_design_cg_x,
        _load_effective_flight_profile,
        _load_effective_mass_kg,
        _resolve_cruise_speed_with_md_fallback,
        _trim_or_estimate_point,
    )
    from app.services.trim_enrichment_service import (
        build_deflection_limits_from_schema,
        build_mix_params_from_schema,
        compute_enrichment,
    )

    aircraft = _get_aircraft_or_raise(db, aircraft_uuid)
    profile, _src = _load_effective_flight_profile(db, aircraft, None)
    cruise = _resolve_cruise_speed_with_md_fallback(aircraft, profile.get("goals", {}), _src)
    profile.setdefault("goals", {})["cruise_speed_mps"] = cruise
    refs = _estimate_reference_speeds(profile, cached_context=aircraft.assumption_computation_context)
    mass_kg = _load_effective_mass_kg(db, aircraft.id, aircraft.total_mass_kg)
    design_cg_x = _load_design_cg_x(db, aircraft.id)

    bank = float(request.bank_angle_deg)
    velocity = float(request.velocity) if request.velocity else max(cruise, 1.3 * refs["vs_clean"])
    altitude = float(request.altitude) if request.altitude is not None else 0.0
    name = request.name or f"turn_{round(bank)}"

    target = {
        "name": name,
        "config": "clean",
        "velocity": velocity,
        "altitude": altitude,
        "beta_target_deg": 0.0,
        "bank_deg": bank,
        "n_target": round(1.0 / math.cos(math.radians(bank)), 4),
    }

    plane_schema = aeroplane_model_to_aeroplane_schema_async(aircraft)
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
    asb_airplane.xyz_ref = [design_cg_x, 0.0, 0.0]
    capabilities = _detect_control_capabilities(asb_airplane)
    deflection_limits = build_deflection_limits_from_schema(plane_schema)

    point = _trim_or_estimate_point(
        asb_airplane=asb_airplane,
        aircraft=aircraft,
        target=target,
        constraints=profile.get("constraints", {}),
        capabilities=capabilities,
        effective_mass_kg=mass_kg,
    )
    _apply_turn_feasibility(point, bank, point.velocity, refs.get("vs_clean", 0.0))

    enrichment_data = None
    try:
        enrichment = compute_enrichment(
            controls=point.controls,
            limits=deflection_limits,
            trim_method=point.trim_method,
            trim_score=point.trim_score,
            trim_residuals=point.trim_residuals or {},
            op_name=point.name,
            alpha_deg=math.degrees(point.alpha_rad),
            status=point.status.value if point.status else None,
            mix_params=build_mix_params_from_schema(plane_schema),
        )
        enrichment_data = enrichment.model_dump()
    except Exception:
        enrichment_data = None

    model = OperatingPointModel(
        aircraft_id=aircraft.id,
        name=point.name,
        description=point.description,
        config=point.config,
        status=point.status.value,
        warnings=point.warnings,
        controls=point.controls,
        velocity=point.velocity,
        alpha=point.alpha_rad,
        beta=point.beta_rad,
        p=point.p,
        q=point.q,
        r=point.r,
        xyz_ref=[design_cg_x, 0.0, 0.0],
        altitude=point.altitude,
        trim_enrichment=enrichment_data,
    )
    db.add(model)
    db.flush()
    db.refresh(model)
    return model
```

> The imported helpers (`_get_aircraft_or_raise`, `_load_effective_flight_profile`,
> `_resolve_cruise_speed_with_md_fallback`, `_estimate_reference_speeds`,
> `_load_effective_mass_kg`, `_load_design_cg_x`, `_detect_control_capabilities`,
> `_trim_or_estimate_point`, `_apply_turn_feasibility`) all exist in
> `operating_point_generator_service` (verified against the source).

- [ ] **Step 5: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_add_turn_service.py -q`
Expected: PASS (unit + integration; the integration test needs AeroSandbox)

- [ ] **Step 6: Commit**

```bash
git add app/schemas/aeroanalysisschema.py app/services/add_turn_service.py app/tests/test_add_turn_service.py
git commit -m "feat(gh-806): add-turn request schema + service"
```

---

### Task 6: Add-turn endpoint

**Files:**
- Modify: `app/api/v2/endpoints/operating_points.py` (new POST route, model after the
  `aerobuildup_trim_operating_point` route ~line 178-205)
- Test: `app/tests/test_add_turn_endpoint.py`

- [ ] **Step 1: Write the failing test**

```python
# app/tests/test_add_turn_endpoint.py
"""gh-806: POST add-turn endpoint creates and returns a turn OP."""

import pytest


@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_add_turn_endpoint(client_and_db):
    from app.tests.conftest import seed_smoke_conventional_ttail

    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        uuid = aeroplane.uuid
    finally:
        session.close()

    resp = client.post(
        f"/aeroplanes/{uuid}/operating-points/add-turn",
        json={"bank_angle_deg": 30.0},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["name"] == "turn_30"


def test_add_turn_rejects_bad_bank(client_and_db):
    from app.tests.conftest import seed_smoke_conventional_ttail

    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        uuid = seed_smoke_conventional_ttail(session).uuid
    finally:
        session.close()
    resp = client.post(f"/aeroplanes/{uuid}/operating-points/add-turn", json={"bank_angle_deg": 95.0})
    assert resp.status_code == 422
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_add_turn_endpoint.py -q`
Expected: FAIL — 404 (route not registered)

- [ ] **Step 3: Implement the endpoint**

Read the existing `aerobuildup_trim_operating_point` route (~line 178-205) for the exact
router decorator style, dependency injection, and the `_raise_http_from_domain` error
wrapper, then add an analogous route:

```python
@router.post(
    "/aeroplanes/{aeroplane_uuid}/operating-points/add-turn",
    response_model=StoredOperatingPointRead,
    operation_id="add_turn_operating_point",
)
def add_turn_operating_point_endpoint(
    aeroplane_uuid: UUID4,
    request: AddTurnRequest,
    db: Annotated[Session, Depends(get_db)],
):
    from app.services.add_turn_service import add_turn_operating_point

    try:
        return add_turn_operating_point(db, aeroplane_uuid, request)
    except ServiceException as exc:
        _raise_http_from_domain(exc)
```

Add the imports at the top of `operating_points.py`: `from app.schemas.aeroanalysisschema
import AddTurnRequest` (extend the existing import line if one already pulls from that
module), and ensure `StoredOperatingPointRead`, `ServiceException`, `_raise_http_from_domain`,
`UUID4`, `Annotated`, `Session`, `Depends`, `get_db` are already imported (they are — used
by the neighboring routes).

- [ ] **Step 4: Run tests to verify they pass**

Run: `poetry run pytest app/tests/test_add_turn_endpoint.py -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/v2/endpoints/operating_points.py app/tests/test_add_turn_endpoint.py
git commit -m "feat(gh-806): POST add-turn endpoint"
```

---

### Task 7: Slow integration — turns trim across configs

**Files:**
- Test: `app/tests/test_turn_ops_integration.py`

- [ ] **Step 1: Write the test**

```python
# app/tests/test_turn_ops_integration.py
"""gh-806: default generation yields three trimmed turns with real rates."""

import pytest


@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_default_set_has_three_turns_with_rates(client_and_db):
    from app.services.operating_point_generator_service import generate_default_set_for_aircraft
    from app.tests.conftest import seed_smoke_conventional_ttail

    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        result = generate_default_set_for_aircraft(session, aeroplane.uuid, replace_existing=True)
    finally:
        session.close()

    names = {op.name for op in result.operating_points}
    assert {"turn_20", "turn_40", "turn_60"} <= names
    turns = [op for op in result.operating_points if op.name in {"turn_20", "turn_40", "turn_60"}]
    # nonzero yaw rate proves real turn kinematics (not the old p=q=r=0 model)
    assert all(abs(op.r) > 0.0 for op in turns)
```

- [ ] **Step 2: Run it**

Run: `poetry run pytest app/tests/test_turn_ops_integration.py -m slow -q -p no:randomly`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add app/tests/test_turn_ops_integration.py
git commit -m "test(gh-806): slow integration — default turns trim with real rates"
```

---

### Final verification

- [ ] **Run the fast suite** (regression): `poetry run pytest -q -m "not slow"` — expect green.
- [ ] **Lint:** `poetry run ruff check app/ && poetry run ruff format --check app/`
- [ ] **Push + PR:** `git push -u github feat/gh-806-turn-operating-points` then
  `gh pr create --base main --title "feat(gh-806): coordinated turn operating points" --body "Closes #806"`.
