# spar-sizing

> Use-case specification, nested under the module [`wing-design`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: wing-design
> (Structural pipeline, Stages 1–4), `_reversa_sdd/data-dictionary.md`
> §Module: wing-design.

## Overview

`spar-sizing` turns a bending-moment distribution into a **buildable spar
layout**: it sizes each station by required section modulus, samples the wing's
containment band from section geometry, then solves a telescoping run of
straight pieces per half-span with joint types, bore diameters, utilisation and
an honest feasibility verdict. It is structural-safety output consumed directly
by the person cutting carbon tube. 🟢

## Responsibilities

- Compute the required section modulus from a design bending moment, and invert
  it into a physical dimension for each of the four spar shapes. 🟢
- Reject a non-positive allowable stress at the formula rather than dividing by
  zero. 🟢
- Sample station data (chord, thickness, containment band, design moment) across
  the half-span, nudging the pinched root slice off `y_span = 0`. 🟢
- Keep a **computed** rear spar clear of the movable surface's hinge line. 🟢
  *(Marked 🟢 before gh-1096 on the strength of the function alone — no caller
  reached it. A definition read in isolation is not confirmed behaviour; the
  call graph is part of the evidence.)*
- Solve a buildable layout per half-span: greedy straight-piece fit, telescoping
  runs, front/rear joint type, bore, and utilisation. 🟢
- Report infeasibility honestly — never clamp, never silently shrink. 🟢
- Emit **no piece** for a negligible-load tip and report where the spar stops. 🟢
- Provide the `(y/span, x/c)` section-geometry seam in an analytic default mode
  and an optional solid-slicing mode. 🟢
- Persist the solved plan back onto the wing's spars. 🟢

**Explicitly NOT this use case's responsibility:** spar *CRUD* and the mm↔m
conversion boundary (→ [`../cross-section-crud/`](../cross-section-crud/requirements.md)),
the aerodynamic load calculation that produces `moment_fn` (→ `aero-analysis`),
building the CAD solid (→ `cad-generation`), and the frozen topology classes
(→ `cad-designer-topology`, read-only per ADR 0002).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md).

- **BR-W16 — The structural model is a two-spar wing whose skin carries no load.** 🟢
  *(module-level BR-W16; this use case is its owner.)* **Ist** — maintainer-stated
  2026-08-17, and the reason every rule below is shaped the way it is. It holds for
  **both** manufacturing routes.

  | member | carries |
  |---|---|
  | front spar | the primary **bending** moment, alone |
  | rear spar | the **torsion** couple, reacted over the front–rear chordwise spacing |
  | skin — printed shell *or* film covering | aerodynamic shape and air-load transfer — **not** a structural member |
  | rib (built-up wing) | transfers the local air load **into** the spar — carries none of it onward |

  **Printed wing.** The shell is printed around the spars and deliberately **not
  bonded** to them, so the two can move relative to each other. There is no
  adhesive joint to size between spar and shell.

  **Built-up (wooden-rib) wing.** The ribs are fixed to the spar, and the wing is
  covered with a **film that conforms to the load** rather than resisting it. A rib
  is a shape-holder and a transfer path into the spar; it is not sized for load
  itself. This is the structural reason behind the part-count rule that makes ribs a
  **DXF cutting file rather than a modelled component** ([`../requirements.md`](../requirements.md),
  *minimise part count*).

  **The tip is always attached to the spar.** Depending on the planform the wing end
  is either a **rib** — which must be joined to the rest of the wing, so the spar runs
  through it — or a **wingtip / winglet**, printed as a shell or sanded from balsa,
  which is **fastened to** the spar. A fully printed wing may have a **spar-less tip
  segment**, and that is a *declared construction property, not a strength result*:
  `wing_segment_type == 'tip'` is explicitly exempt from `VaseModeWingCreator`'s rule
  that every segment carries at least one spar, because a tip cap is a wing-end cap
  and not a structural bay (gh-361, `VaseModeWingCreator.py:703-735`).
  **Where the spar ends is therefore topology, not a computation** — see BR-W10.

  Two consequences that are load-bearing for the whole sizing method:

  **Neither route has a stressed skin.** Shell and covering contribute nothing to
  bending stiffness, so the spar is sized as if it stood alone — which it does. A
  conventional built-up wing lets a bonded **D-box** carry torsion and part of the
  bending; **neither route here builds one**, and a film covering cannot form a
  torsion box at all.

  **Torsion is therefore always the second spar's job.** This is why
  `_make_rear_moment_fn` sizes the rear member from `T(y)/spacing` rather than from
  the bending moment (gh-1038): with no torsion-carrying skin, the front–rear pair
  **is** the torsion structure. Were the skin bonded and stressed, that model would
  be wrong and the front spar over-sized.

  > Recorded because the assumption was previously implicit in the code and
  > nowhere in the specification, while every spar result depends on it. A reader
  > who assumed a stressed-skin wing would judge this method too conservative;
  > one who assumed a bonded shell would look for a joint that does not exist.
  > **Both misreadings are already in the tree**: the no-spar tip region is justified
  > in four places — one of them the *public* API schema — by *"the D-box skin + ribs
  > carry the tip"* (**gh-1136**). No behaviour depends on it, but removing the wrong
  > reason exposes a real question: a printed shell can carry a near-zero tip moment
  > incidentally, a film covering cannot, so the no-spar region may be
  > **printed-wing-only**. 🔴 **Soll** — to be answered in this rule before the rib
  > Creator lands (gh-1136 Part B).

