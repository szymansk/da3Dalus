# avl-geometry-generation — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] An aeroplane schema exposing wings, x-sections, airfoil references,
      `symmetric` flags, TED roles, hinge points and mixing gains
      (`wing-design`).
- [ ] `control_surface_mixing` with `axis_control_name` and
      `assert_unique_control_names`
      (→ [`../control-surface-naming/tasks.md`](../control-surface-naming/tasks.md)).
- [ ] AeroSandbox for `Airfoil.max_thickness` and `Atmosphere`.
- [ ] NeuralFoil (**optional** — the file must be emittable without CDCL).
- [ ] `avl_geometry_files` table with `UniqueConstraint(aeroplane_id)`.
- [ ] The repository's `.avl` fixtures as regression inputs.
- [ ] **No AVL binary required for any task in this file.**

## Tasks

- [ ] **T-01 — The dataclass hierarchy.**
  Implement every class of [`design.md`](design.md) with `__repr__` emitting its
  block: `AvlGeometryFile`, `AvlSymmetry`, `AvlReference`, `AvlSurface`,
  `AvlSection`, `AvlControl`, `AvlCdcl`, `AvlNaca`, `AvlAfile`,
  `AvlAirfoilInline`, `AvlDesign`, `AvlBody`.
  - Legacy origin: `app/avl/geometry.py`
  - Definition of done: `repr(AvlGeometryFile(...))` is the complete file; each
    block's field order matches the AVL format; there is **no** template or
    separate serialiser anywhere.
  - Confidence: 🟢

- [ ] **T-02 — Conditional emission rules.**
  `CDp` only when `not math.isclose(cdp, 0, abs_tol=1e-12)`; `YDUPLICATE 0.0`
  exactly when `wing.symmetric`, otherwise **omit the block** (do not emit a
  sentinel).
  - Legacy origin: `app/avl/geometry.py`
  - Definition of done: `cdp = 0.0` → no `CDp` line; an asymmetric surface
    contains no `YDUPLICATE` token at all.
  - Confidence: 🟢

- [ ] **T-03 — Airfoil routing (gh-588).**
  `_NACA_RE = ^naca\s*(\d{4,5})$` — integers only. Everything else →
  `_resolve_airfoil_reference` → `AvlAfile`. Last resort `AvlNaca("0012")`.
  - Legacy origin: `app/services/avl_geometry_service.py:52`
  - Definition of done: `"naca2412"` → `NACA 2412`; `"naca23013.5"` → `AFIL`
    (pinned as a named regression test — the old regex crashed AVL with
    `Read error on line N`); an unresolvable name → `NACA 0012` without raising.
  - Confidence: 🟢

- [ ] **T-04 — `CLAF` per section.**
  `1 + 0.77 · max_thickness` from the ASB airfoil; `1.0` on any failure to build
  it.
  - Legacy origin: `app/services/avl_geometry_service.py:102`
  - Definition of done: a 12 % section emits `CLAF 1.0924`; an unbuildable
    airfoil emits `CLAF 1.0`.
  - Confidence: 🟢

- [ ] **T-05 — Control emission with strip duplication.**
  For each x-section carrying a control surface, resolve its axes through
  `control_surface_mixing` and append an `AvlControl` to sections `i` **and**
  `i+1`.
  - Legacy origin: `_build_controls_for_wing` in
    `app/services/avl_geometry_service.py`
  - Definition of done: a one-segment control appears in exactly two `SECTION`
    blocks; a dual-role surface contributes **two** `CONTROL` lines per section
    (`+1` primary, `−1` secondary).
  - Confidence: 🟢

- [ ] **T-06 — Uniqueness: dedup per surface, assert across surfaces.**
  - Legacy origin: `build_avl_geometry_file` +
    `app/services/control_surface_mixing.py:149-164`
  - Definition of done: a cross-surface collision raises `ValueError` **before
    any file text is produced**; repetition within one surface does not raise.
    The rationale (AVL silently collapses duplicate `CONTROL` names into one DOF,
    avl_doc 778-789) must be in a comment — it is not inferable from the code.
  - Confidence: 🟢

