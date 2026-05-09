# E2E Analysis Smoke Test Suite — Design Spec

## Goal

A Playwright-BDD test suite that verifies every analysis action in the
da3Dalus workbench produces a working response (no 500 errors) across
7 aircraft configurations covering all control surface role
combinations. Tests run against an isolated test database, not the
user's development DB.

## Problem

The existing `.feature` files describe aspirational user flows but
don't actually run against the real backend. Clicking "Compute
Stability" on a real plane produces a 500 error that no test catches.
This suite fixes that by exercising every "Run/Compute/Generate"
button on every analysis tab with realistic aircraft geometry.

## Architecture

```
scripts/seed_e2e_planes.py          # Python seeder — creates test DB
frontend/e2e/
  features/analysis-smoke.feature   # Gherkin scenarios (Scenario Outline × 7 planes)
  steps/analysis-smoke.steps.ts     # Step definitions
  global-setup.ts                   # Starts backend with test DB
  global-teardown.ts                # Kills backend, deletes test DB
```

### Pipeline

1. `global-setup.ts` runs `poetry run python scripts/seed_e2e_planes.py`
   → creates `db/e2e_test.db`, runs Alembic migrations, inserts 7 planes
2. `global-setup.ts` starts the backend with
   `SQLALCHEMY_DATABASE_URL=sqlite:///./db/e2e_test.db`
3. Playwright runs all analysis smoke tests against the backend
4. `global-teardown.ts` kills the backend process, deletes `db/e2e_test.db`

The frontend dev server is managed by Playwright's existing `webServer`
config (reuses running instance or starts one).

---

## Test Plane Configurations

All planes use Peter's Glider geometry from AeroSandbox:

**Main wing** (symmetric, SD7037):
- Section 0 (root→mid): `xyz_le=[0, 0, 0]`, chord 0.18m, twist 2°
- Section 1 (mid→tip): `xyz_le=[0.01, 0.5, 0]`, chord 0.16m, twist 0°
- Section 2 (tip):      `xyz_le=[0.08, 1.0, 0.1]`, chord 0.08m, twist -2°

**Horizontal stabilizer** (symmetric, NACA 0010):
- Root: chord 0.10m, twist -10°, at `[0.6, 0, 0.06]`
- Tip:  chord 0.08m, twist -10°, at `[0.62, 0.17, 0.06]`

**Vertical stabilizer** (non-symmetric, NACA 0010):
- Root: chord 0.10m, twist 0°, at `[0.6, 0, 0.07]`
- Tip:  chord 0.06m, twist 0°, at `[0.64, 0, 0.22]`

**V-tail** (symmetric, NACA 0010, dihedral ~35°):
- Root: chord 0.12m, twist -10°, at `[0.6, 0, 0.06]`
- Tip:  chord 0.08m, twist -10°, at `[0.62, 0.17, 0.12]`

All TEDs use: hinge at 75% chord, ±25° deflection limits, 0° initial
deflection.

### Configuration Matrix

| # | Name                      | Wing sec 0 | Wing sec 1 | Tail                    | Tail TEDs              |
|---|---------------------------|------------|------------|-------------------------|------------------------|
| 1 | `e2e-conventional-ttail`  | —          | aileron    | htail + vtail           | elevator + rudder      |
| 2 | `e2e-vtail-ruddervator`   | —          | aileron    | V-tail (×2 symmetric)   | ruddervator × 2        |
| 3 | `e2e-conventional-cross`  | —          | aileron    | htail + vtail (cross)   | elevator + rudder      |
| 4 | `e2e-flying-wing`         | elevon     | elevon     | none                    | —                      |
| 5 | `e2e-flaperon-ttail`      | flaperon   | flaperon   | htail + vtail           | elevator + rudder      |
| 6 | `e2e-flap-aileron-ttail`  | flap       | aileron    | htail + vtail           | elevator + rudder      |
| 7 | `e2e-stabilator-ttail`    | —          | aileron    | htail (all-moving) + vt | stabilator + rudder    |

**Config differences:**
- Config 3 vs 1: htail at `[0.6, 0, 0.0]` (base-mounted) vs `[0.6, 0, 0.06]`
- Config 4: no tail surfaces, swept wing for pitch authority
- Config 7: htail has no TED — the entire surface is the stabilator
  (role on the wing, not on a TED)

**Design assumptions** (seeded per plane):
- mass: 1.5 kg
- cg_x: 0.15 m
- cl_max: 1.4
- g_limit: 3.0
- cd0: 0.03
- target_static_margin: 0.12

