# operating-point-solve — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `AnalysisModel` and `analyse_aerodynamics` in place
      ([`../tasks.md`](../tasks.md) T-01, T-02).
- [ ] `operating_points` table with `alpha`/`beta` in **radians**, `controls`,
      `control_deflections`, `status`, `warnings`, `trim_enrichment`.
- [ ] An `asb.Airplane` builder that carries the gh-772 control-variable names
      (→ `wing-design` / `control_surface_mixing`).
- [ ] SciPy (`optimize.brentq`).
- [ ] The aeroplane schema exposing per-TED deflection limits.

## Tasks

- [ ] **T-01 — `OperatingPointSchema` with the rad/deg guard.**
  Fields and defaults per [`../contracts.md`](../contracts.md). Add the field
  validator rejecting `|alpha| > 180` or `|beta| > 180` with the message
  "almost certainly means radians were passed instead of degrees
  (gh-577/gh-587)". `alpha` accepts `float | list[float]`; `beta` is scalar.
  - Legacy origin: `app/schemas/aeroanalysisschema.py:231`
  - Definition of done: `alpha = 200` → 422 with that message; `alpha = 0.0873`
    is accepted as 0.09°; a list-valued `alpha` passes validation.
  - Confidence: 🟢

- [ ] **T-02 — `operating_point_model_to_schema` — the single conversion point.**
  Convert `alpha`/`beta` radians → degrees; copy `velocity`, `p`, `q`, `r`,
  `altitude`, `xyz_ref` verbatim; call `_require_field` for every NOT-NULL
  column instead of defaulting.
  - Legacy origin: `app/services/operating_point_resolver.py`
  - Definition of done: `0.0873 rad` → `5.0 deg`; a NULL `velocity` raises; no
    other function in the codebase calls `degrees()` on an OP field.
  - Confidence: 🟢

- [ ] **T-03 — `_pick_deflections` precedence.**
  A **non-empty** `control_deflections` wins; `None` or `{}` falls back to
  `controls`.
  - Legacy origin: `app/services/operating_point_resolver.py`
  - Definition of done: `{}` leaves a fresh trim intact; `{"elevator": 1.0}`
    replaces `controls` wholesale (it is a replacement, not a merge).
  - Confidence: 🟢

- [ ] **T-04 — `resolve_operating_point` (gh-577).**
  Four guards, in order: pass-through when `operating_point_id is None`; load
  **constrained to `aircraft_pk` in the query**; require `TRIMMED` unless
  `require_trimmed=False`; convert via T-02.
  - Legacy origin: `app/services/operating_point_resolver.py:138-213`
  - Definition of done: an OP id belonging to another aeroplane is **not found**
    (the filter is in the `WHERE` clause, not a post-check); a `DIRTY` row is
    refused by default and accepted with the flag.
  - Confidence: 🟢

- [ ] **T-05 — `validate_deflections_against_airplane` (BR-20).**
  Collect the airplane's available control-variable names, diff against the
  request, raise a `ValidationError` naming **both** sets when the diff is
  non-empty. Call it from the streamline, four-view, strip-force and
  AeroBuildup-trim paths.
  - Legacy origin: `app/services/operating_point_resolver.py`
  - Definition of done: a typo'd surface name returns 422 with both lists; ASB's
    silent drop is unreachable from any endpoint.
  - Confidence: 🟢

- [ ] **T-06 — Trim-variable resolution.**
  Accept the tagged name, the display name, or a **role** name. A role resolves
  to that surface's **primary (pitch | lift)** axis, because AeroBuildup models
  only the symmetric axis (gh-772 / ADR 0003).
  - Legacy origin: `app/services/aerobuildup_trim_service.py`
  - Definition of done: trimming with `"ruddervator"` moves
    `[ruddervator]pitch_…` and leaves `[ruddervator]yaw_…` at `0.0`.
  - Confidence: 🟢

- [ ] **T-07 — Bracketed Brent trim.**

  ```
  residual(δ) = coeff(δ) − target        # one run_with_stability_derivatives per call
  if residual(lower) · residual(upper) > 0:
      return converged = False, warning naming the interval and both residuals
  brentq(residual, lower, upper, xtol = 1e-6, maxiter = 50)
  ```

  - Legacy origin: `app/services/aerobuildup_trim_service.py`
  - Definition of done: `Cm → 0` within tolerance on a trimmable aircraft; an
    unbracketed case returns HTTP 200 with `converged=false` and **never**
    raises; the solver-call count is bounded by `maxiter + 3`.
  - Confidence: 🟢

