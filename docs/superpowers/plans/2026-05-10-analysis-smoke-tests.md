# Analysis Smoke Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add pytest-parametrised smoke tests that exercise every analysis endpoint against 7 aircraft configurations covering all control-surface role combinations — 10 tests × 7 configs = 70 test cases.

**Architecture:** Extend `app/tests/conftest.py` with 7 factory functions (one per aircraft config), each using the existing `_add_xsec` / `make_wing` helpers with Peter's Glider geometry. A new `app/tests/test_analysis_smoke.py` file contains a parametrised `smoke_plane` fixture and 10 test functions. Assertions are minimal (status 200 + top-level keys) — the goal is crash detection, not correctness.

**Tech Stack:** pytest, FastAPI TestClient, SQLAlchemy in-memory SQLite, AeroSandbox, AVL

**Closes:** #468

---

## File Structure

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `app/tests/conftest.py` | Add 7 `seed_smoke_*` factory functions |
| Create | `app/tests/test_analysis_smoke.py` | `SmokeConfig` dataclass, `smoke_plane` fixture, 10 test functions |

---

### Task 1: Add 7 smoke-plane factory functions to conftest.py

**Files:**
- Modify: `app/tests/conftest.py` (append after `seed_design_assumptions`)

All factories follow the same pattern as the existing `seed_integration_aeroplane`:
- Create `AeroplaneModel` directly (not via `make_aeroplane`) with `total_mass_kg=1.5`, `xyz_ref=[0.15, 0.0, 0.0]`
- Build wings using `make_wing` + `_add_xsec`
- All TEDs: `rel_chord_root=0.75`, `rel_chord_tip=0.75`, `±25°` deflection, `deflection_deg=0.0`
- Main wing uses `sd7037` airfoil, tail surfaces use `naca0010`
- Return the `AeroplaneModel` (caller seeds design assumptions separately)

#### Geometry reference (Peter's Glider)

**Main wing** (symmetric, 3 sections):
| Section | sort_index | xyz_le | chord | twist | TED varies by config |
|---------|-----------|--------|-------|-------|---------------------|
| root | 0 | `[0, 0, 0]` | 0.18 | 2.0 | config-dependent |
| mid | 1 | `[0.01, 0.5, 0]` | 0.16 | 0.0 | config-dependent |
| tip | 2 | `[0.08, 1.0, 0.1]` | 0.08 | -2.0 | never |

**Horizontal tail** (symmetric, NACA 0010, 2 sections):
| Section | sort_index | xyz_le | chord | twist |
|---------|-----------|--------|-------|-------|
| root | 0 | `[0.6, 0, 0.06]` (T-tail) or `[0.6, 0, 0.0]` (cross) | 0.10 | -10.0 |
| tip | 1 | `[0.62, 0.17, 0.06]` or `[0.62, 0.17, 0.0]` | 0.08 | -10.0 |

**Vertical tail** (non-symmetric, NACA 0010, 2 sections):
| Section | sort_index | xyz_le | chord | twist |
|---------|-----------|--------|-------|-------|
| root | 0 | `[0.6, 0, 0.07]` | 0.10 | 0.0 |
| tip | 1 | `[0.64, 0, 0.22]` | 0.06 | 0.0 |

**V-tail** (symmetric, NACA 0010, dihedral via z-offset):
| Section | sort_index | xyz_le | chord | twist |
|---------|-----------|--------|-------|-------|
| root | 0 | `[0.6, 0, 0.06]` | 0.12 | -10.0 |
| tip | 1 | `[0.62, 0.17, 0.12]` | 0.08 | -10.0 |

- [ ] **Step 1: Write a minimal smoke test that calls the first factory**

Create `app/tests/test_analysis_smoke.py` with just enough to verify the factory:

```python
"""Smoke tests — verify analysis endpoints don't crash across aircraft configs."""

from __future__ import annotations

import pytest

from app.tests.conftest import seed_design_assumptions, seed_smoke_conventional_ttail


@pytest.mark.integration
def test_smoke_factory_creates_plane(client_and_db):
    """Temporary bootstrap test — proves the first factory works."""
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = seed_smoke_conventional_ttail(session)
        seed_design_assumptions(session, aeroplane.id)
        assert aeroplane.name == "smoke-conventional-ttail"
        assert aeroplane.total_mass_kg == 1.5
        assert len(aeroplane.wings) == 3  # main + htail + vtail
    finally:
        session.close()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest app/tests/test_analysis_smoke.py::test_smoke_factory_creates_plane -v`
Expected: FAIL — `seed_smoke_conventional_ttail` not found in conftest.

- [ ] **Step 3: Implement `seed_smoke_conventional_ttail` in conftest.py**

Append to `app/tests/conftest.py` after `seed_design_assumptions`:

```python
# --------------------------------------------------------------------------- #
# Smoke-test plane factories (gh-468)
#
# 7 aircraft configurations covering all control-surface role combinations.
# Geometry: Peter's Glider (SD7037 main wing, NACA 0010 tail surfaces).
# --------------------------------------------------------------------------- #


def _smoke_main_wing(
    session: Session,
    aeroplane_id: int,
    *,
    sec0_ted: dict | None = None,
    sec1_ted: dict | None = None,
) -> WingModel:
    """Build the standard 3-section main wing used by all smoke configs."""
    wing = make_wing(session, aeroplane_id=aeroplane_id, name="main_wing", symmetric=True)
    _add_xsec(
        session, wing,
        xyz_le=[0, 0, 0], chord=0.18, twist=2.0, airfoil="sd7037", sort_index=0,
        **({"x_sec_type": "segment", "ted_kwargs": sec0_ted} if sec0_ted else {}),
    )
    _add_xsec(
        session, wing,
        xyz_le=[0.01, 0.5, 0], chord=0.16, twist=0.0, airfoil="sd7037", sort_index=1,
        **({"x_sec_type": "segment", "ted_kwargs": sec1_ted} if sec1_ted else {}),
    )
    _add_xsec(
        session, wing,
        xyz_le=[0.08, 1.0, 0.1], chord=0.08, twist=-2.0, airfoil="sd7037", sort_index=2,
    )
    return wing


def _smoke_htail(
    session: Session,
    aeroplane_id: int,
    *,
    z_offset: float = 0.06,
    ted_kwargs: dict | None = None,
) -> WingModel:
    """Build a horizontal tail (symmetric, NACA 0010)."""
    htail = make_wing(session, aeroplane_id=aeroplane_id, name="horizontal_tail", symmetric=True)
    _add_xsec(
        session, htail,
        xyz_le=[0.6, 0, z_offset], chord=0.10, twist=-10.0, airfoil="naca0010", sort_index=0,
        **({"x_sec_type": "segment", "ted_kwargs": ted_kwargs} if ted_kwargs else {}),
    )
    _add_xsec(
        session, htail,
        xyz_le=[0.62, 0.17, z_offset], chord=0.08, twist=-10.0, airfoil="naca0010", sort_index=1,
    )
    return htail


def _smoke_vtail(
    session: Session,
    aeroplane_id: int,
    *,
    ted_kwargs: dict | None = None,
) -> WingModel:
    """Build a vertical tail (non-symmetric, NACA 0010)."""
    vtail = make_wing(session, aeroplane_id=aeroplane_id, name="vertical_tail", symmetric=False)
    _add_xsec(
        session, vtail,
        xyz_le=[0.6, 0, 0.07], chord=0.10, twist=0.0, airfoil="naca0010", sort_index=0,
        **({"x_sec_type": "segment", "ted_kwargs": ted_kwargs} if ted_kwargs else {}),
    )
    _add_xsec(
        session, vtail,
        xyz_le=[0.64, 0, 0.22], chord=0.06, twist=0.0, airfoil="naca0010", sort_index=1,
    )
    return vtail


_AILERON = {
    "name": "Aileron", "role": "aileron",
    "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
    "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
    "deflection_deg": 0.0, "symmetric": False,
}
_ELEVATOR = {
    "name": "Elevator", "role": "elevator",
    "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
    "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
    "deflection_deg": 0.0, "symmetric": True,
}
_RUDDER = {
    "name": "Rudder", "role": "rudder",
    "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
    "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
    "deflection_deg": 0.0, "symmetric": True,
}


def _smoke_aeroplane(session: Session, name: str) -> AeroplaneModel:
    """Create the base AeroplaneModel shared by all smoke configs."""
    aeroplane = AeroplaneModel(
        name=name,
        uuid=uuid.uuid4(),
        total_mass_kg=1.5,
        xyz_ref=[0.15, 0.0, 0.0],
    )
    session.add(aeroplane)
    session.flush()
    return aeroplane


def seed_smoke_conventional_ttail(session: Session) -> AeroplaneModel:
    """Config 1: aileron + T-tail with elevator + rudder."""
    aeroplane = _smoke_aeroplane(session, "smoke-conventional-ttail")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest app/tests/test_analysis_smoke.py::test_smoke_factory_creates_plane -v`
