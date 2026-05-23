# gh-630 — Polar-Fit Design-Rejection Feedback to UI · Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Surface polar-fit rejections caused by **unphysical geometry** (k≤0, e_oswald ∉ (0.4, 1.0]) as visible design-warning badges in the analysis dashboard, instead of silently falling back to `e_oswald = 0.8`. Other rejection categories (sweep/data/consistency) propagate the structured reason internally but stay invisible to the user.

**Architecture:** Introduce a new Pydantic `PolarRejection` schema that travels alongside each per-configuration `ParabolicPolar` through the existing `ComputationContext.polar_by_config` JSON pipeline. Refactor `_fit_parabolic_polar` to return a 4-tuple `(cd0, e_oswald, r2, rejection)`. Every rejection branch constructs a `PolarRejection` with `gate`, `category`, `fitted_value`, `threshold`, and a human-readable `hint`. The frontend's `useComputationContext` type is extended; a small composable `PolarRejectionBadge` component renders the hint only when `category == "design"`.

**Tech Stack:** Python 3.11 + Pydantic v2 + pytest (backend); Next.js 16 / React 19 + Tailwind + vitest + playwright-bdd (frontend). No new dependencies.

---

## File Structure

### Backend

| File | Role |
|---|---|
| `app/schemas/polar_by_config.py` | **Modify** — add `PolarRejection` model and optional `rejection` field on `ParabolicPolar`. |
| `app/services/assumption_compute_service.py` | **Modify** — `_fit_parabolic_polar` returns 4-tuple; call sites in `recompute_assumptions` and `_run_polar_for_deflection` thread `rejection` into the per-config polar. |
| `app/tests/test_polar_fit.py` | **Modify** — extend existing rejection tests to assert the new tuple shape AND the `(gate, category)` mapping. Add a parametrized test that exercises every gate. |
| `app/tests/test_polar_rejection_propagation.py` | **Create** — integration test that the API endpoint serialises `rejection` for a failed design case. |

### Frontend

| File | Role |
|---|---|
| `frontend/hooks/useComputationContext.ts` | **Modify** — extend the TS interface with `PolarRejection` and `polar_by_config`. |
| `frontend/components/workbench/PolarRejectionBadge.tsx` | **Create** — small composable badge that renders the `hint` only when `category == "design"`; returns `null` otherwise. |
| `frontend/__tests__/PolarRejectionBadge.test.tsx` | **Create** — vitest unit tests for the badge component. |
| `frontend/components/workbench/analysis/<dashboard>.tsx` | **Modify** — wire the badge into the existing analysis dashboard (file pinpointed in Task 9). |
| `frontend/e2e/features/polar-design-warning.feature` | **Create** — playwright-bdd feature exercising the design-rejection visibility. |

### Boundaries

- **No** changes to AeroBuildup, AVL, NeuralFoil, sweep-data, thresholds, or `_fine_sweep_cl_max` α-resolution.
- **No** Alembic migration — `assumption_computation_context` is a JSON column; the new `rejection` key rides through `model_dump()`.
- **No** MCP-tool surface changes.
- **No** modification to existing reject-tests' assertions beyond extending tuples from length-3 to length-4. The thresholds (`0.4 < e ≤ 1.0`, ≥6 points, 20% cd0 deviation, monotonicity) stay byte-identical.

---

## Hint Catalogue (referenced by Task 3 and Task 8)

| Gate | Category | Hint (German — user-visible only for `design`) |
|---|---|---|
| `insufficient_points` | `sweep` | `"Zu wenig Punkte im linearen Polar-Fenster — α-Auflösung zu grob."` |
| `non_monotonic_polar` | `data` | `"Nicht-monotone Polare im linearen Bereich — möglicher Laminar-Bubble oder Stall-Kontamination."` |
| `negative_slope_k` | `design` | `"Polare zeigt mit steigendem Auftrieb fallenden Widerstand — wahrscheinlich Twist/Verwindung oder Planform-Kink unphysikalisch. AVL-Run prüfen."` |
| `non_positive_cd0` | `consistency` | `"Parabolischer Fit liefert negatives cd0 — Datenrauschen am unteren Fensterrand."` |
| `unphysical_e_oswald` | `design` | `"Berechnete Spannweiteneffizienz e = {value} außerhalb (0.4, 1.0]. Konfiguration für AeroBuildup vermutlich ungeeignet, AVL nutzen."` |
| `cd0_stability_mismatch` | `consistency` | `"cd0 aus Polar-Fit weicht >20 % vom Stability-Run ab — Datenkonsistenz prüfen."` |

The `{value}` placeholder in `unphysical_e_oswald` is filled with the rounded `fitted_value` at construction time.

---

## Tasks

### Task 1: Add `PolarRejection` schema and extend `ParabolicPolar`

**Files:**
- Modify: `app/schemas/polar_by_config.py`
- Test: `app/tests/test_polar_by_config_schema.py` (create)

- [ ] **Step 1: Write the failing test**

Create `app/tests/test_polar_by_config_schema.py`:

```python
"""Schema tests for the gh-630 PolarRejection extension."""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.schemas.polar_by_config import ParabolicPolar, PolarRejection


class TestPolarRejection:
    def test_minimal_construction(self):
        r = PolarRejection(
            gate="negative_slope_k",
            category="design",
            fitted_value=-0.0123,
            threshold="k > 0",
            hint="Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
        )
        assert r.gate == "negative_slope_k"
        assert r.category == "design"
        assert r.fitted_value == pytest.approx(-0.0123)
        assert r.threshold == "k > 0"
        assert r.hint.startswith("Polare")

    def test_fitted_value_may_be_none(self):
        r = PolarRejection(
            gate="insufficient_points",
            category="sweep",
            fitted_value=None,
            threshold=">= 6 points",
            hint="Zu wenig Punkte.",
        )
        assert r.fitted_value is None

    def test_rejects_unknown_gate(self):
        with pytest.raises(ValidationError):
            PolarRejection(
                gate="bogus_gate",  # type: ignore[arg-type]
                category="design",
                fitted_value=None,
                threshold="-",
                hint="-",
            )

    def test_rejects_unknown_category(self):
        with pytest.raises(ValidationError):
            PolarRejection(
                gate="negative_slope_k",
                category="weather",  # type: ignore[arg-type]
                fitted_value=None,
                threshold="-",
                hint="-",
            )

    def test_serialises_to_dict(self):
        r = PolarRejection(
            gate="unphysical_e_oswald",
            category="design",
            fitted_value=1.42,
            threshold="(0.4, 1.0]",
            hint="e = 1.42 außerhalb (0.4, 1.0].",
        )
        d = r.model_dump()
        assert d == {
            "gate": "unphysical_e_oswald",
            "category": "design",
            "fitted_value": 1.42,
            "threshold": "(0.4, 1.0]",
            "hint": "e = 1.42 außerhalb (0.4, 1.0].",
        }


class TestParabolicPolarRejectionField:
    def test_rejection_defaults_to_none(self):
        p = ParabolicPolar(cl_max=1.2)
        assert p.rejection is None

    def test_rejection_can_be_attached(self):
        rej = PolarRejection(
            gate="negative_slope_k",
            category="design",
            fitted_value=-0.001,
            threshold="k > 0",
            hint="hint",
        )
        p = ParabolicPolar(cl_max=1.2, rejection=rej)
        assert p.rejection is rej

    def test_rejection_survives_json_roundtrip(self):
        rej = PolarRejection(
            gate="unphysical_e_oswald",
            category="design",
            fitted_value=1.1,
            threshold="(0.4, 1.0]",
            hint="e=1.1 außerhalb (0.4, 1.0].",
        )
        p = ParabolicPolar(cl_max=1.2, rejection=rej)
        as_dict = p.model_dump()
        roundtripped = ParabolicPolar.model_validate(as_dict)
        assert roundtripped.rejection == rej
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-630-polar-rejection-feedback
poetry run pytest app/tests/test_polar_by_config_schema.py -v
```

