# ai-copilot / copilot-tools

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

The **6-tool registry** is the copilot's entire capability surface and, in the
absence of authentication, effectively its security model. Every tool computes
its numbers in Python, returns JSON, and reports failure as data. 🟢

Two properties make this use case load-bearing:
**curation** (6 tools, not the 76-tool MCP surface and not the ~230-route REST
surface) and **determinism** (the drag split, the polar characteristic points
and the neutral point are all computed server-side because the model is
unreliable at arithmetic). 🟢

## Responsibilities

- Hold `TOOL_REGISTRY` and expose `list_schemas()` to the turn loop. 🟢
- Resolve the **effective target id** (read-retargeting) before dispatch. 🟢
- Compute the induced/parasite drag split and the polar characteristic points. 🟢
- Evaluate stability at the cruise point and override `x_np` from the
  computation context. 🟢
- Return wing geometry in **mm/degrees**, editable + derived. 🟢
- Time-box analysis at 60 s and report a timeout as a *status*. 🟢

## Business Rules

- **BR-47 — Six tools, curated.** 🟢 `get_design_snapshot`,
  `get_wing_geometry`, `run_analysis`, `get_version_tree`,
  `apply_design_edits`, `discard_proposal`. The module header states the rule:
  *"only the tools that are safe, fast, and meaningful for an advisory
  interaction"*.
- **BR-CO6 — `fn(db, aeroplane_id, **kwargs) -> dict`**, JSON-serialisable,
  errors as `{"error": …}`, never raised, never committing. 🟢
- **BR-CO7 — Read-retargeting (gh-938).** 🟢
  `_READ_RETARGETED_TOOLS = {get_design_snapshot, get_wing_geometry,
  run_analysis}` resolve to `branch.head_id` of the open proposal;
  `get_version_tree` and both write tools always receive the live id.
- **BR-CO30 — An unknown tool name returns the known list.** 🟢
  `{"error": "Unknown tool 'x'. Known tools: apply_design_edits, …"}` — sorted,
  so the model can self-correct.
- **BR-45 / ADR 0004 — Numbers are computed in Python.** 🟢
  `CD_i = CL²/(π·AR·e)`; `CD_parasite = CD_total − CD_i`. One source for
  `CD_total`; snapshot `cd0` is **never** mixed in.
- **BR-CO8 / ADR 0012 — Impossible is reported, not fudged.** 🟢
  `None` on a missing input or `AR ≤ 0 / e ≤ 0 / CD_total ≤ 0`; a
  `note`-carrying dict with the raw inputs when `cd_i < 0`, `cd_par < 0` or
  `cd_i > cd_total`.
- **BR-CO31 — The polar's `e` and `AR` come from the same place as the split.**
  🟢 `_polar_drag_breakdown` reads `aspect_ratio` / `e_oswald` from
  `assumption_computation_context` and picks the max-L/D point via
  `nanargmax(CL/CD)`.
- **BR-CO32 — The polar sweep is fixed.** 🟢 AeroBuildup over α ∈ [−10°, +15°],
  **26 points**, V = 20 m/s, h = 0. Reported: `cl_max`, `cl_min`, `cd_min`,
  `cl_cd_max`, `drag_breakdown`, plus four characteristic points renamed for the
  model — `best_glide`, `min_drag`, `cl_max_point`, `stall`.
- **BR-CO9 — One op-point, one neutral point (gh-924).** 🟢 Stability is
  evaluated at α = 0 with `v_cruise_mps` from the context (fallback 20 m/s), and
  the fresh neutral point is **overridden** with `ctx["x_np_m"]`;
  `SM = (x_np − cg_x)/MAC × 100`.
- **BR-CO10 — 60 s cap; a timeout is a status.** 🟢
  `{"status": "timeout", "note": …}`.
- **BR-CO11 — The derived wing block is read, not re-derived.** 🟢 (gh-958)
  From persisted `WingXSecModel.xyz_le` (m × 1000); accumulated cant from
  `atan2(Δz, Δy)`. The `note` warns that `chord_root_mm` is **read-only**.