- [ ] **T-07 — `SpacingConfig` and the escape hatch.**
  Defaults `n_chord=12`, `c_space=1.0`, `n_span=20`, `s_space=1.0`,
  `auto_optimise=True`; bounds `n_chord ∈ [4, 100]`, `n_span ∈ [4, 200]`. With
  `auto_optimise = False` the config passes through verbatim.
  - Legacy origin: `app/schemas/aeroanalysisschema.py:212-219`
  - Definition of done: out-of-bounds values are rejected by the schema;
    `auto_optimise = False` produces exactly the configured numbers.
  - Confidence: 🟢

- [ ] **T-08 — Heuristic 1: hinge-line chordwise resolution.**
  Any control surface on a surface ⇒ `n_chord = max(n_chord, 16)`.
  - Legacy origin: `app/avl/spacing.py:97`
  - Definition of done: a flapped wing emits `n_chord ≥ 16`; a clean wing keeps
    12.
  - Confidence: 🟢

- [ ] **T-09 — Heuristic 2: minus-sine spanwise spacing.**
  `sweep = atan2(Δx, sqrt(Δy² + Δz²)) < 5°` **and** no interior section at
  `|y| < 1e-6` ⇒ `s_space = −2.0`.
  - Legacy origin: `app/avl/spacing.py:17, :101`
  - Definition of done: a straight wing without a centreline break gets `−2.0`;
    adding an interior section at `y = 0` restores `1.0`; a 10°-swept wing keeps
    `1.0`. A comment must record why: the induced-drag gradient is steepest at
    root and tip.
  - Confidence: 🟢

- [ ] **T-10 — Heuristic 3: spanwise vortex sufficiency (gh-590).**

  ```
  gaps    = [|y[i+1] − y[i]| for consecutive sections if the gap > 1e-9]
  min_gap = min(gaps)                      # coincident sections EXCLUDED
  n_span  = max(n_span, ceil(span / min_gap) + 2)
  ```

  - Legacy origin: `app/avl/spacing.py:43-68`
  - Definition of done: two sections 2 mm apart on a 1 m span raise `n_span`;
    two **coincident** sections (a chord discontinuity) leave `n_span` finite;
    the AVL failure this prevents (`Cannot adjust spanwise spacing at section N`
    / `Insufficient number of spanwise vortices`) is named in a comment.
  - 🟡 Decide the behaviour when **every** gap is ≤ 1e-9 (a fully degenerate
    wing) — the legacy's handling is not documented.
  - Confidence: 🟢

- [ ] **T-11 — `compute_reynolds_number`.**
  `Re = V · chord / ν(altitude)` using the ASB `Atmosphere`.
  - Legacy origin: `app/services/neuralfoil_cdcl_service.py`
  - Definition of done: sea-level values match a hand-computed case; altitude
    changes `ν`.
  - Confidence: 🟢

- [ ] **T-12 — The 3-point NeuralFoil polar.**
  From an α sweep: point 2 at `argmin(CD)` (drag bucket), point 3 at
  `argmax(CL)` (positive stall), point 1 at `argmin(CL)` (negative stall);
  emitted as `CL1 CD1  CL2 CD2  CL3 CD3`. Any non-finite value ⇒ a logged
  warning and an all-zero `AvlCdcl`.
  - Legacy origin: `app/services/neuralfoil_cdcl_service.py`
  - Definition of done: the ordering is asserted explicitly (it is easy to emit
    the three points in sweep order by mistake); NaN yields zeros, never a
    fabricated polar (ADR 0012).
  - Confidence: 🟢

