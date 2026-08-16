# control-surface-naming — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] A TED role vocabulary: `elevator`, `stabilator`, `aileron`, `rudder`,
      `flap`, `elevon`, `flaperon`, `ruddervator`, `other` (`wing-design`).
- [ ] Per-TED `hinge_point`, `mix_gain_primary`, `mix_gain_secondary`,
      `differential_ratio`, `symmetric` and deflection limits.
- [ ] A wing key and an x-section index available at build time.
- [ ] **No database, solver or binary dependency** — this use case must be pure
      functions over primitives.

## Tasks

- [ ] **T-01 — The axis tables.**

  ```
  _DUAL_ROLE_AXES = { elevon:      (pitch, roll),
                      flaperon:    (lift,  roll),
                      ruddervator: (pitch, yaw)  }
  PRIMARY_AXES   = {pitch, lift}     # symmetric      SgnDup = +1
  SECONDARY_AXES = {roll,  yaw}      # antisymmetric  SgnDup = −1
  ```

  - Legacy origin: `app/services/control_surface_mixing.py:29-33`
  - Definition of done: every role in the vocabulary is either in
    `_DUAL_ROLE_AXES` or explicitly single-axis; every axis appears in exactly
    one of `PRIMARY_AXES` / `SECONDARY_AXES`; a test asserts the two sets are
    disjoint and cover the axis vocabulary.
  - Confidence: 🟢

- [ ] **T-02 — `ControlAxis`.**
  Immutable value object with `name`, `sgn_dup`, `gain`, `symmetric`,
  `hinge_point`, `deflection`, `role`, `axis`.
  - Legacy origin: `app/services/control_surface_mixing.py:41`
  - Definition of done: it carries enough to explain any emitted name back to its
    source; `sgn_dup` is documented as a **sign flag, never a magnitude**
    (BR-10).
  - Confidence: 🟢

- [ ] **T-03 — `axis_control_name`.**
  `f"[{role}]{axis}_{sanitize(wing_key)}_{xsec_index}"`.
  - Legacy origin: `app/services/control_surface_mixing.py:76-84`
  - Definition of done: `("ruddervator", "pitch", "htail", 1)` →
    `"[ruddervator]pitch_htail_1"`; a wing named `"H Tail"` produces a name AVL
    accepts.
  - 🟡 **Specify `sanitize` explicitly.** The analysis does not record which
    characters it strips or replaces. Two wing names differing only in
    punctuation must not sanitise to the same key, or the uniqueness assertion
    fires on aircraft that are actually valid.
  - Confidence: 🟢 for the format, 🟡 for `sanitize`

- [ ] **T-04 — `_ROLE_TAG_RE` and role extraction.**
  `^\[(\w+)\](.*)$`.
  - Legacy origin: `app/services/control_surface_mixing.py:25`
  - Definition of done: `"[elevon]roll_wing_2"` → role `"elevon"`; an untagged
    name yields no role rather than raising. Capability gating in
    `mission-and-sizing` must be able to classify controls **from the name
    alone**, without a database round-trip.
  - Confidence: 🟢

- [ ] **T-05 — The decomposition.**
  For a dual role emit **two** `ControlAxis` per the table in
  [`requirements.md`](requirements.md) BR-9; for anything else emit the existing
  single-axis object with its tagged name and `±1` sign **verbatim**.
  - Legacy origin: `app/services/control_surface_mixing.py`, single-axis
    passthrough at l.134-146
  - Definition of done: an `elevon` at 10° yields
    `[elevon]pitch_…` (`+1`, gain `mix_gain_primary`, `symmetric = True`,
    deflection 10) and `[elevon]roll_…` (`−1`, gain `mix_gain_secondary`,
    `symmetric = False`, deflection **`0.0`**); an `elevator` is byte-identical
    before and after the change (gh-772 must be backwards compatible).
  - Confidence: 🟢

- [ ] **T-06 — The zero secondary baseline, with its reason recorded.**
  - Legacy origin: same
  - Definition of done: the antisymmetric axis's `deflection` is `0.0`, and a
    comment records why: the same `ControlAxis` list is handed to AeroSandbox,
    which models a **single** axis, so a non-zero antisymmetric baseline would be
    applied as if it were symmetric (ADR 0003, negative consequence).
  - Confidence: 🟢