Expected: PASS

- [ ] **Step 5: Implement remaining 6 factory functions**

Append to `app/tests/conftest.py` after `seed_smoke_conventional_ttail`:

```python
def seed_smoke_vtail_ruddervator(session: Session) -> AeroplaneModel:
    """Config 2: aileron + V-tail with ruddervator ×2."""
    aeroplane = _smoke_aeroplane(session, "smoke-vtail-ruddervator")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)
    vtail = make_wing(
        session, aeroplane_id=aeroplane.id, name="v_tail", symmetric=True,
    )
    _add_xsec(
        session, vtail,
        xyz_le=[0.6, 0, 0.06], chord=0.12, twist=-10.0, airfoil="naca0010",
        sort_index=0, x_sec_type="segment",
        ted_kwargs={
            "name": "Ruddervator", "role": "ruddervator",
            "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
            "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
            "deflection_deg": 0.0, "symmetric": True,
        },
    )
    _add_xsec(
        session, vtail,
        xyz_le=[0.62, 0.17, 0.12], chord=0.08, twist=-10.0,
        airfoil="naca0010", sort_index=1,
    )
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_conventional_cross(session: Session) -> AeroplaneModel:
    """Config 3: aileron + base-mounted htail (z=0.0) + vtail with elevator + rudder."""
    aeroplane = _smoke_aeroplane(session, "smoke-conventional-cross")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)
    _smoke_htail(session, aeroplane.id, z_offset=0.0, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_flying_wing(session: Session) -> AeroplaneModel:
    """Config 4: elevon on sec 0 + sec 1, no tail surfaces."""
    aeroplane = _smoke_aeroplane(session, "smoke-flying-wing")
    elevon_0 = {
        "name": "Elevon_0", "role": "elevon",
        "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
        "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
        "deflection_deg": 0.0, "symmetric": False,
    }
    elevon_1 = {
        "name": "Elevon_1", "role": "elevon",
        "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
        "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
        "deflection_deg": 0.0, "symmetric": False,
    }
    _smoke_main_wing(session, aeroplane.id, sec0_ted=elevon_0, sec1_ted=elevon_1)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_flaperon_ttail(session: Session) -> AeroplaneModel:
    """Config 5: flaperon on sec 0 + sec 1, T-tail with elevator + rudder."""
    aeroplane = _smoke_aeroplane(session, "smoke-flaperon-ttail")
    flaperon_0 = {
        "name": "Flaperon_0", "role": "flaperon",
        "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
        "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
        "deflection_deg": 0.0, "symmetric": False,
    }
    flaperon_1 = {
        "name": "Flaperon_1", "role": "flaperon",
        "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
        "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
        "deflection_deg": 0.0, "symmetric": False,
    }
    _smoke_main_wing(session, aeroplane.id, sec0_ted=flaperon_0, sec1_ted=flaperon_1)
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_flap_aileron_ttail(session: Session) -> AeroplaneModel:
    """Config 6: flap on sec 0 + aileron on sec 1, T-tail with elevator + rudder."""
    aeroplane = _smoke_aeroplane(session, "smoke-flap-aileron-ttail")
    flap = {
        "name": "Flap", "role": "flap",
        "rel_chord_root": 0.75, "rel_chord_tip": 0.75,
        "positive_deflection_deg": 25.0, "negative_deflection_deg": 25.0,
        "deflection_deg": 0.0, "symmetric": True,
    }
    _smoke_main_wing(session, aeroplane.id, sec0_ted=flap, sec1_ted=_AILERON)
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=_ELEVATOR)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane


def seed_smoke_stabilator_ttail(session: Session) -> AeroplaneModel:
    """Config 7: aileron + all-moving htail (no TED) + vtail with rudder."""
    aeroplane = _smoke_aeroplane(session, "smoke-stabilator-ttail")
    _smoke_main_wing(session, aeroplane.id, sec1_ted=_AILERON)
    _smoke_htail(session, aeroplane.id, z_offset=0.06, ted_kwargs=None)
    _smoke_vtail(session, aeroplane.id, ted_kwargs=_RUDDER)
    session.commit()
    session.refresh(aeroplane)
    return aeroplane
```

