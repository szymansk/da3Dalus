# Implementation Plan: #416 — Control Surface Deflection Overrides on Operating Points

## Goal

Add a `control_deflections` field to operating points so that runtime
control surface deflection angles can be specified per analysis run,
independent of the geometry definition. This enables manual deflection
sweeps, trim analysis (future #418/#419), and what-if studies.

## Scope

- Backend schema, model, migration, analysis logic, tests
- Frontend is out of scope (separate ticket per issue)

## Architecture

```
OperatingPointSchema.control_deflections: dict[str, float] | None
         │
         ▼
analyse_aerodynamics()
  ├─ AVL:          build_control_deflection_commands(airplane, overrides)
  ├─ AeroBuildup:  airplane.with_control_deflections(overrides)
  └─ VLM:          airplane.with_control_deflections(overrides)
         │
         ▼
OperatingPointModel.control_deflections: Column(JSON, nullable=True)
```

Override merge logic: OP overrides take precedence over geometry defaults.
For AVL, this means modifying `build_control_deflection_commands` to
accept an optional override dict. For AeroBuildup/VLM, this means calling
`with_control_deflections()` before solver instantiation.

## Tasks

### Task 1: Schema Changes (RED → GREEN)

**Files:** `app/schemas/aeroanalysisschema.py`

1. Add to `OperatingPointSchema`:
   ```python
   control_deflections: dict[str, float] | None = Field(
       default=None,
       description="Runtime control surface deflections (name → degrees). "
                   "Overrides geometry defaults for this operating point.",
   )
   ```

2. Add to `StoredOperatingPointCreate`:
   ```python
   control_deflections: dict[str, float] | None = Field(
       default=None,
       description="Runtime control surface deflections (name → degrees). "
                   "Overrides geometry defaults for this operating point.",
   )
   ```

3. Update the `json_schema_extra` example in `OperatingPointSchema`.

**Tests:** `app/tests/test_operating_point_deflections.py`
- Schema accepts `control_deflections` as dict
- Schema accepts `control_deflections` as None (default)
- Schema rejects invalid types
- `StoredOperatingPointCreate` round-trips with deflections

### Task 2: Model + Migration

**Files:**
- `app/models/analysismodels.py` — add `control_deflections = Column(JSON, nullable=True)`
- `alembic/versions/<new>_add_control_deflections_to_operating_points.py`

**Tests:**
- Model round-trip: create with deflections, read back, verify JSON
- Model default: create without deflections, verify None

### Task 3: Analysis Logic — AeroBuildup & VLM

**Files:** `app/api/utils.py`

Modify `analyse_aerodynamics()` to apply deflection overrides:

```python
def analyse_aerodynamics(...):
    op_point = _build_operating_point(operating_point)
    asb_airplane.xyz_ref = operating_point.xyz_ref

    # Apply control deflection overrides if present
    if operating_point.control_deflections:
        asb_airplane = asb_airplane.with_control_deflections(
            operating_point.control_deflections
        )
    ...
```

This handles AeroBuildup and VLM automatically since they both use
the `asb_airplane` object directly. For AVL, the deflection commands
are built separately (Task 4).

**Tests:** `app/tests/test_operating_point_deflections.py`
- AeroBuildup receives airplane with overridden deflections (mock)
- VLM receives airplane with overridden deflections (mock)
- No override → airplane passed unchanged
- Override dict is empty → treated as no override

### Task 4: Analysis Logic — AVL

**Files:** `app/services/avl_strip_forces.py`, `app/api/utils.py`

Modify `build_control_deflection_commands()` to accept optional overrides:

```python
def build_control_deflection_commands(
    airplane,
    overrides: dict[str, float] | None = None,
) -> list[str]:
    seen: dict[str, float] = {}
    for wing in airplane.wings:
        for xsec in wing.xsecs:
            for cs in xsec.control_surfaces:
                if cs.name not in seen:
                    seen[cs.name] = float(cs.deflection)
    # Apply overrides — OP deflections take precedence
    if overrides:
        for name, defl in overrides.items():
            if name in seen:
                seen[name] = float(defl)
    return [f"d{i} d{i} {defl}" for i, defl in enumerate(seen.values(), 1)]
```

Update `_build_control_run_command()` in `utils.py` to pass overrides:

```python
def _build_control_run_command(asb_airplane, overrides=None) -> str | None:
    from app.services.avl_strip_forces import build_control_deflection_commands
    commands = build_control_deflection_commands(asb_airplane, overrides)
    return "\n".join(commands) if commands else None
```

Update `_run_avl()` to accept and pass overrides.

Also update `AVLWithStripForces._default_keystroke_file_contents()` to
accept overrides (for strip forces endpoint).

**Tests:** `app/tests/test_operating_point_deflections.py`
- `build_control_deflection_commands` with no overrides → geometry defaults
- `build_control_deflection_commands` with overrides → merged values
- Override for non-existent control surface → ignored (only known surfaces)
- AVL `_run_avl` passes overrides through
- `AVLWithStripForces` passes overrides through

### Task 5: CRUD Endpoint Tests

**Files:** `app/tests/test_operating_points_endpoint.py` (extend)

- Create OP with `control_deflections` → persisted and returned
- Update OP with `control_deflections` → updated
- Create OP without deflections → `control_deflections` is None
- List OPs → deflections included in response

### Task 6: Integration Test (mark slow)

**Files:** `app/tests/test_operating_point_deflections_integration.py`

- End-to-end: create OP with deflections → run AeroBuildup analysis →
  verify results differ from geometry-default run
- Mark `@pytest.mark.slow`

## Acceptance Criteria (from issue)

- [x] `OperatingPointSchema` has `control_deflections: dict[str, float] | None`
- [x] `OperatingPointModel` persists deflections as JSON
- [x] `analyse_aerodynamics()` applies overrides for AeroBuildup
- [x] `analyse_aerodynamics()` applies overrides for VLM
- [x] `build_control_deflection_commands()` applies overrides for AVL
- [x] CRUD endpoints handle the new field
- [x] All solver paths tested
- [x] Migration exists and is reversible

## Out of Scope

- Frontend UI for deflection input (separate ticket)
- `/compute` endpoint (part of broader OP extensions, needs event system)
- Event-driven invalidation (Phase 2 infrastructure)