- [ ] **T-13 — The polar cache.**
  `@lru_cache(maxsize=128)` on hashable primitives only: airfoil **name**, `Re`,
  `mach`, α range, `model_size`, `n_crit`, `xtr_upper`, `xtr_lower`,
  `include_360_deg_effects`.
  - Legacy origin: `app/services/neuralfoil_cdcl_service.py:25`
  - Definition of done: two identical requests issue one NeuralFoil call; no
    schema object or airfoil instance appears in the key.
  - 🟡 The key uses the airfoil **name**, so two different geometries sharing a
    name collide; and the cache is process-local.
  - Confidence: 🟢

- [ ] **T-14 — `inject_cdcl`.**
  Walk surfaces and sections in **parallel index order**, mutating in place;
  preserve any section whose `cdcl` is present and not all-zero.
  - Legacy origin: `app/services/avl_geometry_service.py`
  - Definition of done: a hand-written non-zero block survives byte-identically;
    an all-zero block is replaced.
  - 🟡 **Deviation to decide:** the legacy pairs surfaces to wings with `zip` and
    only **warns** on a count mismatch, so injection can be silently incomplete.
    Raise, or report the mismatch in the response.
  - Confidence: 🟢

- [ ] **T-15 — `avl_geometry_files` and the trust rule.**
  One row per aeroplane; `get_user_avl_content` returns the content **only** when
  the row exists **and** `is_user_edited` **and not** `is_dirty`.
  - Legacy origin: `app/models/avl_geometry_file.py:27`,
    `app/services/avl_geometry_service.py`
  - Definition of done: all four `(is_user_edited, is_dirty)` combinations behave
    as specified; a second save updates the same row rather than inserting.
  - Confidence: 🟢

- [ ] **T-16 — Dirty listeners.**
  `after_insert/update/delete` on `WingModel`, `WingXSecModel`, `FuselageModel`
  set `is_dirty = True`.
  - Legacy origin: `app/models/avl_geometry_events.py`
  - Definition of done: a wing x-section update flips the flag **once**.
  - 🟡 Factored out so the event publishes once (`Q-AA-4`, derived).
    Register once; this module should subscribe to `GeometryChanged` instead
    (→ [`../../aero-analysis/retrim-invalidation/tasks.md`](../../aero-analysis/retrim-invalidation/tasks.md)
    T-03).
  - 🟢 **Decided (`Q-AV-4`):** a successful regenerate clears `is_dirty`. Previously only a user `PUT` or a
    regenerate. Decide whether a regenerate-on-read should clear it.
  - Confidence: 🟢

- [ ] **T-17 — The four routes.**
  `GET` (stored row, else generate **without persisting**), `PUT` (save;
  `is_user_edited = True`, `is_dirty = False`), `POST …/regenerate` (delete the
  row, return fresh content), `DELETE` (**204**, 404 when absent).
  - Legacy origin: `app/api/v2/endpoints/aeroplane/avl_geometry.py`
  - Definition of done: matches [`../contracts.md`](../contracts.md) exactly,
    including the 204; a `GET` on a fresh aeroplane leaves the table empty.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Fixture round-trip.** Every `.avl` fixture in the tree parses and
      re-emits into an AVL-acceptable file.
- [ ] **TT-02 — gh-588 regression.** `naca23013.5` → `AFIL`; `naca2412` →
      `NACA`.
- [ ] **TT-03 — Airfoil fallback** → `NACA 0012`, no exception.
- [ ] **TT-04 — `CDp` suppression** at exactly `0.0` and at `1e-13`.
- [ ] **TT-05 — `YDUPLICATE`** present for symmetric, entirely absent otherwise.
- [ ] **TT-06 — `CLAF`** computed value and `1.0` default.
- [ ] **TT-07 — Strip duplication.** One control → two `SECTION` blocks.
- [ ] **TT-08 — Dual-role emission.** Two `CONTROL` lines, `+1` / `−1`,
      secondary baseline `0.0`.
- [ ] **TT-09 — Collision.** Cross-surface duplicate raises before any text;
      intra-surface duplication does not.