- [ ] **T-08 — `build_deflection_limits_from_schema`.**
  Produce `{control_name: (max_pos_deg, max_neg_deg)}` from the aeroplane
  schema's TED rows.
  - Legacy origin: `app/services/trim_enrichment_service.py:72-118`
  - Definition of done: every control variable the solver can move has an entry.
  - 🟢 **Decided (`Q-WD-1`):** key by the canonical mixing name. The legacy keys this map by the **raw DB
    TED name**, while `controls` uses the gh-772 mixing name
    (`[ruddervator]pitch_htail_1`). Key it by the **mixing name** — derive it
    with `control_surface_mixing.axis_control_name`. A dual-role surface
    contributes **two** entries (primary and secondary axis).
  - Confidence: 🟢 for the legacy shape, 🔴 for the key

- [ ] **T-09 — `compute_enrichment` — the single entry point.**
  Implement the whole threshold block from [`design.md`](design.md)
  §Enrichment Flow: usage fractions with the 0.95 / 0.80 ladder, the trim-quality
  ladder (0.5 / 0.1), the `LIMIT_REACHED` critical, the static-margin ladder
  (`−Cm_a/CL_a`: ≤ 0 / < 0.05 / > 0.30), and the AeroBuildup + mixed-surface
  solver caveat. Union every surface via `dict.fromkeys(limits, 0.0) | controls`
  (gh-863).
  - Legacy origin: `app/services/trim_enrichment_service.py:380-572`
  - Definition of done: it is the only enrichment implementation, called by all
    three trim paths (AVL trim, AeroBuildup trim, OP generation); a 0.96 usage
    yields exactly one `critical`/`authority` warning naming the surface.
  - Confidence: 🟢

- [ ] **T-10 — `decompose_dual_role`.**

  ```
  d_sym  = mix_gain_primary   · δ_primary
  d_anti = mix_gain_secondary · δ_secondary
  right  =  d_anti ; left = −d_anti
  the negative (up-going) side is scaled by differential_ratio
  deflection_left/right = d_sym + left/right
  ```

  - Legacy origin: `app/services/trim_enrichment_service.py`
  - Definition of done: `differential_ratio` never multiplies `d_sym`; with
    `ratio = 1.0` left and right are symmetric about `d_sym`; the values are
    **reporting only** — no trim or aero quantity changes (BR-10).
  - Confidence: 🟢

- [ ] **T-11 — `TrimEnrichment` and friends.**
  `analysis_goal`, `trim_method`, `trim_score`,
  `trim_residuals: dict[str, float]` (**floats only**, gh-627),
  `deflection_reserves`, `design_warnings`, `effectiveness`,
  `stability_classification`, `mixer_values`, `result_summary`,
  `aero_coefficients`; nested types per
  [`../contracts.md`](../contracts.md).
  - Legacy origin: `app/schemas/aeroanalysisschema.py`
  - Definition of done: a string in `trim_residuals` fails validation; the
    solver path is only expressible through `trim_method`.
  - Confidence: 🟢

- [ ] **T-12 — Best-effort enrichment on the trim endpoints.**
  Compute enrichment inside a guard so a failure degrades the response rather
  than failing the trim.
  - Legacy origin: `app/api/v2/endpoints/operating_points.py`
    (`avl_trim_operating_point`, `aerobuildup_trim_operating_point`)
  - Definition of done: an enrichment exception still returns the converged trim
    with HTTP 200.
  - Confidence: 🟢