- [ ] **Step 6: Update the bootstrap test to verify all 7 factories**

Replace the bootstrap test in `test_analysis_smoke.py`:

```python
"""Smoke tests — verify analysis endpoints don't crash across aircraft configs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import pytest
from sqlalchemy.orm import Session

from app.models.aeroplanemodel import AeroplaneModel
from app.tests.conftest import (
    seed_design_assumptions,
    seed_smoke_conventional_cross,
    seed_smoke_conventional_ttail,
    seed_smoke_flap_aileron_ttail,
    seed_smoke_flaperon_ttail,
    seed_smoke_flying_wing,
    seed_smoke_stabilator_ttail,
    seed_smoke_vtail_ruddervator,
)


@dataclass(frozen=True)
class SmokeConfig:
    name: str
    factory: Callable[[Session], AeroplaneModel]
    trim_ted: str


SMOKE_CONFIGS = [
    SmokeConfig("conventional-ttail", seed_smoke_conventional_ttail, "Elevator"),
    SmokeConfig("vtail-ruddervator", seed_smoke_vtail_ruddervator, "Ruddervator"),
    SmokeConfig("conventional-cross", seed_smoke_conventional_cross, "Elevator"),
    SmokeConfig("flying-wing", seed_smoke_flying_wing, "Elevon_0"),
    SmokeConfig("flaperon-ttail", seed_smoke_flaperon_ttail, "Elevator"),
    SmokeConfig("flap-aileron-ttail", seed_smoke_flap_aileron_ttail, "Elevator"),
    SmokeConfig("stabilator-ttail", seed_smoke_stabilator_ttail, "Aileron"),
]


@pytest.fixture(params=SMOKE_CONFIGS, ids=lambda c: c.name)
def smoke_plane(request, client_and_db):
    """Yield (client, aeroplane, config) for each aircraft configuration."""
    config: SmokeConfig = request.param
    client, SessionLocal = client_and_db
    session = SessionLocal()
    try:
        aeroplane = config.factory(session)
        seed_design_assumptions(session, aeroplane.id)
    finally:
        session.close()
    return client, aeroplane, config


@pytest.mark.integration
def test_smoke_factories(smoke_plane):
    """All 7 factories produce a seeded aeroplane with wings and design assumptions."""
    _client, aeroplane, config = smoke_plane
    assert aeroplane.name == f"smoke-{config.name}"
    assert aeroplane.total_mass_kg == 1.5
    assert len(aeroplane.wings) >= 1
```