- [ ] **T-07 — `assert_unique_control_names`.**
  Raise `ValueError` naming the colliding string on any duplicate.
  - Legacy origin: `app/services/control_surface_mixing.py:149-164`
  - Definition of done: it is called **across surfaces** by the AVL builder
    **before** any file text exists; the rationale is in a comment (AVL silently
    collapses identically named `CONTROL` variables into a single DOF,
    avl_doc 778-789).
  - Confidence: 🟢

- [ ] **T-08 — Per-surface dedup.**
  The AVL builder duplicates a control onto sections `i` and `i+1` of the same
  surface; that repetition must be deduped, not rejected.
  - Legacy origin: `build_avl_geometry_file` in
    `app/services/avl_geometry_service.py`
  - Definition of done: intra-surface repetition builds successfully;
    cross-surface repetition raises.
  - Confidence: 🟢

- [ ] **T-09 — Single implementation, three consumers.**
  The AVL geometry builder, the ASB airplane builder and the trim-enrichment
  service must all import this module rather than deriving names themselves.
  - Legacy origin: `app/services/avl_geometry_service.py`,
    `app/converters/model_schema_converters.py`,
    `app/services/trim_enrichment_service.py`
  - Definition of done: a grep for a control-name format string (`"[{"` /
    `"]{"` patterns, or an f-string containing `_` joins of role and axis)
    outside this module returns nothing.
  - Confidence: 🟢

- [ ] **T-10 — #955 fix (a): key deflection limits by the mixing name.**
  `build_deflection_limits_from_schema` must produce
  `{axis_control_name(...): (max_pos, max_neg)}`. A **dual-role surface
  contributes two entries** — one per axis — because the solver can move each
  axis independently.
  - Legacy origin: `app/services/trim_enrichment_service.py:72-118`
  - Definition of done: on a V-tail aircraft the reserve is computed against the
    **real** TED limits, not `(25.0, 25.0)`, and the gh-863 union produces **no
    phantom surface** under the DB name.
  - Confidence: 🔴 (confirmed defect; the fix is a deliberate deviation)

- [ ] **T-11 — #955 fix (b): resolve the pitch control by the mixing name.**
  `retrim_service._find_pitch_control_name` must return the **primary (pitch)
  axis name** of the first TED whose role ∈
  `{elevator, stabilator, elevon, ruddervator}`, not the raw DB `name`.
  - Legacy origin: `app/services/retrim_service.py`
  - Definition of done: the background retrim resolves a V-tail's pitch control
    directly, without relying on `aerobuildup_trim_service` re-resolving
    display/role names; a test asserts the returned string equals
    `axis_control_name(role, "pitch", wing_key, index)`.
  - Confidence: 🔴

- [ ] **T-12 — #955 fix (c): stop matching `"elevator"` by substring.**
  `stability_service._find_trim_elevator` must resolve the pitch control through
  the axis decomposition.
  - Legacy origin: `app/services/stability_service.py`
  - Definition of done: a V-tail aircraft reports a **non-null**
    `trim_elevator_deg`; the row records **which** control variable it came
    from, so a `NULL` distinguishes "no pitch control" from "no match".
  - Confidence: 🔴

- [ ] **T-13 — Make a limits miss loud (ADR 0012).**
  When a control variable has no entry in `limits`, do not silently substitute
  `(25.0, 25.0)`.
  - Legacy origin: **absent** — this is new behaviour
  - Definition of done: a miss either raises (preferred, since after T-10 it can
    only mean a genuine bug) or emits a `DesignWarning` and marks the reserve's
    provenance as `fallback`, so the number is never presented as authoritative.
  - Confidence: 🔴 (new behaviour)

## Test Tasks

- [ ] **TT-01 — Axis tables.** `PRIMARY_AXES` and `SECONDARY_AXES` are disjoint
      and cover the axis vocabulary; every dual role maps to one of each.