- **BR-CO33 — `get_design_snapshot` returns the `versioning` payload
  verbatim.** 🟢 It calls the private `_metrics_payload`, so the tool contract
  inherits that function's quirks — including `stability_results[-1]` being the
  last **inserted** row, not the newest by `computed_at`. 🟡

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Expose exactly 6 tools with OpenAI function-calling schemas | Must | `len(TOOL_REGISTRY) == 6`; `list_schemas()` returns 6 |
| RF-02 | Retarget the three read tools to the proposal head | Must | With a proposal open, the snapshot reflects the proposal |
| RF-03 | Never retarget `get_version_tree` or the write tools | Must | They see the live lineage / live id |
| RF-04 | Return an error dict, never raise | Must | Every impl is exception-free at its boundary |
| RF-05 | Report an unknown tool with the known list | Must | Sorted names present in the message |
| RF-06 | Compute the drag split from a single `CD_total` source | Must | `CD_parasite == CD_total − CD_i` |
| RF-07 | Return `None` on degenerate drag inputs | Must | `e = 0` ⇒ `None` |
| RF-08 | Return a note dict on an impossible split | Must | Raw inputs present, no split keys |
| RF-09 | Pick the polar's max-L/D point via `nanargmax(CL/CD)` | Must | NaNs in the polar do not shift the pick |
| RF-10 | Report the four renamed characteristic points | Must | `best_glide`, `min_drag`, `cl_max_point`, `stall` |
| RF-11 | Evaluate stability at the cruise point | Must | α = 0, `v = ctx.v_cruise_mps or 20` |
| RF-12 | Override the neutral point from the context | Must | Result `x_np == ctx["x_np_m"]` |
| RF-13 | Recompute static margin from the overridden `x_np` | Must | `(x_np − cg_x)/MAC × 100` |
| RF-14 | Time-box analysis at 60 s and return a timeout status | Must | `{"status": "timeout"}`, not an error |
| RF-15 | Return wing geometry in mm/degrees with both blocks | Must | `editable[]` + `derived[]` present |
| RF-16 | Source the derived block from persisted `xyz_le` | Must | Matches the `cad_designer` frame including root dihedral |
| RF-17 | Carry the `chord_root_mm` read-only note | Must | `note` present in the payload |
| RF-18 | Return the lineage tree for the live node | Should | Nodes + branches |
| RF-19 | Return `_metrics_payload` verbatim for the snapshot | Should | Same keys as the `versioning` contract |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Correctness | No reported number originates from the model | `_drag_breakdown:242`, `_run_stability_async` | 🟢 |
| Correctness | Exactly one neutral point exists per aircraft | gh-924 override; ADR 0004 | 🟢 |
| Correctness | A physically impossible result is surfaced, never replaced by a fallback | ADR 0012; the note dict | 🟢 |
| Performance | An analysis cannot occupy the turn for more than 60 s | `DEFAULT_ANALYSIS_TIMEOUT_S` | 🟢 |
| Reliability | A tool never propagates an exception into the loop | `try/except` at every impl boundary | 🟢 |
| Security | The model cannot select an aeroplane — the id is fixed by the endpoint | `execute(name, db, aeroplane_id, …)` | 🟢 |
| Consistency | Units are SI except the one documented mm/degrees tool | module docstring | 🟢 (a 🟡 trap) |
| Observability | A retarget failure surfaces in the tool result (`Q-CO-3`) | `except Exception: pass` today | 🟡 |

## Acceptance Criteria