- [ ] **Step 7: Run factory verification across all 7 configs**

Run: `poetry run pytest app/tests/test_analysis_smoke.py::test_smoke_factories -v`
Expected: 7 PASSED (one per config)

- [ ] **Step 8: Delete the bootstrap test and commit**

Remove `test_smoke_factories` from the test file (it served its purpose — the real endpoint tests in Task 2 will exercise the factories).

```bash
git add app/tests/conftest.py app/tests/test_analysis_smoke.py
git commit -m "test(gh-468): add 7 smoke-plane factory functions + SmokeConfig infrastructure"
```

---

### Task 2: Add 10 parametrised endpoint test functions

**Files:**
- Modify: `app/tests/test_analysis_smoke.py`

Each test follows the same pattern:
1. Unpack `smoke_plane` fixture → `(client, aeroplane, config)`
2. POST/GET the endpoint with minimal valid input
3. Assert `response.status_code == 200` with `f"{config.name}: {response.text}"` for triage
4. Assert top-level key presence for structured responses

- [ ] **Step 1: Write `test_alpha_sweep`**

Add to `test_analysis_smoke.py`:

```python
@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_alpha_sweep(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/alpha_sweep",
        json={
            "alpha_start": -5,
            "alpha_end": 15,
            "alpha_num": 5,
            "velocity": 15.0,
            "altitude": 0,
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
```

- [ ] **Step 2: Run `test_alpha_sweep` across all 7 configs**

Run: `poetry run pytest app/tests/test_analysis_smoke.py::test_alpha_sweep -v --timeout=120`
Expected: 7 PASSED

- [ ] **Step 3: Write `test_strip_forces`**

```python
@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_strip_forces(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/strip_forces",
        json={"alpha": 5.0, "velocity": 15.0, "altitude": 0},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "surfaces" in data, f"{config.name}: missing 'surfaces' key"
```

- [ ] **Step 4: Write `test_streamlines`**

```python
@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_streamlines(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/streamlines",
        json={"alpha": 5.0, "velocity": 15.0, "altitude": 0},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
```

- [ ] **Step 5: Write `test_flight_envelope`**

```python
@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_flight_envelope(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/flight-envelope/compute",
        json={},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
```

- [ ] **Step 6: Write `test_stability_summary`**

```python
@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_stability_summary(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/stability_summary/aerobuildup",
        json={"velocity": 15.0, "alpha": 5.0, "altitude": 0},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "neutral_point_x" in data, f"{config.name}: missing 'neutral_point_x'"
    assert "static_margin" in data, f"{config.name}: missing 'static_margin'"
```

- [ ] **Step 7: Write `test_generate_default_ops`**

```python
@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_generate_default_ops(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/operating-pointsets/generate-default",
        json={"replace_existing": True},
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "operating_points" in data, f"{config.name}: missing 'operating_points'"
```

- [ ] **Step 8: Write `test_avl_trim`**

```python
@pytest.mark.slow
@pytest.mark.requires_avl
def test_avl_trim(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/operating-points/avl-trim",
        json={
            "operating_point": {
                "velocity": 15.0,
                "alpha": 5.0,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "xyz_ref": [0.15, 0.0, 0.0],
                "altitude": 0.0,
            },
            "trim_constraints": [
                {"variable": "alpha", "target": "PM", "value": 0.0},
            ],
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
```

- [ ] **Step 9: Write `test_aerobuildup_trim`**

