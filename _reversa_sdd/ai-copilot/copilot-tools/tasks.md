# ai-copilot / copilot-tools — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `versioning._metrics_payload` and `list_tree`.
- [ ] `copilot_apply_service` (`_find_open_proposal`, `apply_edits`,
      `get_or_open_proposal`, `discard_open_proposal`, `compute_metrics_diff`).
- [ ] `aero-analysis`: an AeroBuildup polar coroutine and a stability summary
      coroutine.
- [ ] `assumption_computation_context` carrying `x_np_m`, `cg_x`, `mac`,
      `aspect_ratio`, `e_oswald`, `v_cruise_mps`.
- [ ] `wing-design`: the validated `WingConfig` (mm) and persisted
      `WingXSecModel.xyz_le` (m).
- [ ] The turn loop dispatching through `asyncio.to_thread` — **without it
      `asyncio.run` inside `_run_analysis` fails**.

## Tasks

- [ ] **T-01 — `ToolEntry`, `TOOL_REGISTRY`, `list_schemas`.**
  Six entries, each a `schema` (OpenAI function-calling dict) + `impl`.
  - Legacy origin: `app/services/copilot_tools.py:828`
  - Definition of done: `len(TOOL_REGISTRY) == 6` and a test asserts the exact
    name set. The schemas are sent verbatim on every iteration, so a schema
    change is a model-visible contract change.
  - Confidence: 🟢

- [ ] **T-02 — `execute` + read-retargeting.**
  Unknown name ⇒ `{"error": "Unknown tool …. Known tools: <sorted>"}`;
  `_READ_RETARGETED_TOOLS = {get_design_snapshot, get_wing_geometry,
  run_analysis}` resolve through `_effective_target_id`; everything else gets
  the live id.
  - Legacy origin: `app/services/copilot_tools.py:866`
  - Definition of done: a test with an open proposal proves the three read tools
    see the proposal while `get_version_tree` and both write tools see the live
    node. Carry the docstring's reason — a retargeted write tool would open a
    proposal *of the proposal*.
  - Confidence: 🟢

- [ ] **T-03 — `_effective_target_id`.**
  Find the open proposal branch, return `branch.head_id`; `except Exception:
  pass` ⇒ the live id.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: reproduce the silent fallback **and record it as a
    gap** — a failed lookup is currently indistinguishable from "no proposal".
  - Confidence: 🟢 / 🔴

- [ ] **T-04 — `_drag_breakdown`.**
  `None` on missing inputs or `AR ≤ 0 / e ≤ 0 / CD_total ≤ 0`;
  `cd_i = cl²/(π·ar·e)`; `cd_par = cd_total − cd_i`; a `note`-carrying dict with
  the raw inputs when the split is impossible.
  - Legacy origin: `app/services/copilot_tools.py:242`
  - Definition of done: three unit tests (valid, `None`, note). Carry the
    comment naming the observed LLM failures (impossible splits, 10× errors) —
    it is the justification for the whole function.
  - Confidence: 🟢

- [ ] **T-05 — `_polar_drag_breakdown`.**
  `nanargmax(CL/CD)` for the max-L/D index; `aspect_ratio` / `e_oswald` from
  `assumption_computation_context`.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: a polar containing NaNs still selects the correct index;
    the `e` used is the **same** value the polar was computed with — never a
    snapshot `cd0`-derived one.
  - Confidence: 🟢

- [ ] **T-06 — `_run_polar_async`.**
  AeroBuildup over α ∈ [−10°, +15°], 26 points, V = 20 m/s, h = 0. Report
  `cl_max`, `cl_min`, `cd_min`, `cl_cd_max`, `drag_breakdown` and the four
  renamed characteristic points (`best_glide`, `min_drag`, `cl_max_point`,
  `stall`).
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: the renamed keys are present (the raw solver labels must
    not leak to the model); a missing context yields `drag_breakdown = None`
    without failing the polar.
  - Confidence: 🟢

- [ ] **T-07 — `_run_stability_async` + the gh-924 override.**
  Evaluate at α = 0 with `v = ctx.get("v_cruise_mps") or 20.0`; then override
  `neutral_point_x` with `ctx["x_np_m"]` and recompute
  `static_margin_pct = (x_np − cg_x)/mac × 100`.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: with a solver stub returning 0.109 and a context holding
    0.080, the tool reports **0.080**. Carry the comment explaining that the two
    stability paths normalise against different reference chords.
  - Confidence: 🟢

- [ ] **T-08 — `_run_analysis` wrapper.**
  Dispatch on `kind`; wrap in `asyncio.wait_for(..., 60.0)` executed via
  `asyncio.run`; `TimeoutError ⇒ {"status": "timeout", "note": …}`; any other
  exception ⇒ `{"error": str(exc)}`.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: the timeout result is a **status**, not an error, so the
    model tells the user to check the Analysis tab. Document that `asyncio.run`
    is only legal because the caller dispatches through `asyncio.to_thread`.
  - Confidence: 🟢