Expected: `ImportError` or `AttributeError` because `PolarRejection` and the `rejection` field do not exist yet.

- [ ] **Step 3: Write minimal implementation**

Edit `app/schemas/polar_by_config.py`. Add **above** the `ParabolicPolar` class (after the existing `Provenance` block at line 32) and extend `ParabolicPolar`:

```python
RejectionGate = Literal[
    "insufficient_points",
    "non_monotonic_polar",
    "negative_slope_k",
    "non_positive_cd0",
    "unphysical_e_oswald",
    "cd0_stability_mismatch",
]
"""Which gate in `_fit_parabolic_polar` rejected the fit (gh-630)."""

RejectionCategory = Literal["sweep", "data", "design", "consistency"]
"""Coarse class of the rejection (gh-630).

- `sweep` — α-resolution too coarse; raise α density to fix.
- `data` — polar shape contaminated (laminar bubble, stall); profile / Re issue.
- `design` — geometry/config aerodynamically implausible; user-facing warning.
- `consistency` — fit conflicts with the stability-run baseline; internal sanity.
"""


class PolarRejection(BaseModel):
    """Why `_fit_parabolic_polar` could not produce a fit (gh-630).

    Disjoint from `e_oswald_quality`: set ONLY when no fit was produced.
    Surfaced to the UI only when `category == "design"`.
    """

    gate: RejectionGate = Field(..., description="Which rejection guard fired")
    category: RejectionCategory = Field(
        ..., description="Coarse class — controls UI visibility"
    )
    fitted_value: float | None = Field(
        None, description="Numeric value that triggered the rejection, when meaningful"
    )
    threshold: str = Field(..., description="Threshold expression the value failed against")
    hint: str = Field(..., description="Human-readable explanation; shown to user when design")
```

And extend `ParabolicPolar` by adding **one line** at the end of the field list (after `provenance`):

```python
    rejection: PolarRejection | None = Field(
        None,
        description="Set only when the parabolic fit was rejected (gh-630); "
                    "disjoint from e_oswald_quality which applies to successful fits.",
    )
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest app/tests/test_polar_by_config_schema.py -v
```

Expected: 8 tests pass.

- [ ] **Step 5: Commit**

```bash
git add app/schemas/polar_by_config.py app/tests/test_polar_by_config_schema.py
git commit -m "feat(gh-630): add PolarRejection schema and ParabolicPolar.rejection field"
```

---

### Task 2: Refactor `_fit_parabolic_polar` to a 4-tuple with structured rejections

**Files:**
- Modify: `app/services/assumption_compute_service.py` (`_fit_parabolic_polar` body and its return type)
- Modify: `app/tests/test_polar_fit.py` (extend existing rejection assertions to length-4)

**Why this is one task, not seven:** The function is a single unit; the 7 rejection branches share the same return-shape change. Splitting into seven micro-tasks would inflate the diff churn (each subsequent gate would force re-touching the same lines). The TDD discipline is preserved by writing the **parametrized gate-mapping test FIRST**, then refactoring the function body.

- [ ] **Step 1: Write the failing parametrized test**

Append to `app/tests/test_polar_fit.py`:

```python
# ---------------------------------------------------------------------------
# gh-630: PolarRejection propagation per gate
# ---------------------------------------------------------------------------

import math

import numpy as np
import pytest

from app.schemas.polar_by_config import PolarRejection
from app.services.assumption_compute_service import _fit_parabolic_polar


def _make_insufficient_points():
    cl_max = 1.0
    cl_lo = max(0.10, 0.10 * cl_max)
    cl_hi = 0.85 * cl_max
    cls = np.linspace(cl_lo, cl_hi, 5)
    cds = 0.03 + cls**2 / (math.pi * 0.75 * 7.0)
    return dict(cl=cls, cd=cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03)


def _make_non_monotonic():
    cl_max = 1.2
    cl_lo = max(0.10, 0.10 * cl_max)
    cl_hi = 0.85 * cl_max
    cls = np.linspace(cl_lo, cl_hi, 25)
    k = 1.0 / (math.pi * 0.75 * 7.0)
    cds = 0.03 + k * cls**2
    # Inject a downward dip mid-window — laminar-bubble signature
    mid = len(cds) // 2
    cds[mid] = cds[mid] - 0.005
    return dict(cl=cls, cd=cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03)


def _make_negative_slope():
    cl_max = 1.0
    cls = np.linspace(0.1, 0.8, 20)
    cds = 0.04 - 0.01 * cls**2  # k < 0
    return dict(cl=cls, cd=cds, ar=7.0, cl_max=cl_max, cd0_stability=0.04)


def _make_non_positive_cd0():
    cl_max = 1.0
    cls = np.linspace(0.1, 0.8, 20)
    k = 1.0 / (math.pi * 0.75 * 7.0)
    # Force a fit with cd0_intercept ≤ 0 by anchoring CD ≈ k·CL² near zero.
    # Subtract a constant slightly larger than the genuine intercept.
    cds = k * cls**2 - 0.0005
    return dict(cl=cls, cd=cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03)


def _make_unphysical_e_low():
    cl_max = 1.0
    k = 1.0 / (math.pi * 0.1 * 7.0)  # e=0.1 → out of range
    cls = np.linspace(0.1, 0.8, 20)
    cds = 0.03 + k * cls**2
    return dict(cl=cls, cd=cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03)


def _make_unphysical_e_high():
    cl_max = 1.0
    k = 1.0 / (math.pi * 1.5 * 7.0)  # e=1.5 → out of range
    cls = np.linspace(0.1, 0.8, 20)
    cds = 0.03 + k * cls**2
    return dict(cl=cls, cd=cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03)


def _make_cd0_stability_mismatch():
    cl_max = 1.0
    cls = np.linspace(0.1, 0.8, 20)
    k = 1.0 / (math.pi * 0.75 * 7.0)
    cds = 0.10 + k * cls**2  # fitted cd0≈0.10 but stability says 0.03 → 233% deviation
    return dict(cl=cls, cd=cds, ar=7.0, cl_max=cl_max, cd0_stability=0.03)


GATE_CASES = [
    ("insufficient_points", "sweep", _make_insufficient_points),
    ("non_monotonic_polar", "data", _make_non_monotonic),
    ("negative_slope_k", "design", _make_negative_slope),
    ("non_positive_cd0", "consistency", _make_non_positive_cd0),
    ("unphysical_e_oswald", "design", _make_unphysical_e_low),
    ("unphysical_e_oswald", "design", _make_unphysical_e_high),
    ("cd0_stability_mismatch", "consistency", _make_cd0_stability_mismatch),
]


@pytest.mark.parametrize("expected_gate,expected_category,factory", GATE_CASES)
def test_fit_parabolic_polar_returns_rejection(expected_gate, expected_category, factory):
    inputs = factory()
    result = _fit_parabolic_polar(**inputs)
    assert isinstance(result, tuple) and len(result) == 4, (
        "gh-630: _fit_parabolic_polar must return (cd0, e, r2, rejection)"
    )
    cd0_fit, e_fit, r2, rejection = result
    assert (cd0_fit, e_fit, r2) == (None, None, None)
    assert isinstance(rejection, PolarRejection)
    assert rejection.gate == expected_gate
    assert rejection.category == expected_category
    assert rejection.hint  # non-empty


def test_fit_parabolic_polar_success_carries_no_rejection():
    cls, cds = _make_synthetic_polar(0.031, 0.75, 7.32, 1.6)
    result = _fit_parabolic_polar(cls, cds, ar=7.32, cl_max=1.6, cd0_stability=0.031)
    assert len(result) == 4
    cd0_fit, e_fit, r2, rejection = result
    assert e_fit is not None
    assert rejection is None
```

Also **extend the existing reject-tests** in `app/tests/test_polar_fit.py` (`test_requires_min_6_points_in_window`, `test_rejects_negative_slope`, `test_rejects_e_below_0_4`, `test_rejects_e_above_1_0`, `test_rejects_laminar_bubble_non_monotonic`, etc.) so they tolerate a length-4 return. The minimal change is to update the unpacking lines from:

```python
cd0_fit, e_fit, r2 = _fit_parabolic_polar(...)
```

to:

```python
cd0_fit, e_fit, r2, *_ = _fit_parabolic_polar(...)
```

This keeps the existing assertion `(cd0_fit, e_fit, r2) == (None, None, None)` intact, satisfies the constraint that **no existing assertion is modified**, and is forward-compatible with the new tuple shape.

- [ ] **Step 2: Run tests to verify they fail**

```bash
poetry run pytest app/tests/test_polar_fit.py -v -k "test_fit_parabolic_polar_returns_rejection or test_fit_parabolic_polar_success_carries_no_rejection"
```

Expected: 8 parametrized FAILs (length-4 expectation not met). Existing tests should still pass (`*_` swallows the 3-tuple).

- [ ] **Step 3: Refactor `_fit_parabolic_polar`**

In `app/services/assumption_compute_service.py`:

1. Update the import block near the top to add:

```python
from app.schemas.polar_by_config import (
    ParabolicPolar,  # already imported elsewhere — keep one canonical import
    PolarRejection,
)
```

(Check existing imports; consolidate if `ParabolicPolar` is imported separately.)

2. Change the function signature's return type:

```python
def _fit_parabolic_polar(
    cl: np.ndarray,
    cd: np.ndarray,
    ar: float,
    cl_max: float,
    cd0_stability: float,
) -> tuple[float | None, float | None, float | None, PolarRejection | None]:
```

3. Add a small helper above `_fit_parabolic_polar`:

```python
def _build_rejection(
    gate: str,
    category: str,
    fitted_value: float | None,
    threshold: str,
    hint: str,
) -> PolarRejection:
    """Construct a PolarRejection (gh-630) with consistent rounding."""
    return PolarRejection(
        gate=gate,  # type: ignore[arg-type]
        category=category,  # type: ignore[arg-type]
        fitted_value=round(fitted_value, 6) if fitted_value is not None else None,
        threshold=threshold,
        hint=hint,
    )
```

4. Replace every `return None, None, None` inside `_fit_parabolic_polar` with `return None, None, None, _build_rejection(...)`. Match each gate exactly. The success return at the end becomes `return cd0_fit, e_oswald, r2, None`.

Concrete substitutions (preserve all existing `logger.warning(...)` calls — they stay):

```python
# Gate 1 — invalid AR
if ar is None or ar <= 0:
    logger.warning("polar fit rejected: invalid aspect ratio %r", ar)
    return None, None, None, _build_rejection(
        gate="insufficient_points",          # placeholder; see note below
        category="sweep",
        fitted_value=float(ar) if ar is not None else None,
        threshold="ar > 0",
        hint="Ungültiges Streckenverhältnis — Wing-Geometrie nicht definiert.",
    )
```

> **Note on Gate 1:** The spec for #630 explicitly puts AR-validation **out of scope** (it is upstream wing-schema responsibility). But the branch already exists in code today and must keep returning `(None, None, None, ...)` for type consistency. We map it to gate `insufficient_points`/category `sweep` only because emitting `None` for rejection would break the invariant "rejection ⇔ no fit". If in the future this branch is removed, the mapping disappears with it. The hint is intentionally generic; this gate is not user-visible (sweep category).