- [ ] **TT-10 — Heuristic 1.** Flapped → `n_chord ≥ 16`; clean → 12.
- [ ] **TT-11 — Heuristic 2.** Unswept clean → `−2.0`; centreline break → `1.0`;
      10° sweep → `1.0`.
- [ ] **TT-12 — Heuristic 3.** Tight sections raise `n_span`; coincident
      sections do not (gh-590 regression).
- [ ] **TT-13 — `auto_optimise = False`** passes every value through.
- [ ] **TT-14 — Reynolds number** matches a hand-computed sea-level case and
      varies with altitude.
- [ ] **TT-15 — CDCL point ordering.** Point 2 = `argmin(CD)`, point 3 =
      `argmax(CL)`, point 1 = `argmin(CL)` — asserted explicitly.
- [ ] **TT-16 — CDCL NaN** → all zeros plus a warning.
- [ ] **TT-17 — CDCL preservation.** A non-zero user block survives; an all-zero
      one is replaced.
- [ ] **TT-18 — Cache.** Two identical requests → one NeuralFoil call; the key
      contains no unhashable object.
- [ ] **TT-19 — Trust rule.** All four `(is_user_edited, is_dirty)`
      combinations.
- [ ] **TT-20 — Read does not persist.** `GET` on a fresh aeroplane leaves the
      table empty.
- [ ] **TT-21 — `PUT` clears dirty** and sets user-edited.
- [ ] **TT-22 — Listener** flips `is_dirty` exactly once per geometry write.
- [ ] **TT-23 — Route semantics.** `regenerate` deletes; `DELETE` → 204 / 404.
- [ ] **TT-24 — No binary, no NeuralFoil.** The whole file's tests run with the
      `avl-binary` wheel uninstalled **and** NeuralFoil unavailable (CDCL tests
      stub the service).

## Suggested Order

1. **T-01, T-02** — the emitter and its conditional rules; everything else
   produces input for it.
2. **T-03, T-04** — per-section content.
3. **T-05, T-06** — controls, then uniqueness. T-06 depends on
   `control_surface_mixing`, so
   [`../control-surface-naming/tasks.md`](../control-surface-naming/tasks.md)
   T-01…T-03 should land first.
4. **T-07 → T-10** — spacing, independently testable against synthetic section
   lists.
5. **T-11 → T-14** — CDCL, which is optional and must not be a build dependency.
6. **T-15 → T-17** — persistence, invalidation and transport.

Blocking edges: T-05 ⇠ T-01 · T-06 ⇠ T-05 · T-08…T-10 ⇠ T-07 ·
T-12 ⇠ T-11 · T-14 ⇠ T-12, T-13 · T-17 ⇠ T-15.

## Pending Gaps (🔴)

- **`AvlBody` / `BFIL` is never constructed (T-01).** The emitter supports
  fuselages; nothing builds one, so every AVL run is wing-only and every AVL
  result omits fuselage contributions to `Cnb`, `Cm` and drag. Deliberate scope
  or unfinished work? Nothing records the reason.
- **`is_dirty` is never auto-cleared (T-16).** Should a regenerate-on-read clear
  it, or is the flag meant to persist until the user acknowledges the change?
- **Duplicate listener registration (T-16).** Which module owns the three
  geometry listeners?
- **CDCL index pairing (T-14).** A surface/wing count mismatch only warns and
  truncates. Should it raise, or at least surface the mismatch to the caller?
- **CDCL cache key uses the airfoil *name* (T-13).** Two different geometries
  sharing a name collide. Is a content hash warranted?
- **`model_size` divergence.** `"large"` here vs `"xxxlarge"` in the airfoil
  backfill. Which is authoritative for a given airfoil?
- **Fully degenerate wings (T-10).** When every section gap is ≤ 1e-9 there is no
  `min_gap`. What should `n_span` be?
- **Which heuristics fired is not reported.** A surprising panel count cannot be
  explained from the output. Should the response carry the applied rules?