- [ ] **T-09 — `_get_wing_geometry` (gh-958).**
  `editable` per segment from the validated `WingConfig` (mm/deg); `derived` per
  station from persisted `xyz_le × 1000`, with `accumulated_dihedral_deg =
  degrees(atan2(Δz, Δy))` and `te_x_mm = LE_x + chord`; wing-level
  `projected_semi_span_mm` and `tip_xyz_le_mm`; the `note`.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: a wing with a root-airfoil dihedral proves the persisted
    read matches `cad_designer` where a segment re-walk would not. The `note`
    states that `chord_root_mm` is read-only.
  - Confidence: 🟢

- [ ] **T-10 — `_get_design_snapshot` and `_get_version_tree`.**
  Resolve the node by PK and delegate to `versioning._metrics_payload` /
  `list_tree`.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: the snapshot's keys match the `versioning` contract
    exactly, including `wing_names` and `wings[i].n_xsecs` (the model uses
    `at_index = n_xsecs` to append at the tip). Record the inherited
    `stability_results[-1]` quirk as a gap.
  - Confidence: 🟢

- [ ] **T-11 — The write-tool wrappers.**
  `_apply_design_edits` and `_discard_proposal`: `logger.exception` then
  `{"error": …}` on any failure.
  - Legacy origin: `app/services/copilot_tools.py:700-770`
  - Definition of done: no exception escapes either wrapper; the behaviour they
    wrap is specified in
    [`../proposal-adopt-discard/tasks.md`](../proposal-adopt-discard/tasks.md).
  - Confidence: 🟢

- [ ] **T-12 — The six schemas.**
  `get_design_snapshot {}`, `get_wing_geometry {wing?}`,
  `run_analysis {kind: enum[polar,stability]}` (required),
  `get_version_tree {}`, `apply_design_edits {ops}` (required),
  `discard_proposal {}`. The descriptions are the **only** prose the model sees.
  - Legacy origin: `app/services/copilot_tools.py:520-830`
  - Definition of done: `apply_design_edits`'s description carries the four
    operational instructions verbatim — call `get_design_snapshot` first for
    `wing_names` and `n_xsecs`; wing identifiers are **names**; units are mm and
    degrees; do **not** use `diff_proposal_branch` for performance numbers.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Registry:** exactly 6 named tools; no adopt/delete/upload tool
      exists.
- [ ] **TT-02 — Unknown tool:** error message lists the six sorted names.
- [ ] **TT-03 — Retargeting:** reads follow the proposal; tree and writes do not.
- [ ] **TT-04 — Retarget failure (characterisation):** a raising lookup falls
      back to the live id silently.
- [ ] **TT-05 — Drag split:** valid / `None` / note-dict.
- [ ] **TT-06 — Polar pick:** `nanargmax` survives NaNs.
- [ ] **TT-07 — Polar keys:** the four renamed characteristic points.
- [ ] **TT-08 — Stability override:** context value wins over the solver's.
- [ ] **TT-09 — Missing `x_np_m`:** the solver value passes through
      (characterisation of the one remaining divergence path).
- [ ] **TT-10 — Timeout:** `{"status": "timeout"}` and not an error.
- [ ] **TT-11 — Wing geometry:** both blocks, mm/degrees, the `note`, and a
      root-dihedral case that only the persisted read gets right.
- [ ] **TT-12 — Snapshot passthrough:** keys equal `_metrics_payload`'s.
- [ ] **TT-13 — No exception escapes:** every impl returns a dict for every
      failure mode exercised.
- [ ] **TT-14 — No commit:** running every read tool leaves the session clean.

## Suggested Order

1. **T-04 → T-05** the pure arithmetic first: no database, no solver, and it is
   the module's whole reason to exist.
2. **T-06 → T-08** the analysis tools, timeout wrapper last so the solver
   behaviour is already proven.
3. **T-09** wing geometry — the only tool with a units exception; write its test
   before its implementation.
4. **T-10** the two passthroughs, trivial once `versioning` exists.
5. **T-01 → T-03** the registry and dispatch, once there is something to
   register. T-03 (retargeting) needs `copilot_apply_service`, so it comes after
   the proposal use case is at least stubbed.
6. **T-11 → T-12** the write wrappers and the schemas last: the descriptions can
   only be finalised once the behaviour they describe is fixed.

## Pending Gaps (🔴)

- **Should a retarget failure be surfaced** to the model (or at least logged)
  rather than degrading to the live design?
- **Should `_metrics_payload` become a public, versioned contract**, given three
  call sites in two modules import it?
- **Should the polar sweep be derived from the aircraft** (cruise speed,
  expected α range) instead of the fixed α ∈ [−10°, +15°] at 20 m/s?
- **What happens when `x_np_m` is missing?** Today the single-source guarantee
  silently lapses.
- **Should the mm/degrees exception be removed** by returning SI plus an explicit
  unit field, so the one deviation stops being a trap?
- **Should tool invocations be instrumented** — duration, argument size, timeout
  rate — so the 60 s cap and the 6-iteration cap can be tuned with data?
- **Should `get_design_snapshot` order `stability_results` by `computed_at`**
  rather than taking the last inserted row?