```python
# Gate 2 — insufficient points in window
if len(cl_win) < 6:
    logger.warning(
        "polar fit rejected: only %d points in window [%.3f, %.3f] (need ≥ 6)",
        len(cl_win), cl_lo, cl_hi,
    )
    return None, None, None, _build_rejection(
        gate="insufficient_points",
        category="sweep",
        fitted_value=float(len(cl_win)),
        threshold=">= 6 points",
        hint="Zu wenig Punkte im linearen Polar-Fenster — α-Auflösung zu grob.",
    )

# Gate 3 — non-monotonic dCD/d(CL²)
if np.any(diffs < -1e-6):
    logger.warning(
        "polar fit rejected: non-monotonic dCD/d(CL²) in window — "
        "possible laminar bubble or stall contamination"
    )
    return None, None, None, _build_rejection(
        gate="non_monotonic_polar",
        category="data",
        fitted_value=float(np.min(diffs)),
        threshold="dCD/d(CL²) >= 0",
        hint="Nicht-monotone Polare im linearen Bereich — möglicher Laminar-Bubble oder Stall-Kontamination.",
    )

# Gate 4 — non-positive slope k
if k <= 0:
    logger.warning("polar fit rejected: non-positive slope k=%.6f (requires k>0)", k)
    return None, None, None, _build_rejection(
        gate="negative_slope_k",
        category="design",
        fitted_value=float(k),
        threshold="k > 0",
        hint=(
            "Polare zeigt mit steigendem Auftrieb fallenden Widerstand — "
            "wahrscheinlich Twist/Verwindung oder Planform-Kink unphysikalisch. "
            "AVL-Run prüfen."
        ),
    )

# Gate 5 — non-positive cd0_fit
if cd0_fit <= 0:
    logger.warning("polar fit rejected: non-positive cd0_fit=%.6f (requires cd0>0)", cd0_fit)
    return None, None, None, _build_rejection(
        gate="non_positive_cd0",
        category="consistency",
        fitted_value=float(cd0_fit),
        threshold="cd0 > 0",
        hint="Parabolischer Fit liefert negatives cd0 — Datenrauschen am unteren Fensterrand.",
    )

# Gate 6 — e_oswald out of physical range
e_oswald = 1.0 / (np.pi * ar * k)
if not (0.4 < e_oswald <= 1.0):
    logger.warning(
        "polar fit rejected: e_oswald=%.4f outside physical range (0.4, 1.0]", e_oswald,
    )
    return None, None, None, _build_rejection(
        gate="unphysical_e_oswald",
        category="design",
        fitted_value=float(e_oswald),
        threshold="(0.4, 1.0]",
        hint=(
            f"Berechnete Spannweiteneffizienz e = {e_oswald:.3f} außerhalb (0.4, 1.0]. "
            "Konfiguration für AeroBuildup vermutlich ungeeignet, AVL nutzen."
        ),
    )

# Gate 7 — cd0_fit vs cd0_stability sanity
if cd0_stability > 0:
    rel_dev = abs(cd0_fit - cd0_stability) / cd0_stability
    if rel_dev > 0.20:
        logger.warning(
            "polar fit rejected: cd0_fit=%.5f deviates %.1f%% from stability run "
            "cd0=%.5f (threshold 20%%)",
            cd0_fit, rel_dev * 100, cd0_stability,
        )
        return None, None, None, _build_rejection(
            gate="cd0_stability_mismatch",
            category="consistency",
            fitted_value=float(rel_dev),
            threshold="<= 0.20",
            hint="cd0 aus Polar-Fit weicht >20 % vom Stability-Run ab — Datenkonsistenz prüfen.",
        )

# Success
...
return cd0_fit, e_oswald, r2, None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest app/tests/test_polar_fit.py -v
poetry run pytest app/tests/test_polar_by_config_schema.py -v
```

Expected: all new parametrized tests pass; **all existing tests in `test_polar_fit.py` still pass** thanks to the `*_` unpacking change.

- [ ] **Step 5: Commit**

```bash
git add app/services/assumption_compute_service.py app/tests/test_polar_fit.py
git commit -m "refactor(gh-630): _fit_parabolic_polar returns (cd0, e, r2, rejection) 4-tuple"
```

---

### Task 3: Thread rejection through `recompute_assumptions` (clean polar)

**Files:**
- Modify: `app/services/assumption_compute_service.py` (the `recompute_assumptions` block that calls `_fit_parabolic_polar` and builds `polar_clean`)
- Modify: `app/tests/test_polar_fit.py` (extend the context integration test)

- [ ] **Step 1: Write the failing test**

In `app/tests/test_polar_fit.py`, add to the existing `TestContextIntegration` class (or near other context tests):

```python
def test_polar_clean_rejection_propagates_to_context(self, client_and_db):
    """When the clean polar fit is rejected with a design gate, the rejection
    is attached to polar_by_config['clean'] in the cached context."""
    # Drive _fit_parabolic_polar via a fake that returns a design-category
    # rejection. Existing test infrastructure has _run_recompute_with_fake_polar
    # — extend it (or add a sibling) to inject (None, None, None, rejection).
    ctx = self._run_recompute_with_fake_polar(
        client_and_db,
        CESSNA_172,
        fit_succeeds=False,
        fake_rejection_kwargs=dict(
            gate="negative_slope_k",
            category="design",
            fitted_value=-0.001,
            threshold="k > 0",
            hint="Polare zeigt …",
        ),
    )
    assert ctx is not None
    pbc = ctx.get("polar_by_config", {})
    clean = pbc.get("clean", {})
    assert clean.get("rejection") is not None
    assert clean["rejection"]["gate"] == "negative_slope_k"
    assert clean["rejection"]["category"] == "design"
```

(The test depends on the fixture `_run_recompute_with_fake_polar`. If that helper currently mocks `_fit_parabolic_polar` to return a 3-tuple, update its mock to honor the new 4-tuple AND accept a `fake_rejection_kwargs` argument — see Step 3 for the helper change.)

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest app/tests/test_polar_fit.py::TestContextIntegration::test_polar_clean_rejection_propagates_to_context -v
```

Expected: KeyError or AssertionError because `polar_clean.rejection` is not set yet.

- [ ] **Step 3: Implement**

In `app/services/assumption_compute_service.py`, locate the `recompute_assumptions` call to `_fit_parabolic_polar` (around the place where `polar_clean` is built). Update unpacking and pass `rejection` into the constructor:

```python
_cd0_fit, e_oswald_fit, e_r2, _rejection = _fit_parabolic_polar(
    np.asarray(sweep_cl_arr, dtype=float),
    np.asarray(sweep_cd_arr, dtype=float),
    ar=aspect_ratio if aspect_ratio is not None else 0.0,
    cl_max=cl_max_effective_for_fit,
    cd0_stability=cd0,
)
e_oswald_fallback = e_oswald_fit is None
e_oswald_effective = e_oswald_fit if e_oswald_fit is not None else 0.8