---

## Analysis Actions Under Test

Every plane exercises every applicable action. The test asserts:
- HTTP response is not 4xx/5xx
- Response body contains expected top-level fields

### Tab: Polar

**Action:** Run alpha sweep (AVL)
**Endpoint:** `POST /aeroplanes/{id}/alpha_sweep`
**Body:** `{ "alpha_start": -5, "alpha_end": 15, "alpha_step": 1, "velocity": 15, "altitude": 0 }`
**Expected fields:** `alphas`, `CLs`, `CDs`

### Tab: Trefftz Plane

**Action:** Run strip forces (AVL)
**Endpoint:** `POST /aeroplanes/{id}/strip_forces`
**Body:** `{ "alpha": 5, "velocity": 15, "altitude": 0 }`
**Expected fields:** `strips` (array)

### Tab: Streamlines

**Action:** Run streamlines (AVL)
**Endpoint:** `POST /aeroplanes/{id}/streamlines`
**Body:** `{ "alpha": 5, "velocity": 15, "altitude": 0 }`
**Expected fields:** response is 200 (streamlines return a URL or data)

### Tab: Envelope

**Action:** Compute flight envelope
**Endpoint:** `POST /aeroplanes/{id}/flight-envelope/compute`
**Body:** `{}`
**Expected fields:** `vn_diagram` or `envelope`

### Tab: Stability

**Action:** Compute stability summary (AVL)
**Endpoint:** `POST /aeroplanes/{id}/stability_summary/avl`
**Body:** `{ "velocity": 20, "alpha": 2, "beta": 0, "altitude": 0 }`
**Expected fields:** `neutral_point`, `static_margin`, `derivatives`

### Tab: Operating Points

**Action 1:** Generate default OPs
**Endpoint:** `POST /aeroplanes/{id}/operating-pointsets/generate-default`
**Body:** `{ "replace_existing": true }`
**Expected fields:** `operating_points` (array, length ≥ 8)

**Action 2:** Trim with AVL (on the generated "cruise" OP)
**Endpoint:** `POST /aeroplanes/{id}/operating-points/avl-trim`
**Body:** `{ "operating_point": { ... cruise OP ... }, "constraints": [...] }`
**Expected fields:** `status`, `trim_result`

**Action 3:** Trim with AeroBuildup (on the generated "cruise" OP)
**Endpoint:** `POST /aeroplanes/{id}/operating-points/aerobuildup-trim`
**Body:** `{ "operating_point": { ... cruise OP ... }, "trim_variable": "elevator", ... }`
**Expected fields:** `status`, `trim_result`

### Tab: Assumptions

**Action:** Compute mass sweep
**Endpoint:** `POST /aeroplanes/{id}/mass_sweep`
**Body:** `{ "velocity": 15, "altitude": 0 }`
**Expected fields:** `masses`, `cls` or `sweep_data`

**Passive check:** CG comparison loads on tab open
**Endpoint:** `GET /aeroplanes/{id}/cg_comparison`
**Expected:** 200

---

## Feature File Structure

A single feature file using Scenario Outlines parameterized by plane
name. This avoids duplicating scenarios 7 times while making failures
clearly report which config broke.

```gherkin
Feature: Analysis Smoke Tests
  All analysis actions must complete without errors across all
  aircraft configurations.

  Background:
    Given the e2e backend is running with the test database

  Scenario Outline: Alpha sweep completes without error
    When I run an alpha sweep on "<plane>"
    Then the response status is 200
    And the response contains "alphas"
    And the response contains "CLs"

    Examples:
      | plane                     |
      | e2e-conventional-ttail    |
      | e2e-vtail-ruddervator     |
      | e2e-conventional-cross    |
      | e2e-flying-wing           |
      | e2e-flaperon-ttail        |
      | e2e-flap-aileron-ttail    |
      | e2e-stabilator-ttail      |

  Scenario Outline: Strip forces complete without error
    When I run strip forces on "<plane>"
    Then the response status is 200
    And the response contains "strips"

    Examples: <all 7 planes>

  Scenario Outline: Streamlines complete without error
    When I run streamlines on "<plane>"
    Then the response status is 200

    Examples: <all 7 planes>

  Scenario Outline: Flight envelope computes without error
    When I compute the flight envelope for "<plane>"
    Then the response status is 200

    Examples: <all 7 planes>

  Scenario Outline: Stability analysis completes without error
    When I compute stability for "<plane>"
    Then the response status is 200
    And the response contains "neutral_point"
    And the response contains "static_margin"

    Examples: <all 7 planes>

  Scenario Outline: Default OPs generate without error
    When I generate default operating points for "<plane>"
    Then the response status is 200
    And the response contains "operating_points"

    Examples: <all 7 planes>

  Scenario Outline: AVL trim completes without error
    Given operating points exist for "<plane>"
    When I trim the cruise OP with AVL on "<plane>"
    Then the response status is 200

    Examples: <all 7 planes>

  Scenario Outline: AeroBuildup trim completes without error
    Given operating points exist for "<plane>"
    When I trim the cruise OP with AeroBuildup on "<plane>"
    Then the response status is 200

    Examples: <all 7 planes>

  Scenario Outline: Mass sweep computes without error
    When I compute the mass sweep for "<plane>"
    Then the response status is 200

    Examples: <all 7 planes>

  Scenario Outline: CG comparison loads without error
    When I load CG comparison for "<plane>"
    Then the response status is 200

    Examples: <all 7 planes>
```