- [ ] **T-13 — Persist the trim.**
  Write `status`, `controls[name] = δ`, `trim_enrichment` and any `warnings`;
  leave `control_deflections` untouched (it is the user's override channel).
  - Legacy origin: `app/api/v2/endpoints/operating_points.py`,
    `app/models/analysismodels.py:20`
  - Definition of done: a re-read returns the same trim; a manual override set
    earlier survives the trim.
  - Confidence: 🟢

- [ ] **T-14 — Deflection patch route.**
  `PATCH /operating_points/{op_id}/deflections` writes
  `control_deflections`; an empty dict is stored as "no override" and must not
  erase `controls`.
  - Legacy origin: `app/api/v2/endpoints/operating_points.py:331-355`
  - Definition of done: patching `{}` leaves the resolved deflections equal to
    `controls`.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Happy path, stored trimmed point.** rad→deg; the analysis runs
      with the OP's `controls`.
- [ ] **TT-02 — Empty override is a no-op.** `{}` does not erase a fresh trim.
- [ ] **TT-03 — Manual override wins.** A non-empty override replaces
      `controls`.
- [ ] **TT-04 — Cross-aeroplane injection refused.** The row is not found; no
      solver call is made (assert on a mock).
- [ ] **TT-05 — Untrimmed refused by default**, accepted with
      `require_trimmed=False`.
- [ ] **TT-06 — NULL NOT-NULL column raises**, never analyses at `0.0`.
- [ ] **TT-07 — Unknown deflection name → 422** listing unknown and available.
- [ ] **TT-08 — Rad/deg guard.** `alpha = 200` → 422 with the documented
      message.
- [ ] **TT-09 — Moment reference.** Changing `xyz_ref[0]` changes `Cm` with
      geometry fixed.
- [ ] **TT-10 — Brent convergence.** `|Cm|` at the returned deflection is below
      tolerance; the call count is bounded.
- [ ] **TT-11 — Unbracketed root.** HTTP 200, `converged=false`, a warning
      naming the interval, no exception.
- [ ] **TT-12 — Role → primary axis.** `"ruddervator"` moves the pitch axis
      only.
- [ ] **TT-13 — Authority ladder.** 0.96 → critical, 0.85 → warning, 0.5 →
      nothing.
- [ ] **TT-14 — Trim-quality ladder.** `trim_score` 0.6 → critical, 0.2 →
      warning.
- [ ] **TT-15 — Static-margin ladder.** `−Cm_a/CL_a` of −0.01 → critical, 0.03 →
      warning, 0.35 → warning, 0.15 → nothing.
- [ ] **TT-16 — Full-surface reporting.** Three surfaces, one trimmed → three
      entries, two at `0.0`.
- [ ] **TT-17 — Mixer decomposition.** `differential_ratio` scales only the
      up-going side; `d_sym` is untouched.
- [ ] **TT-18 — `trim_residuals` rejects strings** (gh-627 regression).
- [ ] **TT-19 — #955 regression.** A ruddervator's reserve uses its **real** TED
      limits, not `(25, 25)`, and no phantom surface appears under the DB name.
- [ ] **TT-20 — Best-effort enrichment.** An enrichment exception still returns
      the converged trim.
- [ ] **TT-21 — Fast-tier coverage.** Every test above runs **without**
      AeroSandbox installed by stubbing the solver boundary (ADR 0015).

## Suggested Order

1. **T-01 → T-04** — the resolver chain is the entry gate; nothing downstream is
   safe until the four guards exist.
2. **T-05** immediately after, because every solver path calls it.
3. **T-06, T-07** — trim-variable resolution before the root-find, so the Brent
   loop always receives a real control name.
4. **T-08** before **T-09**: the enrichment cannot be tested without a limits
   map, and T-08 carries the #955 deviation that T-09's assertions depend on.
5. **T-10, T-11** with T-09 (same schema surface).
6. **T-12 → T-14** last — transport and persistence over a green service layer.

Blocking edges: T-04 ⇠ T-02, T-03 · T-07 ⇠ T-06 · T-09 ⇠ T-08, T-11 ·
T-10 ⇠ T-11 · T-13 ⇠ T-07, T-09.

## Pending Gaps

- **#955 naming divergence (T-08).** Must be decided before T-09 is written: key
  the limits map by the gh-772 mixing name. Open sub-question — should the
  response also expose *which* name a reserve was matched on, so a future
  mismatch is visible instead of silent?
- **The `(25.0, 25.0)` fallback is unmarked.** Should a reserve computed against
  the default carry a flag (e.g. `limits_provenance: "fallback"`), so the UI can
  distinguish "±25° because that is the real limit" from "±25° because we could
  not find one"? ADR 0012 argues yes.
- **`analyze_wing` vs `analyze_airplane` geometry divergence.** The wing path
  prunes the airplane and therefore never uses the stored AVL geometry. Is that
  intended, or should both consult the same source?
- **Non-finite handling on the operating-point router.** It is a plain
  `APIRouter()`, so NaN is not converted to `null` there. Deliberate or an
  oversight?
- **Warnings are never cleared.** A successful trim leaves earlier warnings on
  the row. Should a successful trim reset the list, or is the audit trail the
  point?