polar_clean = ParabolicPolar(
    cd0=round(_cd0_fit, 5) if _cd0_fit is not None else None,
    e_oswald=round(e_oswald_fit, 4) if e_oswald_fit is not None else None,
    cl_max=round(cl_max, 4),
    e_oswald_r2=round(e_r2, 4) if e_r2 is not None else None,
    e_oswald_quality=_classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
    flap_deflection_deg=0.0,
    provenance="aerobuildup",
    rejection=_rejection,
)
```

Also update the test helper `_run_recompute_with_fake_polar` (in the same test file) to return a 4-tuple from its mock:

```python
def _fake_fit(*args, **kwargs):
    if fit_succeeds:
        return (0.031, 0.75, 0.95, None)
    if fake_rejection_kwargs is not None:
        return (None, None, None, PolarRejection(**fake_rejection_kwargs))
    return (None, None, None, None)
```

- [ ] **Step 4: Run test to verify it passes**

```bash
poetry run pytest app/tests/test_polar_fit.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/services/assumption_compute_service.py app/tests/test_polar_fit.py
git commit -m "feat(gh-630): attach rejection to polar_clean in recompute_assumptions"
```

---

### Task 4: Thread rejection through `_run_polar_for_deflection` (takeoff/landing)

**Files:**
- Modify: `app/services/assumption_compute_service.py` (`_run_polar_for_deflection`)
- Test: extend `app/tests/test_polar_fit.py`

- [ ] **Step 1: Write the failing test**

```python
def test_polar_landing_rejection_independent_of_clean(self, client_and_db):
    """Landing-config fit failure attaches rejection only to polar_by_config['landing'],
    leaving 'clean' (and 'takeoff') unaffected."""
    ctx = self._run_recompute_with_flap_fake(
        client_and_db,
        CESSNA_172,
        clean_succeeds=True,
        landing_succeeds=False,
        landing_rejection_kwargs=dict(
            gate="unphysical_e_oswald",
            category="design",
            fitted_value=1.12,
            threshold="(0.4, 1.0]",
            hint="e=1.12 außerhalb (0.4, 1.0].",
        ),
    )
    pbc = ctx["polar_by_config"]
    assert pbc["clean"]["rejection"] is None
    assert pbc["landing"]["rejection"]["gate"] == "unphysical_e_oswald"
    assert pbc["landing"]["rejection"]["category"] == "design"
```

(Adds a new helper `_run_recompute_with_flap_fake` modelled on the existing single-config helper.)

- [ ] **Step 2: Run test to verify it fails**

```bash
poetry run pytest app/tests/test_polar_fit.py -v -k "test_polar_landing_rejection_independent_of_clean"
```

Expected: `KeyError` on `rejection` or `None`.

- [ ] **Step 3: Implement**

In `_run_polar_for_deflection`, update both the unpacking and the `ParabolicPolar(...)` construction:

```python
_cd0_fit, e_oswald_fit, e_r2, _rejection = _fit_parabolic_polar(
    np.asarray(cl_arr, dtype=float),
    np.asarray(cd_arr, dtype=float),
    ar=aspect_ratio if aspect_ratio is not None else 0.0,
    cl_max=cl_max_effective_for_fit if cl_max_effective_for_fit else cl_max,
    cd0_stability=cd0_stability,
)

return ParabolicPolar(
    cd0=round(_cd0_fit, 5) if _cd0_fit is not None else None,
    e_oswald=round(e_oswald_fit, 4) if e_oswald_fit is not None else None,
    cl_max=round(float(cl_max), 4),
    e_oswald_r2=round(e_r2, 4) if e_r2 is not None else None,
    e_oswald_quality=_classify_polar_quality(e_r2) if e_r2 is not None else "unknown",
    flap_deflection_deg=float(flap_deflection_deg),
    provenance="aerobuildup",
    rejection=_rejection,
)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
poetry run pytest app/tests/test_polar_fit.py -v
```

- [ ] **Step 5: Commit**

```bash
git add app/services/assumption_compute_service.py app/tests/test_polar_fit.py
git commit -m "feat(gh-630): attach rejection to per-config polars (takeoff/landing)"
```

---

### Task 5: API integration test — `rejection` is in the JSON response

**Files:**
- Create: `app/tests/test_polar_rejection_propagation.py`

- [ ] **Step 1: Write the failing test**

```python
"""gh-630: end-to-end check that polar_by_config.rejection is exposed via the
get_computation_context API endpoint."""
from __future__ import annotations

from unittest.mock import patch

import pytest

from app.schemas.polar_by_config import PolarRejection


@pytest.mark.usefixtures("client_and_db")
class TestRejectionInComputationContextEndpoint:
    def test_design_rejection_is_serialised(self, client_and_db):
        client, _db, aeroplane_uuid = client_and_db

        fake_rej = PolarRejection(
            gate="negative_slope_k",
            category="design",
            fitted_value=-0.001,
            threshold="k > 0",
            hint="Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
        )

        # Patch the underlying fit so the recompute path produces this rejection
        # on the clean configuration.
        with patch(
            "app.services.assumption_compute_service._fit_parabolic_polar",
            return_value=(None, None, None, fake_rej),
        ):
            r = client.post(
                f"/api/v2/aeroplanes/{aeroplane_uuid}/assumptions/recompute"
            )
            assert r.status_code in (200, 204)

        r = client.get(
            f"/api/v2/aeroplanes/{aeroplane_uuid}/assumptions/computation-context"
        )
        assert r.status_code == 200
        ctx = r.json()
        clean = ctx["polar_by_config"]["clean"]
        assert clean["rejection"] == {
            "gate": "negative_slope_k",
            "category": "design",
            "fitted_value": -0.001,
            "threshold": "k > 0",
            "hint": "Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
        }
```

- [ ] **Step 2: Run test to verify it fails (then passes)**

```bash
poetry run pytest app/tests/test_polar_rejection_propagation.py -v
```

If Tasks 3 and 4 are correctly implemented, this test passes immediately. If it fails, the failure pinpoints which serialisation hop is dropping the field.

- [ ] **Step 3: Adjust if needed**

If serialisation breaks, check that `ParabolicPolar.model_dump()` includes the new field with `None`-default. Pydantic v2 includes optional fields by default; no `model_config` change should be required.

- [ ] **Step 4: Commit**

```bash
git add app/tests/test_polar_rejection_propagation.py
git commit -m "test(gh-630): end-to-end rejection serialisation through API"
```

---

### Task 6: Frontend types — extend `ComputationContext` with `polar_by_config`

**Files:**
- Modify: `frontend/hooks/useComputationContext.ts`

**Read first:** `frontend/AGENTS.md` warns that Next.js 16 + React 19 may differ from training data. The task here is **types-only**, so framework differences do not bite — but verify by skimming the existing file before editing.

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/useComputationContext.types.test.ts`:

```typescript
import { describe, it, expectTypeOf } from "vitest";
import type {
  ComputationContext,
  PolarRejection,
  PolarRejectionGate,
  PolarRejectionCategory,
} from "@/hooks/useComputationContext";

describe("useComputationContext types (gh-630)", () => {
  it("PolarRejection has the six gate literals", () => {
    expectTypeOf<PolarRejectionGate>().toEqualTypeOf<
      | "insufficient_points"
      | "non_monotonic_polar"
      | "negative_slope_k"
      | "non_positive_cd0"
      | "unphysical_e_oswald"
      | "cd0_stability_mismatch"
    >();
  });

  it("PolarRejection has the four category literals", () => {
    expectTypeOf<PolarRejectionCategory>().toEqualTypeOf<
      "sweep" | "data" | "design" | "consistency"
    >();
  });

  it("PolarRejection shape matches the backend schema", () => {
    expectTypeOf<PolarRejection>().toMatchTypeOf<{
      gate: PolarRejectionGate;
      category: PolarRejectionCategory;
      fitted_value: number | null;
      threshold: string;
      hint: string;
    }>();
  });

  it("ComputationContext.polar_by_config carries optional rejection per config", () => {
    expectTypeOf<ComputationContext["polar_by_config"]>().toMatchTypeOf<
      | {
          clean: { rejection: PolarRejection | null };
          takeoff: { rejection: PolarRejection | null };
          landing: { rejection: PolarRejection | null };
        }
      | undefined
    >();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm run test:unit -- useComputationContext.types
```

Expected: type errors — `PolarRejection`, `PolarRejectionGate`, `PolarRejectionCategory`, `polar_by_config` are not exported.

- [ ] **Step 3: Implement**

Edit `frontend/hooks/useComputationContext.ts`. Inside the existing `"use client";` module, **add** above the `ComputationContext` interface:

```typescript
export type PolarRejectionGate =
  | "insufficient_points"
  | "non_monotonic_polar"
  | "negative_slope_k"
  | "non_positive_cd0"
  | "unphysical_e_oswald"
  | "cd0_stability_mismatch";

export type PolarRejectionCategory = "sweep" | "data" | "design" | "consistency";

export interface PolarRejection {
  gate: PolarRejectionGate;
  category: PolarRejectionCategory;
  fitted_value: number | null;
  threshold: string;
  hint: string;
}

export type PolarConfigName = "clean" | "takeoff" | "landing";

export interface ParabolicPolar {
  cd0: number | null;
  e_oswald: number | null;
  cl_max: number;
  e_oswald_r2: number | null;
  e_oswald_quality: "high" | "medium" | "low" | "unknown";
  flap_deflection_deg: number;
  provenance: string;
  rejection: PolarRejection | null;
}

export type PolarByConfig = Record<PolarConfigName, ParabolicPolar>;
```

Then extend `ComputationContext` with one additional optional field:

```typescript
  polar_by_config?: PolarByConfig;
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run test:unit -- useComputationContext.types
```

- [ ] **Step 5: Commit**

```bash
git add frontend/hooks/useComputationContext.ts frontend/__tests__/useComputationContext.types.test.ts
git commit -m "feat(gh-630): extend ComputationContext type with polar_by_config + PolarRejection"
```

---

### Task 7: Build `PolarRejectionBadge` — small composable component

**Files:**
- Create: `frontend/components/workbench/PolarRejectionBadge.tsx`
- Create: `frontend/__tests__/PolarRejectionBadge.test.tsx`

**Design notes:**
- Composition-first: the badge accepts a `PolarRejection | null` and decides internally whether to render. **No boolean `isDesign` prop.** Caller does not need to know category-routing rules — that's the component's job.
- Visual: dark amber pill — `bg-amber-500/15 border border-amber-500/40 text-amber-200`. Uses `AlertTriangle` from `lucide-react`. Matches the existing dark-theme + orange-accent style without overlapping the `AlertBanner` primitive (which is for full-width section warnings).
- Returns `null` for any `category !== "design"` or when `rejection` is `null` — caller can render unconditionally.

- [ ] **Step 1: Write the failing test**

Create `frontend/__tests__/PolarRejectionBadge.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

vi.mock("lucide-react", () => ({
  AlertTriangle: (props: Record<string, unknown>) => (
    <svg data-testid="warn-icon" {...props} />
  ),
}));

import { PolarRejectionBadge } from "../components/workbench/PolarRejectionBadge";
import type { PolarRejection } from "../hooks/useComputationContext";

const designRejection: PolarRejection = {
  gate: "negative_slope_k",
  category: "design",
  fitted_value: -0.001,
  threshold: "k > 0",
  hint: "Polare zeigt mit steigendem Auftrieb fallenden Widerstand.",
};

const sweepRejection: PolarRejection = {
  gate: "insufficient_points",
  category: "sweep",
  fitted_value: 5,
  threshold: ">= 6 points",
  hint: "Zu wenig Punkte.",
};

const dataRejection: PolarRejection = {
  ...sweepRejection,
  gate: "non_monotonic_polar",
  category: "data",
};

const consistencyRejection: PolarRejection = {
  ...sweepRejection,
  gate: "cd0_stability_mismatch",
  category: "consistency",
};

describe("PolarRejectionBadge", () => {
  it("renders the hint when category is design", () => {
    const { container } = render(<PolarRejectionBadge rejection={designRejection} />);
    expect(screen.getByText(designRejection.hint)).toBeDefined();
    expect(screen.getByTestId("warn-icon")).toBeDefined();
    expect(container.firstChild).not.toBeNull();
  });

  it("renders nothing when rejection is null", () => {
    const { container } = render(<PolarRejectionBadge rejection={null} />);
    expect(container.firstChild).toBeNull();
  });

  it.each([
    ["sweep", sweepRejection],
    ["data", dataRejection],
    ["consistency", consistencyRejection],
  ] as const)("renders nothing when category is %s", (_label, rej) => {
    const { container } = render(<PolarRejectionBadge rejection={rej} />);
    expect(container.firstChild).toBeNull();
  });

  it("exposes role=alert for accessibility on design rejection", () => {
    render(<PolarRejectionBadge rejection={designRejection} />);
    expect(screen.getByRole("alert")).toBeDefined();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm run test:unit -- PolarRejectionBadge
```

Expected: Module-not-found.

- [ ] **Step 3: Implement**

Create `frontend/components/workbench/PolarRejectionBadge.tsx`:

```typescript
"use client";

import { AlertTriangle } from "lucide-react";

import type { PolarRejection } from "@/hooks/useComputationContext";

export interface PolarRejectionBadgeProps {
  rejection: PolarRejection | null;
}

/**
 * gh-630: surface aerodynamically implausible polar-fit rejections
 * (k <= 0, e_oswald outside (0.4, 1.0]) to the user as a design warning.
 *
 * Renders nothing for `null` or for non-`design` categories — sweep, data,
 * and consistency rejections are internal-only. Callers should pass
 * `rejection` directly without category-routing.
 */
export function PolarRejectionBadge({ rejection }: PolarRejectionBadgeProps) {
  if (rejection === null || rejection.category !== "design") {
    return null;
  }
  return (
    <div
      role="alert"
      className="inline-flex items-center gap-2 rounded-md border border-amber-500/40 bg-amber-500/15 px-2.5 py-1 text-xs leading-tight text-amber-200"
    >
      <AlertTriangle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
      <span className="font-medium">Design issue:</span>
      <span>{rejection.hint}</span>
    </div>
  );
}
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run test:unit -- PolarRejectionBadge
```

Expected: all 6 cases pass (1 design + 1 null + 3 non-design + 1 a11y).

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/PolarRejectionBadge.tsx frontend/__tests__/PolarRejectionBadge.test.tsx
git commit -m "feat(gh-630): add PolarRejectionBadge component (composable, design-only visibility)"
```

---

### Task 8: Wire the badge into the analysis dashboard

**Files:**
- Modify: `frontend/components/workbench/PerformanceOverview.tsx` (or — if a more specific polar-display component exists — wire it there)
- Test: extend `frontend/__tests__/PerformanceOverview.test.tsx` (create if absent)

**Pre-step: confirm host component.**

```bash
cd /Users/szymanski/Projects/da3Dalus/cad-modelling-service/.claude/worktrees/feat+gh-630-polar-rejection-feedback
grep -rn "polar_by_config\|e_oswald" frontend/components/workbench/ | head -30
```

If a component already reads `polar_by_config` (likely `PerformanceOverview.tsx`, `AssumptionsPanel.tsx`, or `MatchingChartTab.tsx`), wire the badge there next to where polar metrics or `e_oswald_quality` are rendered. Otherwise, wire into `PerformanceOverview.tsx` near the existing KPI cards — it already imports `useComputationContext`.

- [ ] **Step 1: Write the failing test**

Create or extend `frontend/__tests__/PerformanceOverview.test.tsx`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import React from "react";

import type {
  ComputationContext,
  PolarRejection,
} from "@/hooks/useComputationContext";

vi.mock("lucide-react", () => new Proxy({}, {
  get: () => (p: Record<string, unknown>) => <svg data-testid="icon" {...p} />,
}));

const designRej: PolarRejection = {
  gate: "negative_slope_k",
  category: "design",
  fitted_value: -0.001,
  threshold: "k > 0",
  hint: "Polare zeigt …",
};

const baseContext: ComputationContext = {
  v_cruise_mps: 50,
  reynolds: 1e6,
  mac_m: 1.2,
  x_np_m: 0.3,
  target_static_margin: 0.1,
  cg_agg_m: 0.25,
  computed_at: "2026-05-23T00:00:00Z",
  polar_by_config: {
    clean: {
      cd0: null, e_oswald: null, cl_max: 1.2, e_oswald_r2: null,
      e_oswald_quality: "unknown", flap_deflection_deg: 0, provenance: "aerobuildup",
      rejection: designRej,
    },
    takeoff: {
      cd0: 0.04, e_oswald: 0.78, cl_max: 1.6, e_oswald_r2: 0.99,
      e_oswald_quality: "high", flap_deflection_deg: 15, provenance: "aerobuildup",
      rejection: null,
    },
    landing: {
      cd0: 0.05, e_oswald: 0.75, cl_max: 2.0, e_oswald_r2: 0.98,
      e_oswald_quality: "high", flap_deflection_deg: 35, provenance: "aerobuildup",
      rejection: null,
    },
  },
};

vi.mock("@/hooks/useComputationContext", async (importOriginal) => {
  const actual = (await importOriginal()) as Record<string, unknown>;
  return {
    ...actual,
    useComputationContext: () => ({
      data: baseContext, error: undefined, isLoading: false, mutate: vi.fn(),
    }),
  };
});

import { PerformanceOverview } from "../components/workbench/PerformanceOverview";

describe("PerformanceOverview — PolarRejectionBadge wiring (gh-630)", () => {
  it("shows the design-rejection hint when polar_by_config.clean has a design rejection", () => {
    render(<PerformanceOverview aeroplaneId="x" />);
    expect(screen.getByText(/Polare zeigt …/)).toBeDefined();
    expect(screen.getByRole("alert")).toBeDefined();
  });

  it("renders no rejection badge when all polars succeed", () => {
    const ctx = {
      ...baseContext,
      polar_by_config: {
        ...baseContext.polar_by_config!,
        clean: { ...baseContext.polar_by_config!.clean, rejection: null },
      },
    };
    // Swap the mock implementation:
    vi.mocked(
      (await import("@/hooks/useComputationContext")).useComputationContext,
    ).mockReturnValueOnce({ data: ctx, error: undefined, isLoading: false, mutate: vi.fn() });

    render(<PerformanceOverview aeroplaneId="x" />);
    expect(screen.queryByRole("alert")).toBeNull();
  });
});
```

> **Note:** The exact `PerformanceOverview` props signature must match the real one. Adjust the props passed in the test to whatever the real component takes (likely `aeroplaneId: string`).

- [ ] **Step 2: Run test to verify it fails**

```bash
cd frontend && npm run test:unit -- PerformanceOverview
```

Expected: no `role="alert"` rendered yet.

- [ ] **Step 3: Implement**

In `PerformanceOverview.tsx`, import the badge and render one instance per configuration:

```typescript
import { PolarRejectionBadge } from "./PolarRejectionBadge";

// inside the JSX, near where polar/e_oswald data is currently rendered:
{data?.polar_by_config && (
  <div className="flex flex-col gap-1 mt-2">
    <PolarRejectionBadge rejection={data.polar_by_config.clean.rejection} />
    <PolarRejectionBadge rejection={data.polar_by_config.takeoff.rejection} />
    <PolarRejectionBadge rejection={data.polar_by_config.landing.rejection} />
  </div>
)}
```

Because the badge returns `null` for non-design / null cases, the visible output is exactly the design-category rejections. No extra branching is needed in the host.

- [ ] **Step 4: Run test to verify it passes**

```bash
cd frontend && npm run test:unit -- PerformanceOverview
```

- [ ] **Step 5: Commit**

```bash
git add frontend/components/workbench/PerformanceOverview.tsx frontend/__tests__/PerformanceOverview.test.tsx
git commit -m "feat(gh-630): wire PolarRejectionBadge into analysis dashboard"
```