- **BR-W17 — The margin is a two-sided partial-factor format, and the total is hidden.**
  🟡 *(module-level BR-W17; this use case is its owner.)* **Ist** — established with the
  domain experts 2026-08-17, recorded here because the code carries the factors without
  naming what each one guards against.

  ```
  M_break = M(1g) · n_limit · j · k        with  j = 1.5  and  k = σ-record's SF
  ```

  | factor | sits on | guards against |
  |---|---|---|
  | **`j = 1.5`** (`safety_factor_j`) | the **load** | the service load being exceeded — gust, misjudgement, more stick than planned. *Sicherheitszahl*, hence the German-notation name `j`. Limit load → ultimate load: nothing deforms permanently below limit, nothing breaks below ultimate. CS-23.303 / CS-25.303; Sadraey Eq. (10.4). |
  | **`k`** (`sigma_allow_sf` in the material record) | the **resistance** | the datasheet strength not being what the part delivers — fibre waviness, voids, moisture, scatter |

  `j` asks *how much more load than planned*; `k` asks *how much less strength than
  promised*. **They are not double-counting.** In CS-23/CS-25 the 1.5 sits on top of an
  **A- or B-basis allowable** — a statistical lower bound from a coupon programme, so
  the statistics live *inside* `σ_allow` and are invisible in the 1.5. No one sizing a
  0.5–15 kg airframe will ever have A/B-basis allowables; **`k` is the substitute for the
  statistical basis this class cannot produce**, not extra padding.

  ⚠️ **Three interface defects follow from this and are not yet fixed** (→ gh-1079):

  1. **`g_limit` is not a load factor as consumed.** It is multiplied by `j · k` ≈ 3.75
     before it means anything, so a field named `g_limit = 3` describes a wing that
     breaks at **11.3 g**. Every reader misreads it (ADR 0019, ADR 0022).
  2. **`j` is unreadable without German strength-of-materials literature**, and the
     schema defines it circularly: *"Safety factor applied to M_design = |M|·g_limit·j."*
  3. **`k` is a property of the supplier record, not a design choice** — it is
     pre-divided into `allowable_bending_stress_mpa`, so two snapshots with different
     SF would not be noticed. (The current data *is* process-differentiated: 2.5 for
     roll-wrapped twill, 2.0 for pultruded — with one pultruded entry inconsistently
     at 2.5.)

  **`n_break = n_limit · j · k` is the number to display.** It is the language RC
  practice reasons in — *"this wing takes 15 g"* — and the only quantity in the chain
  that can be verified on a bench: invert the wing, support at the joiner, load to
  `n_break × m_total`. Both domain experts arrived at this independently.

