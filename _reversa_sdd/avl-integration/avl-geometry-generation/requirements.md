# avl-geometry-generation

> Use-case specification, nested under the module
> [`avl-integration`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: avl-integration
> (Geometry emission, R1–R4, Panel spacing, CDCL injection, Stored geometry file
> lifecycle), `_reversa_sdd/data-dictionary.md` §`avl_geometry_files` and
> §AVL geometry dataclasses, `_reversa_sdd/state-machines.md` §9.

## Overview

`avl-geometry-generation` turns an aircraft schema into `.avl` text and manages
the one user-editable copy per aeroplane. It owns the dataclass hierarchy whose
`__repr__` **is** the file format, the airfoil routing rules, the per-section
`CLAF`, the three panel-spacing heuristics, the NeuralFoil-derived CDCL
injection, and the `avl_geometry_files` lifecycle (`is_dirty` /
`is_user_edited`). 🟢

## Responsibilities

- Emit a complete `.avl` file from an aircraft schema through `repr()`. 🟢
- Route each section's airfoil to `NACA`, `AFIL` or inline `AIRFOIL`. 🟢
- Compute `CLAF` per section from the ASB airfoil. 🟢
- Emit `CONTROL` blocks per section, duplicated across the panel strip. 🟢
- Apply the three panel-spacing heuristics when `auto_optimise` is set. 🟢
- Inject 3-point CDCL viscous polars, preserving user-edited values. 🟢
- Store, serve, regenerate and delete the one `.avl` row per aeroplane, and
  decide when the stored copy may be trusted. 🟢

**Explicitly NOT this use case's responsibility:** running AVL and parsing its
output (→ [`../avl-run-and-parse/`](../avl-run-and-parse/requirements.md)), the
control-name decomposition and uniqueness rule
(→ [`../control-surface-naming/`](../control-surface-naming/requirements.md) —
this use case *calls* it), airfoil `.dat` files (→ `airfoil-catalog`), and the
wing geometry itself (→ `wing-design`).

## Business Rules

- **BR-AV1 — `repr()` *is* the file format.** 🟢 `app/avl/geometry.py` is a
  dataclass hierarchy where every `__repr__` emits its AVL block, so
  `repr(AvlGeometryFile(...))` produces the complete `.avl` text. There is no
  separate serialiser and no template — the format cannot drift from the model.

  ```
  AvlGeometryFile(title, mach, symmetry, reference, surfaces[], bodies[], cdp=0.0)
  ├── AvlSymmetry(iy_sym=0, iz_sym=0, z_sym=0.0)
  ├── AvlReference(s_ref, c_ref, b_ref, xyz_ref(3))
  ├── AvlSurface(name, n_chord, c_space, sections[], n_span, s_space,
  │              yduplicate, component, scale, translate, angle,
  │              nowake, noalbe, noload, cdcl)
  │   └── AvlSection(xyz_le(3), chord, ainc=0.0, n_span, s_space,
  │                  airfoil, claf, cdcl, controls[], designs[])
  │       ├── AvlNaca(digits) | AvlAfile(filepath) | AvlAirfoilInline(name, coordinates)
  │       ├── AvlCdcl(cl_min, cd_min, cl_0, cd_0, cl_max, cd_max)
  │       ├── AvlControl(name, gain, xhinge, xyz_hvec(3), sgn_dup)
  │       └── AvlDesign(name, weight)
  └── AvlBody(name, n_body, b_space, bfile, yduplicate, scale, translate)
  ```

  🟢 Never constructed — accepted (`Q-AV-2`, ANSWERED by the maintainer
  2026-08-15). See `BR-AVG3` below.

- **BR-AVG1 — `CDp` is emitted only when non-zero.** 🟢
  `math.isclose(cdp, 0, abs_tol=1e-12)` suppresses the line.
- **BR-AVG2 — `YDUPLICATE 0.0` exactly when the wing is symmetric.** 🟢
  Otherwise the block is omitted entirely (not emitted with a sentinel).
- 🟢 **BR-AVG3 — The `y_root ≥ 0` invariant this document previously
  described as a missing centre-section carry-through is the *opposite*
  defect (`Q-AV-2`, measured against the live database 2026-08-15).** The
  primer requires a fictitious carry-through wing portion when the fuselage is
  omitted (`avl_doc.txt:117-118`), but that case **does not occur here**: 74 of
  82 wing roots sit on `y = 0`, so mirror and original meet with no gap. The 8
  that do not are all deliberately off-centre structural members (struts,
  vertical surfaces) for which `YDUPLICATE` is correct — except the `Wing`
  surface, `y_root = −0.205 m`, which **crosses the centreline**. Mirroring it
  makes it **overlap itself by 0.41 m** — a doubled centre section, not a
  missing one — silently inflating `Sref`, corrupting `CDi` and falsifying the
  reported `e`, with no warning anywhere. Both affected rows have a 4 m chord,
  consistent with an OpenVSP import (ADR 0018) rather than a native RC design.
  **The invariant this module must assert at build time is `y_root ≥ 0` for
  any surface carrying `YDUPLICATE`**, emitting a `DesignWarning` of severity
  `error` (ADR 0020) naming the surface and the overlap width; the primer's
  carry-through rule applies only when a genuine gap exists, which is not this
  codebase's failure mode. Tracked as work (residual register), not implemented
  yet.
- **BR-AV2 — NACA vs AFIL routing accepts integers only (gh-588).** 🟢
  `_NACA_RE = ^naca\s*(\d{4,5})$`. The earlier `\d{4,5}(?:\.\d+)?` over-matched
  and routed `naca23013.5` into an `AvlNaca`, crashing AVL with
  `Read error on line N`. Decimal-bearing names are custom `.dat` files and fall
  through to `_resolve_airfoil_reference` → `AvlAfile`; the last resort is
  `AvlNaca("0012")`.
- **BR-AV3 — `CLAF = 1 + 0.77 · max_thickness`** per section, computed from the
  ASB airfoil, defaulting to `1.0` when the airfoil cannot be built. 🟢
- **BR-AV4 — `CONTROL` blocks are duplicated across the panel strip.** 🟢 Each
  x-section's control(s) are appended to sections `i` **and** `i+1`, replicating
  what AeroSandbox does, so AVL interpolates the deflection across the strip.
- **BR-11 — Control-variable names must be globally unique.** 🟢 Dedup **per
  surface** (repetition inside one surface is legitimate strip duplication), then
  `assert_unique_control_names` **across** surfaces, raising `ValueError` before
  any text is produced. AVL silently collapses identically named `CONTROL`
  variables into a single DOF (avl_doc 778-789), which would couple unrelated
  surfaces with no error anywhere.
- **BR-AV5 — Three spacing heuristics, applied only when `auto_optimise`.** 🟢
  From `SpacingConfig(n_chord=12, c_space=1.0, n_span=20, s_space=1.0,
  auto_optimise=True)`:

  1. **Control surfaces present** → `n_chord = max(n_chord, 16)` (hinge-line
     resolution).
  2. **Unswept** (`atan2(Δx, sqrt(Δy²+Δz²)) < 5°`) **and no centreline break**
     (no interior section at `|y| < 1e-6`) → `s_space = −2.0` (−sine: panels
     concentrated at root and tip, where the induced-drag gradient is steepest).
  3. **Tight section density (gh-590)** →
     `n_span = max(n_span, ceil(span / min_gap) + 2)`. AVL otherwise aborts with
     `Cannot adjust spanwise spacing at section N` /
     `Insufficient number of spanwise vortices`. **Coincident** sections
     (chord/twist discontinuities at the same `y`, gap ≤ 1e-9) are excluded from
     `min_gap`, otherwise `min_gap → 0` drives `n_span → ∞`.

- **BR-AV6 — A user-edited CDCL wins.** 🟢 A section whose `cdcl` is present and
  **not** all-zero is preserved; injection walks surfaces and sections in
  **parallel index order** and mutates in place.
- **BR-AV7 — CDCL is a 3-point polar in AVL's order.** 🟢
  `Re = V · chord / ν(altitude)` (ASB `Atmosphere`); from a NeuralFoil α sweep:
  point 2 at `argmin(CD)` (drag bucket), point 3 at `argmax(CL)` (positive
  stall), point 1 at `argmin(CL)` (negative stall); emitted as
  `CL1 CD1  CL2 CD2  CL3 CD3`.
- **BR-AV8 — The polar cache is keyed on hashable primitives only.** 🟢
  `@lru_cache(maxsize=128)` over airfoil **name**, `Re`, `mach`, α range,
  `model_size`, `n_crit`, `xtr_upper`/`xtr_lower`, `include_360_deg_effects`.
- **BR-AV9 — Non-finite NeuralFoil output yields an all-zero CDCL and a
  warning.** 🟢 Never a fabricated polar (ADR 0012).
- 🟢 **BR-AV10 — A surface/wing count mismatch is an `error`-severity
  `DesignWarning`, not a log line (`Q-AV-5`).** Truncated sections carry **zero
  CDCL — no viscous drag at all**, which is `result_truncated` under
  `P-WARN-0`/ADR 0020. The run must not be presented as a valid viscous result;
  today's silent warn-and-truncate is not compatible with the policy. Not yet
  implemented.
- **BR-AV21 — One row per aeroplane, served only when trustworthy.** 🟢
  `get_user_avl_content` returns the stored content **only** when the row exists
  **and** `is_user_edited` **and not** `is_dirty`; otherwise `None` and the
  caller regenerates.
- 🔴 **BR-AV22 — `is_dirty` is never auto-cleared.** The geometry listeners set
  it; only a user `PUT` or a `POST …/regenerate` resets it.
- 🟡 **BR-AV23 — Asymmetric consultation.** `analyze_wing` and the single-wing
  strip-force path prune the airplane to one wing and therefore **never**
  consult the stored file, while `analyze_airplane`, `trim_with_avl` and the
  full-airplane strip-force path do.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Emit a complete `.avl` file via `repr()` | Must | AVL loads it without a `Read error on line N` |
| RF-02 | Emit `CDp` only when non-zero | Should | `cdp = 0.0` produces no `CDp` line |
| RF-03 | Emit `YDUPLICATE 0.0` exactly for symmetric wings | Must | An asymmetric surface has no `YDUPLICATE` block at all |
| RF-04 | Route integer NACA names to `NACA`, everything else to `AFIL` | Must | `naca23013.5` → `AFIL`; `naca2412` → `NACA 2412` |
| RF-05 | Fall back to `NACA 0012` when nothing resolves | Should | A missing `.dat` yields `NACA 0012`, not a crash |
| RF-06 | Compute `CLAF = 1 + 0.77·max_thickness`, default `1.0` | Should | A 12 % section yields `CLAF 1.0924` |
| RF-07 | Duplicate each control onto sections `i` and `i+1` | Must | A one-segment control appears in two `SECTION` blocks |
| RF-08 | Dedup per surface and assert uniqueness across surfaces | Must | A cross-surface collision raises **before** any text exists |
| RF-09 | Raise `n_chord` to ≥ 16 when controls are present | Should | A flapped wing emits `n_chord ≥ 16` |
| RF-10 | Set `s_space = −2.0` for unswept surfaces without a centreline break | Should | Adding an interior section at `y = 0` restores `s_space = 1.0` |
| RF-11 | Raise `n_span` to `ceil(span/min_gap)+2`, excluding coincident sections | Must | Two sections 2 mm apart raise `n_span`; two coincident ones do not |
| RF-12 | Honour `auto_optimise = False` | Must | All three heuristics are skipped; the config values pass through |
| RF-13 | Preserve a non-zero user-edited CDCL | Must | The hand-written block survives byte-identically |
| RF-14 | Compute a 3-point CDCL in AVL's order | Should | Point 2 is at `argmin(CD)`, point 3 at `argmax(CL)`, point 1 at `argmin(CL)` |
| RF-15 | Emit an all-zero CDCL and warn on non-finite output | Must | NaN never reaches the file |
| RF-16 | Cache polars on primitives, `maxsize = 128` | Should | Two identical requests issue one NeuralFoil call |
| RF-17 | Store one row per aeroplane | Must | A second save updates the same row |
| RF-18 | Serve stored content only when user-edited and not dirty | Must | A dirty row causes regeneration |
| RF-19 | Generate on the fly when no row exists, without persisting | Must | `GET` on a fresh aeroplane creates no row |
| RF-20 | `PUT` sets `is_user_edited = True` and `is_dirty = False` | Must | A saved file is immediately trusted |
| RF-21 | `POST …/regenerate` deletes the row and returns fresh content | Must | The row is gone afterwards |
| RF-22 | `DELETE` removes the row, 404 when absent, 204 on success | Must | Matches [`../contracts.md`](../contracts.md) |
| RF-23 | Mark the row dirty on any geometry write | Must | A wing x-section update sets `is_dirty` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Maintainability | The file format lives in one dataclass hierarchy; there is no template that can drift from the model | `app/avl/geometry.py` | 🟢 |
| Correctness | Control names are asserted unique **before** the file is written, because AVL fails silently on a collision | `assert_unique_control_names` | 🟢 |
| Correctness | `n_span` is raised pre-emptively to avoid AVL's spanwise-vortex abort | `spacing.py:43-68` (gh-590) | 🟢 |
| Correctness | Coincident sections are excluded from `min_gap`, bounding `n_span` | same | 🟢 |
| Performance | CDCL polars are memoised (`lru_cache(maxsize=128)`) on primitive keys | `neuralfoil_cdcl_service.py:25` | 🟢 |
| Robustness | Non-finite NeuralFoil output becomes zeros plus a warning, never a fabricated polar | `neuralfoil_cdcl_service` | 🟢 |
| Robustness | An unresolvable airfoil degrades to `NACA 0012` rather than failing the build | `_resolve_airfoil_reference` | 🟢 |
| Testability | Emission, routing, spacing and CDCL are all binary-free — none of this needs AVL installed | module structure | 🟢 |
| Auditability | `is_dirty` / `is_user_edited` are returned to the client, so staleness is visible | `AvlGeometryResponse` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: File emission

  Scenario: repr produces a loadable file
    Given an aircraft with two surfaces and four sections
    When I take repr of the geometry object
    Then AVL loads the text without a read error

  Scenario: A symmetric wing emits YDUPLICATE
    Given a wing whose symmetric flag is true
    Then its SURFACE block contains YDUPLICATE with value 0.0

  Scenario: An asymmetric wing omits the block entirely
    Given a wing whose symmetric flag is false
    Then no YDUPLICATE line appears in its SURFACE block

  Scenario: Zero parasite drag emits no CDp line
    Given cdp equal to 0.0
    Then the file contains no CDp line

Feature: Airfoil routing

  Scenario: An integer NACA name becomes a NACA block
    Given a section whose airfoil is "naca2412"
    Then a NACA block with digits 2412 is emitted

  Scenario: A decimal-bearing name becomes an AFIL block
    Given a section whose airfoil is "naca23013.5"
    Then an AFIL block referencing a dat file is emitted
    And no NACA block is emitted
    # gh-588 — the old regex crashed AVL with "Read error on line N"

  Scenario: An unresolvable airfoil falls back
    Given a section whose airfoil file cannot be found
    Then a NACA block with digits 0012 is emitted
    And the build does not raise

Feature: Controls

  Scenario: A control is duplicated across the strip
    Given a control on cross-section i
    Then its CONTROL block appears in sections i and i+1

  Scenario: A cross-surface collision is refused
    Given two surfaces whose controls resolve to the same name
    When the geometry file is built
    Then a ValueError is raised
    And no file text is produced

  Scenario: Repetition inside one surface is allowed
    Given the same control name in several sections of one surface
    Then the build succeeds

Feature: Panel spacing

  Scenario: Controls raise the chordwise count
    Given a surface carrying at least one control
    Then n_chord is at least 16

  Scenario: An unswept clean wing gets minus-sine spacing
    Given a surface with sweep below 5 degrees and no interior section at y = 0
    Then s_space is -2.0

  Scenario: A centreline break keeps cosine spacing
    Given the same surface with an interior section at y = 0
    Then s_space stays 1.0

  Scenario: Tight sections raise the spanwise count
    Given two sections 2 mm apart on a 1 m span
    Then n_span is at least ceil(span / min_gap) + 2

  Scenario: Coincident sections do not explode n_span
    Given two sections at the same y, a chord discontinuity
    Then that pair is excluded from min_gap
    And n_span stays finite

  Scenario: Auto-optimisation can be turned off
    Given auto_optimise set to false
    Then n_chord, s_space and n_span are exactly the configured values

Feature: CDCL

  Scenario: A user-edited block is preserved
    Given a section whose CDCL is present and not all zero
    When injection runs
    Then the section keeps its values byte-identically

  Scenario: An all-zero block is replaced
    Given a section whose CDCL is all zeros
    Then injection overwrites it with a computed polar

  Scenario: Non-finite output yields zeros
    Given a NeuralFoil sweep containing NaN
    Then the emitted CDCL is all zeros
    And a warning is logged

  Scenario: The polar is cached
    Given two sections with the same airfoil, Reynolds number and configuration
    Then NeuralFoil is called once

Feature: Stored geometry

  Scenario: Content is served only when trustworthy
    Given a row with is_user_edited true and is_dirty false
    Then get_user_avl_content returns it

  Scenario: A dirty row is not served
    Given a row with is_user_edited true and is_dirty true
    Then get_user_avl_content returns nothing
    And the caller regenerates

  Scenario: A generated row is not served either
    Given a row with is_user_edited false
    Then get_user_avl_content returns nothing

  Scenario: Reading without a row does not persist
    Given an aeroplane with no stored geometry
    When I GET the avl geometry
    Then content is generated and returned
    And no row is created

  Scenario: Saving marks the file trusted
    When I PUT user content
    Then is_user_edited becomes true
    And is_dirty becomes false

  Scenario: A geometry edit dirties the row
    Given a stored row
    When a wing cross-section is updated
    Then is_dirty becomes true

  Scenario: Regeneration deletes the row
    When I POST to the regenerate route
    Then the row is removed
    And fresh content is returned
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Emission + NACA/AFIL routing (RF-01, RF-04) | Must | A malformed file crashes AVL with an unhelpful message and no line context |
| Control emission + uniqueness (RF-07, RF-08) | Must | AVL fails **silently** on a collision — the worst failure mode in the module |
| `n_span` safety margin (RF-11) | Must | Without it AVL aborts outright on tightly spaced sections (gh-590) |
| `YDUPLICATE` correctness (RF-03) | Must | Wrong here means the wrong number of half-wings |
| Stored-file lifecycle + trust rule (RF-17…RF-23) | Must | The user-editable escape hatch; the trust rule is what stops a stale file being flown |
| CDCL injection (RF-13…RF-16) | Should | AVL's viscous advantage, but every path works without it |
| Spacing heuristics 1 and 2 (RF-09, RF-10) | Should | Accuracy improvements, not correctness gates |
| `auto_optimise = False` (RF-12) | Should | The escape hatch for a user who knows better |
| `CLAF` (RF-06) | Should | A refinement with a documented default |
| `CDp` suppression (RF-02) | Should | File hygiene |
| Airfoil fallback (RF-05) | Should | Keeps a partly-configured aircraft analysable |
| Auto-clearing `is_dirty` after a successful regenerate | **Should (open)** | 🔴 today only a user action clears it |
| Emitting a `BODY` block for fuselages | Won't (today) | 🔴 the emitter exists; nothing constructs one, so AVL runs are wing-only |
| Emitting `.mass` / `.run` files | Won't | Never produced; mass and run cases go through keystrokes |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/avl/geometry.py` | the whole dataclass hierarchy and every `__repr__` | 🟢 |
| `app/avl/spacing.py` | `optimise_surface_spacing` (`:71-106`), unswept threshold (`:17`), `n_span` margin (`:43-68`), `s_space = −2.0` (`:101`), `n_chord` floor (`:97`) | 🟢 |
| `app/services/avl_geometry_service.py` | `build_avl_geometry_file`, `_NACA_RE` (`:52`), `_resolve_airfoil_reference`, `CLAF` (`:102`), `_build_controls_for_wing`, `inject_cdcl`, `get_user_avl_content`, stored-file CRUD | 🟢 |
| `app/services/neuralfoil_cdcl_service.py` | `compute_cdcl`, `compute_reynolds_number`, `lru_cache` (`:25`) | 🟢 |
| `app/services/control_surface_mixing.py` | `axis_control_name`, `assert_unique_control_names` (`:149-164`) | 🟢 (owned by [`../control-surface-naming/`](../control-surface-naming/requirements.md)) |
| `app/models/avl_geometry_file.py` | `AvlGeometryFileModel`, `uq_avl_geometry_files_aeroplane_id` | 🟢 |
| `app/models/avl_geometry_events.py` | dirty listeners (🔴 duplicate registration) | 🔴 |
| `app/api/v2/endpoints/aeroplane/avl_geometry.py` | `get_avl_geometry`, `save_avl_geometry`, `regenerate_avl_geometry`, `delete_avl_geometry` | 🟢 |
| `app/schemas/aeroanalysisschema.py` | `SpacingConfig`, `CdclConfig` (`:187-219`) | 🟢 |