- [ ] **TT-02 — Elevon decomposition.** Two axes with the documented sign, gain,
      symmetry and baselines.
- [ ] **TT-03 — Flaperon** → `(lift, roll)`; **ruddervator** → `(pitch, yaw)`.
- [ ] **TT-04 — Single-axis passthrough.** An `elevator`'s name and sign are
      byte-identical before and after the gh-772 decomposition (backwards
      compatibility).
- [ ] **TT-05 — Secondary baseline is `0.0`** for every dual role.
- [ ] **TT-06 — Naming format.** `[ruddervator]pitch_htail_1`.
- [ ] **TT-07 — Sanitisation.** A wing named `"H Tail"` yields an AVL-safe name;
      two wing names differing only in punctuation do **not** collide.
- [ ] **TT-08 — Role extraction.** `[elevon]roll_wing_2` → `elevon`; an untagged
      name yields no role without raising.
- [ ] **TT-09 — Cross-surface collision** raises, naming the string, before any
      geometry is written.
- [ ] **TT-10 — Intra-surface duplication** builds successfully.
- [ ] **TT-11 — Single implementation.** A grep-based test asserts no other
      module formats a control name.
- [ ] **TT-12 — #955 (a).** A V-tail's reserve uses its real TED limits; no
      phantom surface appears.
- [ ] **TT-13 — #955 (b).** The retrim's pitch-control name equals
      `axis_control_name(role, "pitch", …)`.
- [ ] **TT-14 — #955 (c).** A V-tail reports a non-null `trim_elevator_deg`, and
      the source control is recorded.
- [ ] **TT-15 — Loud miss (T-13).** A control variable absent from `limits`
      raises or produces a flagged fallback — never a silent `(25, 25)`.
- [ ] **TT-16 — Purity.** The whole module's tests run with no database, no
      AeroSandbox and no AVL binary.

## Suggested Order

1. **T-01 → T-04** — tables, the value object, the name and the tag regex.
   These are the vocabulary everything else uses.
2. **T-05, T-06** — the decomposition and its load-bearing zero baseline.
3. **T-07, T-08** — uniqueness, together with the per-surface dedup that makes it
   correct.
4. **T-09** — enforce the single implementation before any consumer is written,
   so a second copy never exists even transiently.
5. **T-10 → T-12** — the three halves of the #955 fix. **Land them together.**
   Fixing one leaves the aircraft half-consistent: for example the reserve
   becomes correct while the phantom surface remains, which is harder to reason
   about than the original bug.
6. **T-13** last — once T-10 is in place, a miss can only mean a genuine bug, so
   raising becomes the right response.

Blocking edges: T-03 ⇠ T-01 · T-05 ⇠ T-02, T-03 · T-07 ⇠ T-03 ·
T-10, T-11, T-12 ⇠ T-05 · T-13 ⇠ T-10.

## Pending Gaps (🔴)

- **#955 must be fixed as one change (T-10, T-11, T-12).** Three services, one
  root cause. Partial fixes create states that are harder to diagnose than the
  original.
- **`sanitize` is unspecified (T-03).** Which characters does it strip or
  replace? Two wing names differing only in punctuation must not produce the same
  key — otherwise the uniqueness assertion fires on a valid aircraft, or misses a
  real collision depending on iteration order.
- **The `(25.0, 25.0)` fallback (T-13).** Raise, or warn and flag? ADR 0012
  argues a fallback must be visible; but raising changes a soft failure into a
  hard one for aircraft with incomplete TED data.
- **`trim_elevator_deg` encodes the assumption in its column name (T-12).**
  Should it be renamed (`trim_pitch_control_deg`) and joined by a
  `trim_pitch_control_name` column?
- **The retrim's accidental coupling (T-11).** `_find_pitch_control_name` works
  today only because `aerobuildup_trim_service` re-resolves display and role
  names. Once T-11 lands, is that re-resolution still needed, or should the trim
  service require a canonical name?
- **Re-tagging is unguarded.** Nothing asserts that a name is tagged at most
  once; `_ROLE_TAG_RE` exists to parse tags out, but a double-tagged name would
  parse "successfully" with the wrong role.