**Total: 10 scenarios × 7 planes = 70 test cases.**

---

## Step Definitions

Steps call the backend API directly via Playwright's `request` fixture
(no browser interaction needed — this is a smoke test for backend
correctness). Each step:

1. Resolves the plane name to its UUID from a lookup map built during
   seeding
2. POSTs to the relevant endpoint
3. Stores the response for assertion steps

The lookup map is written by the Python seeder as a JSON file
(`e2e/.e2e-planes.json`) mapping plane name → UUID.

---

## Python Seeder: `scripts/seed_e2e_planes.py`

Responsibilities:
1. Create `db/e2e_test.db`
2. Run Alembic migrations against it
3. Insert 7 aeroplanes with wings, cross sections, TEDs, and design
   assumptions using SQLAlchemy models (same pattern as
   `seed_integration_aeroplane` in `conftest.py`)
4. Write `frontend/e2e/.e2e-planes.json` with `{ name: uuid }` map

The seeder reuses the `_add_xsec` helper pattern from `conftest.py`.

Each plane is built by a factory function:
```python
def _make_conventional_ttail(session, aeroplane) -> None:
    """Add main wing (aileron on sec 1) + htail (elevator) + vtail (rudder)."""
    ...

def _make_vtail_ruddervator(session, aeroplane) -> None:
    """Add main wing (aileron on sec 1) + V-tail (ruddervator × 2)."""
    ...
```

---

## Playwright Infrastructure

### `frontend/e2e/global-setup.ts`

```typescript
export default async function globalSetup() {
  // 1. Run seeder
  execSync("poetry run python scripts/seed_e2e_planes.py", { cwd: ROOT });

  // 2. Start backend with test DB
  const proc = spawn("poetry", ["run", "uvicorn", "app.main:app", ...], {
    env: { ...process.env, SQLALCHEMY_DATABASE_URL: "sqlite:///./db/e2e_test.db" },
  });

  // 3. Wait for health check
  await waitForHealthy("http://localhost:8002/health");

  // 4. Store PID for teardown
  writeFileSync(".e2e-backend-pid", String(proc.pid));
}
```

The test backend runs on port **8002** to avoid conflicting with the
dev server on 8001.

### `frontend/e2e/global-teardown.ts`

```typescript
export default async function globalTeardown() {
  // 1. Kill backend
  const pid = readFileSync(".e2e-backend-pid", "utf-8");
  process.kill(Number(pid));

  // 2. Delete test DB
  unlinkSync("db/e2e_test.db");
}
```

### `playwright.config.ts` changes

Add `globalSetup` and `globalTeardown`. Override `API_URL` to point
at port 8002 for the smoke test project. The existing test config
remains unchanged for UI-focused tests.

---

## What This Does NOT Test

- **UI rendering** — these tests hit the API directly, not through
  the browser. A separate test suite (the existing `.feature` files)
  covers UI flows.
- **Math correctness** — we verify response structure, not whether
  α = 5.3° is aerodynamically correct.
- **Creation flows** — wing/segment/TED/spar/servo creation is a
  separate test concern.
- **3D viewer** — WebGL rendering can't be verified via Playwright
  API calls.

## What This DOES Test

- Every analysis endpoint responds without 500 errors for every
  control surface configuration
- AVL, AeroBuildup, and VortexLattice code paths don't crash
- Response bodies contain expected top-level fields
- The full matrix of tail types × control surface roles works