---

### Task 9: End-to-end Playwright-BDD scenario

**Files:**
- Create: `frontend/e2e/features/polar-design-warning.feature`
- Modify: relevant step-definitions file under `frontend/e2e/steps/` to back the new Gherkin steps

- [ ] **Step 1: Write the failing scenario**

Create `frontend/e2e/features/polar-design-warning.feature`:

```gherkin
Feature: Polar fit design-warning badge (gh-630)

  Scenario: Design-category polar rejection surfaces a warning in the analysis dashboard
    Given an aeroplane whose clean parabolic-polar fit fails with a negative-slope design rejection
    When I open the analysis dashboard
    Then a visible design-warning badge displays the rejection hint
    And the badge has the accessible role "alert"

  Scenario: Sweep-category polar rejection stays invisible
    Given an aeroplane whose clean parabolic-polar fit fails with an insufficient-points sweep rejection
    When I open the analysis dashboard
    Then no polar-design-warning badge is visible

  Scenario: Successful polar fits show no warning
    Given an aeroplane whose three parabolic-polar fits all succeed
    When I open the analysis dashboard
    Then no polar-design-warning badge is visible
```

Implement the three new `Given`/`When`/`Then` steps in the corresponding step file (find via `grep -l "Given an aeroplane" frontend/e2e/steps/` and follow the existing pattern). The `Given` steps stub the API to return crafted `computation-context` payloads.

- [ ] **Step 2: Run scenarios to verify they fail**

```bash
cd frontend && npm run test:e2e -- polar-design-warning
```

Expected: at least the first scenario fails because the assertion expects a visible badge.

- [ ] **Step 3: Implement step glue and ensure the dashboard wiring covers them**

Most likely no further production-code changes are needed if Task 8 was completed correctly — only step-definition glue. If a real wiring gap surfaces (e.g. an alternate dashboard tab that needs the badge), wire it there too in the smallest possible change.

- [ ] **Step 4: Run scenarios to verify they pass**

```bash
cd frontend && npm run test:e2e -- polar-design-warning
```

- [ ] **Step 5: Commit**

```bash
git add frontend/e2e/features/polar-design-warning.feature frontend/e2e/steps/
git commit -m "test(gh-630): playwright-bdd scenarios for polar design-warning visibility"
```

---

### Task 10: Coverage check and final wrap-up

- [ ] **Step 1: Run backend tests with coverage**

```bash
poetry run pytest app/tests/test_polar_fit.py app/tests/test_polar_by_config_schema.py app/tests/test_polar_rejection_propagation.py \
  --cov=app.schemas.polar_by_config --cov=app.services.assumption_compute_service --cov-report=term-missing
```

Expected: coverage on **new code paths** (every `_build_rejection` branch + `PolarRejection` validators) ≥ 80 %.

- [ ] **Step 2: Run frontend unit tests**

```bash
cd frontend && npm run test:unit
```

Expected: all unit tests pass, including the new ones from Tasks 6, 7, and 8.

- [ ] **Step 3: Run e2e tests**

```bash
cd frontend && npm run test:e2e
```

Expected: full e2e suite passes, including the gh-630 scenarios.

- [ ] **Step 4: Run lint and dependency-cruiser**

```bash
poetry run ruff check .
poetry run ruff format --check .
cd frontend && npm run lint && npm run deps:check
```

- [ ] **Step 5: Open the PR**

```bash
git push -u github feat/gh-630-polar-rejection-feedback
gh pr create \
  --title "feat(gh-630): surface polar-fit design rejections as UI warnings" \
  --body "$(cat <<'EOF'
## Summary
- Adds `PolarRejection` schema (gate, category, fitted_value, threshold, hint)
- Refactors `_fit_parabolic_polar` to return a 4-tuple `(cd0, e, r2, rejection)`
- Wires rejection through `recompute_assumptions` and `_run_polar_for_deflection` into all three per-config polars
- Frontend renders an amber design-warning badge **only when** `category == "design"`; sweep/data/consistency stay invisible
- Thresholds and existing test assertions are unchanged

## Test plan
- [ ] `poetry run pytest app/tests/test_polar_fit.py`
- [ ] `poetry run pytest app/tests/test_polar_by_config_schema.py`
- [ ] `poetry run pytest app/tests/test_polar_rejection_propagation.py`
- [ ] `cd frontend && npm run test:unit`
- [ ] `cd frontend && npm run test:e2e -- polar-design-warning`
- [ ] Coverage on new code paths ≥ 80 %

Closes #630
EOF
)"
```

---

## Self-Review

**Spec coverage (every AC from #630):**

| AC | Task |
|---|---|
| 1. `PolarRejection` schema in `polar_by_config.py` with the six gate literals and four category literals | Task 1 |
| 2. `ParabolicPolar.rejection: PolarRejection \| None = None` | Task 1 |
| 3. `_fit_parabolic_polar` returns a 4-tuple; every existing rejection branch constructs a `PolarRejection` | Task 2 |
| 4. Call sites (`recompute_assumptions`, `_run_polar_for_deflection`) attach `rejection` | Tasks 3 and 4 |
| 5. Three configurations carry `rejection` independently | Task 4 (parametrised) |
| 6. Existing analysis/assumptions endpoints serialise the new field | Task 5 |
| 7. Frontend Analysis-Dashboard displays a badge for `design` only | Tasks 7 and 8 |
| 8. Backend unit tests: one per gate, asserting tuple shape and (gate, category) mapping | Task 2 (parametrize over `GATE_CASES`) |
| 9. Frontend test: design-category produces badge; sweep/data/consistency don't | Task 7 + Task 9 |
| 10. No existing tests need modification to pass | Task 2 (`*_` unpacking is non-modifying for assertions) |
| 11. > 80 % coverage on new `PolarRejection` construction paths | Task 10 |

**Placeholder scan:** no `TODO`, `TBD`, or "similar to" references in any task body — every step contains the code, command, or text required.

**Type consistency:** `PolarRejection`, `PolarRejectionGate`, `PolarRejectionCategory` — used identically in backend (Pydantic) and frontend (TS). `_build_rejection` helper signature stable across all 7 callsites. Tuple length-4 is consistent from Task 2 onward.

**Out-of-scope is respected:**
- No α-resolution change in `_fine_sweep_cl_max` ✓
- No new AR schema validation (Gate 1 in Task 2 reuses `insufficient_points`/`sweep` and emits a generic hint; no Pydantic-level AR check is added) ✓
- No threshold tuning — every existing `if` condition is preserved ✓
- No MCP-tool changes — the serialisation rides through `model_dump()` ✓
- No auto-geometry-fixes — badge is informational only ✓