```python
@pytest.mark.slow
@pytest.mark.requires_aerosandbox
def test_aerobuildup_trim(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/operating-points/aerobuildup-trim",
        json={
            "operating_point": {
                "velocity": 15.0,
                "alpha": 5.0,
                "beta": 0.0,
                "p": 0.0,
                "q": 0.0,
                "r": 0.0,
                "xyz_ref": [0.15, 0.0, 0.0],
                "altitude": 0.0,
            },
            "trim_variable": config.trim_ted,
            "target_coefficient": "Cm",
            "target_value": 0.0,
            "deflection_bounds": [-25.0, 25.0],
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
```

Note: `config.trim_ted` resolves to the appropriate control surface per config (e.g. "Elevator" for conventional, "Ruddervator" for V-tail, "Elevon_0" for flying wing, "Aileron" for stabilator).

- [ ] **Step 10: Write `test_mass_sweep`**

```python
@pytest.mark.integration
@pytest.mark.requires_aerosandbox
def test_mass_sweep(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.post(
        f"/aeroplanes/{aeroplane.uuid}/mass_sweep",
        json={
            "masses_kg": [1.0, 1.5, 2.0],
            "velocity": 15.0,
            "altitude": 0,
        },
    )
    assert response.status_code == 200, f"{config.name}: {response.text}"
    data = response.json()
    assert "points" in data, f"{config.name}: missing 'points'"
```

- [ ] **Step 11: Write `test_cg_comparison`**

```python
@pytest.mark.integration
def test_cg_comparison(smoke_plane):
    client, aeroplane, config = smoke_plane
    response = client.get(f"/aeroplanes/{aeroplane.uuid}/cg_comparison")
    assert response.status_code == 200, f"{config.name}: {response.text}"
```

- [ ] **Step 12: Run all 10 tests × 7 configs (fast tests only)**

Run: `poetry run pytest app/tests/test_analysis_smoke.py -v -m integration --timeout=120`
Expected: 56 PASSED (8 integration tests × 7 configs)

- [ ] **Step 13: Run slow trim tests**

Run: `poetry run pytest app/tests/test_analysis_smoke.py -v -m slow --timeout=120`
Expected: 14 PASSED (2 slow tests × 7 configs)

- [ ] **Step 14: Commit**

```bash
git add app/tests/test_analysis_smoke.py
git commit -m "test(gh-468): add 10 parametrised smoke tests across 7 aircraft configs"
```

---

### Task 3: Full verification and cleanup

**Files:**
- Read: `app/tests/test_analysis_smoke.py`, `app/tests/conftest.py`
- Read: `app/tests/test_epic417_integration.py`

- [ ] **Step 1: Kill orphaned CadQuery workers**

```bash
ORPHANS=$(ps -eo pid,ppid,command | grep 'multiprocessing.spawn' | grep -v grep | awk '$2 == 1 {print $1}')
[ -n "$ORPHANS" ] && echo "$ORPHANS" | xargs kill 2>/dev/null || true
```

- [ ] **Step 2: Run the full smoke test suite (all 70 cases)**

```bash
poetry run pytest app/tests/test_analysis_smoke.py -v --timeout=120
```

Expected: 70 PASSED (10 tests × 7 configs)

If any tests fail with backend errors (500s), these are real bugs. File new issues for each failing config/endpoint combination and mark the test with `pytest.mark.xfail(reason="gh-NNN: ...")`.

- [ ] **Step 3: Verify existing integration tests are unaffected**

```bash
poetry run pytest app/tests/test_epic417_integration.py -v --timeout=120
```

Expected: 9 PASSED — identical to baseline

- [ ] **Step 4: Verify mark-based selection works**

```bash
poetry run pytest app/tests/ -v -m integration --co -q | tail -5
poetry run pytest app/tests/ -v -m slow --co -q | tail -5
```

Expected: `integration` collects smoke + epic417 tests; `slow` collects only trim tests.

- [ ] **Step 5: Final commit if any cleanup was needed**

```bash
git add -A
git commit -m "test(gh-468): verification pass — all 70 smoke tests green"
```