```gherkin
Feature: The curated tool surface

  Scenario: Exactly six tools
    When I enumerate TOOL_REGISTRY
    Then it has 6 entries
    And none of them adopts, promotes or merges a branch
    And none of them deletes an aeroplane, wing or cross-section
    And none of them uploads or downloads a file

  Scenario: An unknown tool is self-correcting
    When execute("get_wings") is called
    Then the result is an error naming the six known tools

Feature: Read-retargeting

  Scenario: Reads follow the proposal
    Given an open proposal whose span differs from the live design
    When get_design_snapshot runs
    Then it returns the proposal's span

  Scenario: The version tree stays live
    Given an open proposal
    When get_version_tree runs
    Then it returns the live node's lineage

  Scenario: Write tools stay live
    Given an open proposal
    When apply_design_edits runs
    Then it resolves the proposal from the live lineage, not from itself

  Scenario: A retarget failure degrades silently
    Given the proposal lookup raises
    When get_design_snapshot runs
    Then it returns the live design's metrics
    And nothing indicates the retarget failed

Feature: Deterministic drag

  Scenario: A valid split
    Given CL = 0.8, CD_total = 0.05, AR = 10, e = 0.85
    When _drag_breakdown runs
    Then cd_induced equals 0.8^2 / (pi * 10 * 0.85)
    And cd_parasite equals CD_total minus cd_induced

  Scenario: Degenerate input
    Given e = 0
    Then the result is None

  Scenario: Impossible split
    Given inputs for which cd_induced exceeds CD_total
    Then the result carries a note and the raw inputs
    And it carries no cd_induced/cd_parasite pair

Feature: One neutral point

  Scenario: The context wins
    Given assumption_computation_context.x_np_m = 0.080
    And the solver would return 0.109
    When run_analysis(kind="stability") runs
    Then the reported neutral point is 0.080
    And the static margin is (0.080 - cg_x) / MAC * 100

  Scenario: A slow analysis
    Given the analysis exceeds 60 seconds
    Then the result is {"status": "timeout", ...}
    And it is not an {"error": ...}

Feature: Wing geometry

  Scenario: Both blocks, mm and degrees
    When get_wing_geometry runs for a two-segment wing
    Then editable has 2 entries with chord_root_mm, chord_tip_mm, length_mm,
      sweep_mm, dihedral_rel_deg, incidence_deg, airfoil
    And derived has 3 entries with xyz_le_mm, chord_mm, twist_deg,
      accumulated_dihedral_deg, te_x_mm
    And the note states that chord_root_mm is read-only

  Scenario: Derived follows the persisted frame
    Given a wing whose root airfoil carries a dihedral
    When get_wing_geometry runs
    Then accumulated_dihedral_deg matches the persisted xyz_le geometry
    And not a re-walk of the segment list
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| The 6-tool curation (RF-01) | Must | The surface *is* the permission model |
| Return-value error contract (RF-04/RF-05) | Must | The model self-corrects from data, not from stack traces |
| Read-retargeting (RF-02/RF-03) | Must | Otherwise the model iterates against data it did not write |
| Deterministic drag + the impossible-split note (RF-06…RF-08) | Must | ADR 0004 / ADR 0012 |
| The `x_np` override (RF-11…RF-13) | Must | gh-924 — two neutral points in one UI is a correctness bug |
| Analysis timeout (RF-14) | Must | Bounds the turn |
| Wing geometry in mm with the read-only note (RF-15…RF-17) | Must | The units and the note are what make the edit ops land |
| Polar characteristic points (RF-09/RF-10) | Should | Advisory richness |
| Version tree / snapshot passthrough (RF-18/RF-19) | Should | Thin wrappers over `versioning` |
| A tool that adopts a branch | Won't | ADR 0007 — must never exist |
| A tool that reaches another aeroplane | Won't | The id is fixed by the endpoint |
| Airfoil, COTS, construction-plan or export tools | Won't | Deliberately outside the advisory surface |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/services/copilot_tools.py:242` | `_drag_breakdown` | 🟢 |
| `…` | `_polar_drag_breakdown`, `_run_polar_async`, `_run_stability_async` | 🟢 |
| `…` | `_get_design_snapshot`, `_get_wing_geometry`, `_get_version_tree` | 🟢 |
| `…:828` | `TOOL_REGISTRY` (6) | 🟢 |
| `…:866` | `execute` + `_READ_RETARGETED_TOOLS` | 🟢 |
| `…` | `_effective_target_id` | 🟢 / 🟡 must surface the failure (`Q-CO-3`) |
| `…` | `list_schemas`, `ToolEntry`, `DEFAULT_ANALYSIS_TIMEOUT_S = 60.0` | 🟢 |
| `app/services/aeroplane_version_service.py:74` | `_metrics_payload` | 🟢 owned by `versioning` |