- **BR-W18 — Sizing is strength-only *by decision*; stiffness stays with the designer.** 🟢
  *(module-level BR-W18; this use case is its owner.)* **Ist** — maintainer decision,
  2026-08-17. The chain sizes from `erf_W = M_design / σ_allow` (BR-W5): a section that
  does not **break**. Deflection is nowhere computed, and that is a **deliberate scope
  boundary, not a gap**.

  **What the boundary buys.** No E-modulus is required in the material record —
  `allowable_bending_stress_mpa` and density remain the only structural properties in
  the contract (`app/schemas/spar_sizing.py:114-115`), and the COTS carbon-tube
  snapshots need no new field. Stiffness is exercised where the maintainer already
  exercises it: in choosing the tube.

  **What the boundary costs — state it, don't paper over it.**

  - A tube can pass sizing and still be unacceptably soft. The tool will not say so.
  - **1 g acts at V = 0.** The wing carries its own weight standing still, producing no
    lift — a case an aero-integrated `M(y)` cannot contain, because it comes from a lift
    distribution. It is out of scope, not merely unmodelled.
  - Flutter is outside the scope entirely.
  - Therefore **`feasible = True` means "does not break", never "stiff enough"**, and
    `n_break` is a strength number. Anyone wording these for the UI must not let them
    read as a verdict on the wing (the app also serves designers who are not the
    maintainer — see the module's audience note).

  **Adding a deflection limit or a minimum-`EI` floor is a new decision**, recorded here
  or in an ADR — not an enhancement an implementer may fold into a spar ticket.

- **BR-W5 — Section-modulus sizing is the strength law (gh-1008).** 🟢
  *(module-level BR-W5; this use case is its owner.)* Reference: *kirch
  Hauptholm*. Units are fixed and load-bearing: `M` in **N·m**, `σ` in **MPa**
  (= N/mm²), dimensions in **mm**, `W` in **mm³**, mass in **kg**. The factor
  `1000` in `erf_W` is exactly the N·m → N·mm conversion.

  ```
  M_design(y) = |M(y)| · g_limit · j                    (spar_sizing.py:9-13, docstring)
  erf_W       = M_design · 1000 / σ_allow               (required_section_modulus, l.78-88)
  outer(y)    = chord(y) · (t/c)(y) · packing_factor    (l.13)
  ```

  Section moduli (mm³):

  ```
  rectangular   W = b · h² / 6                          (l.40-45)
  capped (I/C)  W = b · (H³ − h³) / (6 · H)             (l.48-54)
  solid rod     W = d³ / 10                             (l.57-62)
  tube          W = π · (Da⁴ − Di⁴) / (32 · Da)         (l.65-70)
  ```

  Closed-form inverses (`solve_dimension`, l.96+):

  ```
  tube          Di = (Da⁴ − 32 · erf_W · Da / π) ^ (1/4)   (l.137-146)
  rod           d  = (10 · erf_W) ^ (1/3)                  (l.159)
  rectangular   b  = 6 · erf_W / h²                        (l.182)
  capped        h  = (H³ − 6 · H · erf_W / b) ^ (1/3)      (l.196-208)
  ```

- **BR-W6 — `σ_allow ≤ 0` raises.** 🟢 The material schema permits `0`, so the
  division is protected at the formula itself and raises `ValueError`
  (`app/services/spar_sizing.py:86-87`). Fallback thickness ratio when airfoil
  data is unavailable: `_TC_FALLBACK = 0.12` (l.32).
- **BR-W7 — The root slice is nudged off `y_span = 0`.** 🟢 `_ROOT_EPS = 1e-3`.
  The `y_span = 0` slice is a pinched, zero-thickness section on a real loft and
  would poison the governing max-moment root station (gh-1037 #4). Station
  sampling therefore uses `y_spans = linspace(0, 1, n_span)` with
  `y_spans[0] → _ROOT_EPS`.
- **BR-W8 — A computed rear spar must clear the movable surface (gh-1059, gh-1096).** 🟢

  ```
  rear_spar_x_c_with_clearance(requested, hinge_x_c, clearance = 0.03):
      if hinge_x_c is None:
          return requested
      limit = hinge_x_c − clearance
      if limit < 0.05:                      # LE floor and clearance conflict
          raise RearSparClearanceInfeasible # reported, never clamped (RF-SP-20)
      return min(requested, limit)
  ```

  **The clearance line wins over the LE floor.** Until gh-1096 the floor was
  applied last — `max( min(requested, hinge_x_c − 0.03), 0.05 )` — so a hinge
  near the LE produced a spar *behind* it, inside the movable surface, and
  returned it as a valid answer. `Q-WD-8` ② records that order as a confirmed
  defect; when the two cannot both be honoured the layout is infeasible.

  **This guard was unreachable in production until gh-1096.** The function and
  its `build_stations_from_geometry` seam were correct from gh-1059, but
  `spar_plan_service` called the station builder without
  `control_surface_hinge_x_c`, so it defaulted to `None` and every production
  path skipped the guard. The wing's binding hinge is the **most forward** one
  across its cross-sections (`_wing_hinge_x_c`) — a computed rear spar must
  clear every control surface, not just the first. The **front** spar is
  deliberately left unconstrained.

  `_REAR_CLEARANCE_FRACTION = 0.03`, `_MIN_REAR_X_C = 0.05`
  (`cad_designer/airplane/geometry/spar_solver.py:181-221`). The guard is
  explicitly documented as applying only to **computed** spars — a designer may
  still place a reinforcing spar inside a control surface manually.
- **BR-W9 — Utilisation is reported honestly and may exceed 1.0.** 🟢

  ```
  utilisation = od / max(tightest_band, 1e-6)
  feasible    = od ≤ tightest_band
  ```

  The infeasibility message names the governing station and suggests a capped or
  box spar (`spar_solver.py:490-529`, `_piece_from_run_with_od`). No silent
  clamping. Consistent with ADR 0012.
- **BR-W10 — A negligible-load tip produces no spar (gh-1076).** 🟢
  `NEGLIGIBLE_OD_FLOOR_MM = 1.0`. A tip station whose required OD falls below
  1 mm yields **no piece**, and the region is reported as `front_no_spar_from_y`
  / `rear_no_spar_from_y` rather than a degenerate Ø≈0 tube
  (`spar_solver.py:44-53, 438-457`).
  🔴 **Soll (gh-1136) — the rule has the wrong authority.** Where the spar ends is a
  construction property (`wing_segment_type == 'tip'`, BR-W16), not something to infer
  from a strength threshold. Three findings:

  1. The reason given in four places, one of them the **public** schema
     (`app/schemas/spar_plan.py:309`), is a **D-box that neither route builds**.
  2. **The reported region is a sampling artefact — measured, not inferred.** 🟢
     Stations are `linspace(0, 1, n_span)` (`spar_solver.py:745`), `n_span = 6` by
     default, caller-settable 2–200 (`app/schemas/spar_plan.py:107`). Swept over
     `ehawk_main_wing` (750 mm half-span, 12 segments) with an elliptic-lift-integrated
     `M(y)` at `M_root ∈ {30, 8, 2}` N·m:

     | `n_span` | 6 | 8 | 12 | 16 | 25 | 50 |
     |---|---|---|---|---|---|---|
     | region starts at | 80.0 % | 85.7 % | 90.9 % | 93.3 % | 95.8 % | 98.0 % |
     | `(n−2)/(n−1)` | 80.0 % | 85.7 % | 90.9 % | 93.3 % | 95.8 % | 98.0 % |

     An exact match at every resolution, and **identical for all three load levels** —
     the reported boundary is a function of `n_span` alone, not of the wing or the load.

     Worse, on `configurator_wing` (3 equal segments) the region's **existence** flips:
     at `n_span = 6` it appears at 80 % for `M_root = 30` and `2` but not for `8`, and
     from `n_span = 8` upward it disappears entirely. Same wing, same load — refining a
     numerical parameter turns *"the outer 20 % needs no spar"* into *"the spar runs to
     the tip"*, non-monotonically in both `n_span` and load.

     The mechanism is not the one first assumed. The tip station at `y_span = 1.0` does
     always carry `required_od = 0` (measured), but a *piece* takes its **run's governing
     (most-inboard) OD** (`plan_spar`, l.403), so a sub-floor tip station alone drops
     nothing — on a single-run wing (`single_segment_flat`) no region ever appears at any
     resolution or load. The region emerges only when run-splitting puts a whole outer run
     below the floor, and **run boundaries move with the station grid**.

     **Collision with topology, concretely.** `ehawk_main_wing`'s tip segments begin at
     705 mm (94 %). At the default `n_span = 6` the plan reports no spar from **600 mm
     (80 %)** — declaring ~105 mm of *structural* segments spar-free, which is exactly
     what gh-361 forbids at construction time.
  3. The floor keeps one legitimate job: a **feasibility check** — *"no orderable
     section this small"* — never the decision of where the spar stops.
- **BR-W11 — Single-half surfaces force a continuous front joint (gh-1091).** 🟢
  A vertical stabiliser has one half, so `_inboard_collinear` must not index
  into the empty half; the front joint is forced to `"continuous"`.
- **BR-W12 — The spar solver is deliberately CAD-free.** 🟢 Every branch runs on
  the CI fast tier with hand-built `StationData` — there is **no CadQuery import
  in the decision logic** (`spar_solver.py:1-24`). The CAD dependency is
  isolated in the `SectionGeometry` seam (BR-W13).
- **BR-W13 — Section geometry has an analytic fast path (gh-1046).** 🟢
  `SectionGeometry` recovers `(y/span, x/c)` in `"analytic"` mode (the default —
  blends segment airfoils via `WingConfiguration.get_points_on_surface`, builds
  no solid) or `"solid"` mode (builds the RIGHT-half loft once via
  `WingLoftCreator` and slices it; `sample` groups requests by `y_span` so each
  plane is cut once). `points_per_edge` is clamped to `[8, 4096]`. The analytic
  path exists to avoid the documented **~13 s** `WingLoftCreator` bottleneck.
  Raises `SectionGeometryUnavailableError` when CadQuery is absent
  (`cad_designer/airplane/geometry/section_geometry.py:160-219`).
- **BR-S1 — Sizing parameters have fixed defaults and gated fields.** 🟢
  *(refines BR-W5; from `app/schemas/spar_sizing.py:12-51`.)*
  `safety_factor_j = 1.5` (`> 0`), `packing_factor = 0.8` (`0 < x ≤ 1`),
  `shape ∈ {tube, rod, rectangular, capped}`, `cap_width_mm` **required only
  for** `capped`, and `material_id` must point to a `Component` of type
  `material` carrying `allowable_bending_stress_mpa`. Station-sampling defaults:
  `n_span = 6`, `g_limit = 3.0`, `j = 1.5`.
- **BR-S2 — The containment band is derived from the packing factor.** 🟢

  ```
  clr     = (1 − packing_factor) / 2 · thickness
  band_lo = bottom_z + clr
  band_hi = top_z    − clr
  x_c     = requested x/c, else the section's max-thickness location
  ```

  (`spar_solver.build_stations_from_geometry`, l.681-746.)
- **BR-S3 — The bore is reconstructed from the governing rod OD.** 🟢 `_bore_for`
  recovers `erf_W` via `required_section_modulus_from_od(od) = od³ / 10` and
  solves the tube path; when strength wants a solid it falls back to
  `wall_factor = 0.6` of the OD (`spar_solver.py:460-487`).
  `telescope_clearance_mm = 0.5` is the radial slip-fit gap between nested
  tubes.
- **BR-S4 — Joint type is decided per half-span pair.** 🟢
  **Front:** `_inboard_collinear` compares the two halves' root `center_z`
  within `tol_mm = 5.0`; equal → `"continuous"`, otherwise
  `"reinforcement+joiner"` with a generated reinforcement piece. A single-half
  surface is forced to `"continuous"` (BR-W11).
  **Rear:** `"continuous"` when a straight collinear rod through `y = 0` stays
  inside the band on both halves, otherwise `"bent-pin"`.

## Functional Requirements

> The `RF-xx` ids refine the module-level requirements in
> [`../requirements.md`](../requirements.md).

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-15 | Size a spar by required section modulus for the four shapes (tube, rod, rectangular, capped) | Must | Given `M`, `σ_allow`, `g_limit`, `j`, the returned dimension reproduces the closed-form inverse in [`design.md`](design.md) exactly |
| RF-16 | Reject `σ_allow ≤ 0` | Must | `ValueError` is raised rather than a division by zero, for every shape |
| RF-17 | Produce a buildable spar plan per half-span with telescoping runs, joint type, utilisation and feasibility | Must | An over-loaded root reports `feasible = false`, `utilisation > 1.0`, names the governing station and suggests a capped/box spar |
| RF-18 | Emit no spar piece for a negligible-load tip and report the region instead | Must | A tip whose required OD < 1.0 mm yields no piece and sets `front_no_spar_from_y` |
| RF-19 | Keep a computed rear spar clear of the hinge line | Must | With `hinge_x_c = 0.72`, the rear spar `x/c` is `≤ 0.69` and `≥ 0.05` |
| RF-23 | Sample section geometry `(y/span, x/c)` analytically by default, with a solid-slicing mode available | Should | `mode="analytic"` returns points without importing CadQuery; `points_per_edge = 5` is clamped to 8 |
| RF-S1 | Sample stations across the half-span with the root nudged off zero | Must | `n_span = 6` yields 6 stations; `y_spans[0] == 1e-3`, not `0.0` |
| RF-S2 | Derive the containment band from the packing factor | Must | With `packing_factor = 0.8` and thickness `t`, `band_hi − band_lo == 0.8 · t` to floating-point tolerance |
| RF-S3 | Fall back to `t/c = 0.12` when airfoil thickness data is unavailable | Should | With no airfoil data, sizing still returns a dimension computed from `_TC_FALLBACK` |
| RF-S4 | Compute the bore from the governing rod OD, falling back to a wall factor | Should | A station whose strength demands a solid returns a bore of `0.6 × od`; otherwise the tube inverse is used |
| RF-S5 | Decide the front joint from the two halves' root `center_z` within 5 mm | Must | Equal roots → `"continuous"`; a 20 mm offset → `"reinforcement+joiner"` plus a reinforcement piece |
| RF-S6 | Force a continuous front joint on a single-half surface | Must | A vertical stabiliser plan returns `"continuous"` and does not raise on the empty half |
| RF-S7 | Decide the rear joint as continuous or bent-pin | Must | A collinear rod through `y = 0` that stays inside both bands → `"continuous"`; otherwise `"bent-pin"` |
| RF-S8 | Persist the solved plan back onto the wing's spars | Should | After a solve, the wing's spar rows carry the solved origins/vectors and survive the next read (see BR-W3 in `cross-section-crud`) |
| RF-S9 | Run every solver branch without a geometry kernel | Must | The full solver test suite passes on the CI fast tier with hand-built `StationData` and no CadQuery installed |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Infeasible spar layouts are reported, never clamped | `spar_solver.py:490-529` | 🟢 |
| Correctness | The strength division is protected at the formula, because the material schema admits `σ_allow = 0` | `spar_sizing.py:86-87` | 🟢 |
| Correctness | The root station is sampled off `y_span = 0`, because the pinched zero-thickness slice would poison the governing max-moment station | `spar_solver.py` (`_ROOT_EPS = 1e-3`), gh-1037 #4 | 🟢 |
| Correctness | A negligible-load tip yields no piece rather than a degenerate Ø≈0 tube | `spar_solver.py:44-53, 438-457` | 🟢 |
| Testability | The solver contains no CAD import, so every decision branch is exercisable on the CI fast tier | `spar_solver.py:1-24` | 🟢 |
| Performance | Section sampling defaults to an analytic path to avoid a documented ~13 s loft build | `section_geometry.py:160-219` | 🟢 |
| Performance | Solid-mode sampling groups requests by `y_span` so each cutting plane is used once | `section_geometry.py` (`sample`) | 🟢 |
| Performance | `points_per_edge` is clamped to `[8, 4096]` to bound sampling cost | `section_geometry.py` | 🟢 |
| Portability | The geometry seam raises a named `SectionGeometryUnavailableError` when CadQuery is absent, rather than an opaque `ImportError` | `section_geometry.py:181-184` (ADR 0017) | 🟢 |
| Safety | The rear-spar clearance guard applies to computed spars only, leaving manual reinforcing spars possible | `spar_solver.py:181-221` (gh-1059) | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Section-modulus sizing

  Scenario: A rod is sized from the required section modulus
    Given M = 40 N·m, sigma_allow = 300 MPa, g_limit = 3.0 and j = 1.5
    When I size a "rod" spar
    Then required W equals |M| * g_limit * j * 1000 / sigma_allow
    And the diameter equals (10 * W) ** (1/3)

  Scenario: A tube bore is solved from the outer diameter
    Given an outer diameter Da and a required section modulus erf_W
    When I size a "tube" spar
    Then the inner diameter equals (Da**4 - 32 * erf_W * Da / pi) ** (1/4)

  Scenario: A capped spar is solved for its inner height
    Given an outer height H, a cap width b and a required section modulus erf_W
    When I size a "capped" spar
    Then the inner height equals (H**3 - 6 * H * erf_W / b) ** (1/3)

  Scenario: Zero allowable stress is rejected
    Given a material whose allowable_bending_stress_mpa is 0
    When I request a spar size
    Then a ValueError is raised
    And no division by zero occurs

  Scenario: Missing airfoil data falls back to a 12 percent thickness ratio
    Given a station with no resolvable airfoil thickness
    When I size a spar
    Then the thickness ratio used is 0.12
    And a dimension is still returned

Feature: Station sampling

  Scenario: The root station is nudged off zero
    Given n_span = 6
    When stations are sampled from root to tip
    Then 6 stations are produced
    And the first station's y_span is 1e-3, not 0.0

  Scenario: The containment band follows the packing factor
    Given a station of thickness t and packing_factor 0.8
    When the band is computed
    Then band_hi minus band_lo equals 0.8 * t
    And the clearance on each side equals (1 - 0.8) / 2 * t

Feature: Rear-spar hinge clearance

  Scenario: A computed rear spar clears the hinge
    Given a requested rear spar at x/c 0.80 and a hinge at x/c 0.72
    When the plan is solved
    Then the rear spar sits at x/c 0.69

  Scenario: A very forward hinge cannot push the spar past the minimum
    Given a hinge at x/c 0.06
    When the plan is solved
    Then the rear spar sits at x/c 0.05

  Scenario: No hinge leaves the requested position untouched
    Given a requested rear spar at x/c 0.80 and no hinge
    When the plan is solved
    Then the rear spar sits at x/c 0.80

Feature: Layout solve

  Scenario: An over-loaded root reports infeasibility honestly
    Given a station whose required OD exceeds the containment band
    When I solve the spar plan
    Then feasible is false
    And utilisation is greater than 1.0
    And the message names the governing station and suggests a capped or box spar
    And no dimension has been silently reduced to fit

  Scenario: A negligible-load tip gets no spar
    Given a tip station whose required OD is below 1.0 mm
    When I solve the spar plan
    Then no piece is emitted for that region
    And front_no_spar_from_y reports where the spar stops

  Scenario: Offset half-span roots need a joiner
    Given the two halves' root center_z differ by 20 mm
    When the front joint is decided
    Then the joint type is "reinforcement+joiner"
    And a reinforcement piece is generated

  Scenario: Collinear half-span roots join continuously
    Given the two halves' root center_z differ by 2 mm
    When the front joint is decided
    Then the joint type is "continuous"

  Scenario: A single-half surface does not index into an empty half
    Given a vertical stabiliser with exactly one half
    When the front joint is decided
    Then the joint type is "continuous"
    And no IndexError is raised

Feature: Section-geometry seam

  Scenario: The analytic mode needs no geometry kernel
    Given mode "analytic"
    When I sample a section at y/span 0.5
    Then points are returned
    And no solid is built

  Scenario: points_per_edge is clamped
    Given points_per_edge 5
    When I sample a section
    Then the effective points_per_edge is 8

  Scenario: The solid mode fails loudly without CadQuery
    Given mode "solid" and an environment without CadQuery
    When I sample a section
    Then SectionGeometryUnavailableError is raised
    And the error names the missing geometry kernel
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Section-modulus sizing for all four shapes (RF-15) | Must | The strength law itself; every downstream number derives from it |
| `σ_allow ≤ 0` guard (RF-16) | Must | The material schema admits `0`, so the guard is the only thing between a valid input and a `ZeroDivisionError` |
| Layout solve with honest feasibility (RF-17) | Must | Structural-safety output consumed directly by the builder; clamping here would produce a spar that fails in flight |
| Negligible-load tip handling (RF-18) | Must | Without it the plan emits a Ø≈0 tube that is unbuildable and misleading (gh-1076) |
| Rear-spar hinge clearance (RF-19) | Must | A computed spar overlapping the control surface makes the wing unassemblable (gh-1059) |
| Station sampling with the root nudge (RF-S1/RF-S2) | Must | The governing station is the max-moment root; a pinched slice there corrupts the whole plan (gh-1037 #4) |
| Joint decisions, front and rear (RF-S5/RF-S6/RF-S7) | Must | Determines whether the two halves can actually be joined; RF-S6 is a crash guard (gh-1091) |
| CAD-free solver (RF-S9) | Must | The property that makes every branch testable on the fast tier; losing it means the solver stops being verified in CI |
| Bore reconstruction with the wall-factor fallback (RF-S4) | Should | Needed for telescoping tube stock, but a solid rod remains a valid build |
| Section-geometry sampling modes (RF-23) | Should | Needed by the solver's `"solid"` mode; the analytic default has no hard dependency |
| `t/c` fallback of 0.12 (RF-S3) | Should | A convenience so sizing degrades rather than failing on incomplete airfoil data |
| Persisting the solved plan back onto spars (RF-S8) | Should | The plan is useful as a read-only report; persistence is what makes it survive into CAD |
| Clamping an infeasible dimension to fit | Won't | Explicitly rejected by BR-W9 and ADR 0012 — an unsafe spar must never be reported as buildable |
| Fixing the frozen perpendicular-spare branch in `WingConfiguration` | Won't | Known dead branch inside the frozen topology layer, deliberately not fixed (ADR 0002) |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/spar_sizing.py` | `required_section_modulus` (l.78-88), `solve_dimension` (l.96+), the four shape moduli (l.40-70), the four inverses (l.137-208), `_TC_FALLBACK` (l.32), `σ_allow` guard (l.86-87) | 🟢 |
| `app/schemas/spar_sizing.py` | `SparSizingParams` (l.12-51) — `safety_factor_j`, `packing_factor`, `shape`, `cap_width_mm`, `material_id` | 🟢 |
| `cad_designer/airplane/geometry/spar_solver.py` | `plan_spar` (l.342), `solve_spar_plan` (l.619-672), `build_stations_from_geometry` (l.681-746), `rear_spar_x_c_with_clearance` (l.181-221), `_piece_from_run_with_od` (l.490-529), `_bore_for` (l.460-487), `_inboard_collinear`, `NEGLIGIBLE_OD_FLOOR_MM` (l.44-53, 438-457), CAD-free header (l.1-24) | 🟢 |
| `cad_designer/airplane/geometry/section_geometry.py` | `SectionGeometry` (l.160-219), `sample`, `SectionGeometryUnavailableError` (l.181-184) | 🟢 |
| `app/services/spar_plan_service.py` | plan orchestration | 🟢 |
| `app/services/spar_insert_service.py` | plan persistence onto the wing's spars | 🟢 |
| `app/models/aeroplanemodel.py` | `WingXSecSpareModel` (l.129) — the persistence target, **millimetres** | 🟢 |
| `components` / `Component` of type `material` | `allowable_bending_stress_mpa` supplier | 🟡 — the column is referenced by `SparSizingParams.material_id`; the components table itself belongs to the `powertrain` / COTS module |
