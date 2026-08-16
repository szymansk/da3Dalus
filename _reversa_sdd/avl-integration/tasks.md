# avl-integration — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Nested use cases carry their own task lists:
> [`avl-geometry-generation`](avl-geometry-generation/tasks.md) ·
> [`avl-run-and-parse`](avl-run-and-parse/tasks.md) ·
> [`control-surface-naming`](control-surface-naming/tasks.md).

## Prerequisites

- [ ] The **`avl-binary` wheel** installed (`poetry install`); `avl_path()` then
      resolves without any manual symlink
      (`.claude/rules/worktree-setup.md`). The module must still import when the
      wheel is absent.
- [ ] An aeroplane schema exposing wings, x-sections, airfoil references, TED
      roles, hinge points and mixing gains (`wing-design`).
- [ ] `control_surface_mixing` available as the shared axis-decomposition source
      (gh-772 / ADR 0008).
- [ ] AeroSandbox for `Atmosphere` (ν), `Airfoil.max_thickness` and
      `op.convert_axes`.
- [ ] NeuralFoil for the CDCL polars (optional — the module must work without
      CDCL).
- [ ] `avl_geometry_files` table with `UniqueConstraint(aeroplane_id)`.
- [ ] The `.avl` fixtures in the tree (57 files) available as parser regression
      inputs.

## Tasks

- [ ] **T-01 — The geometry dataclass hierarchy.**
  Implement every class of [`design.md`](design.md) §Geometry emission with
  `__repr__` emitting its AVL block, so `repr(AvlGeometryFile(...))` is the
  complete file. Emit `CDp` only when
  `not math.isclose(cdp, 0, abs_tol=1e-12)`; emit `YDUPLICATE 0.0` exactly when
  `wing.symmetric`, otherwise omit the block.
  - Legacy origin: `app/avl/geometry.py`
  - Definition of done: round-tripping each of the repository's `.avl` fixtures
    through the parser and back reproduces an AVL-acceptable file; AVL loads the
    output without a `Read error on line N`.
  - Confidence: 🟢

- [ ] **T-02 — Airfoil routing (gh-588).**
  `_NACA_RE = ^naca\s*(\d{4,5})$` — **integers only**. Anything else goes to
  `_resolve_airfoil_reference` → `AvlAfile`; the last resort is
  `AvlNaca("0012")`.
  - Legacy origin: `app/services/avl_geometry_service.py:52`
  - Definition of done: `"naca2412"` → `NACA 2412`; `"naca23013.5"` → `AFIL`;
    an unresolvable name → `NACA 0012`; a regression test pins the gh-588 case.
  - Confidence: 🟢

- [ ] **T-03 — `CLAF` per section.**
  `CLAF = 1 + 0.77 · max_thickness` from the ASB airfoil; `1.0` when the airfoil
  cannot be built.
  - Legacy origin: `app/services/avl_geometry_service.py:102`
  - Definition of done: a 12 %-thick section emits `CLAF 1.0924`; an unbuildable
    airfoil emits `CLAF 1.0` without raising.
  - Confidence: 🟢

- [ ] **T-04 — Control emission with strip duplication.**
  Append each x-section's control(s) to sections `i` **and** `i+1`, mirroring
  AeroSandbox so AVL interpolates the deflection across the panel strip.
  - Legacy origin: `_build_controls_for_wing` in
    `app/services/avl_geometry_service.py`
  - Definition of done: a one-segment control appears in exactly two `SECTION`
    blocks.
  - Confidence: 🟢

- [ ] **T-05 — Cross-surface name uniqueness.**
  Dedup **per surface** (repetition inside one surface is legitimate panel
  duplication), then call `assert_unique_control_names` **across** surfaces,
  raising `ValueError` on a collision.
  - Legacy origin: `build_avl_geometry_file` +
    `app/services/control_surface_mixing.py:149-164`
  - Definition of done: two surfaces resolving to the same name raise **before
    any file text is produced**; the same name repeated within one surface does
    not raise. The rationale must be in a comment: AVL silently collapses
    identically named `CONTROL` variables into a single DOF (avl_doc 778-789).
  - Confidence: 🟢

- [ ] **T-06 — Panel-spacing heuristics.**

  ```
  start: SpacingConfig(n_chord=12, c_space=1.0, n_span=20, s_space=1.0,
                       auto_optimise=True)
  1. any control surface        → n_chord = max(n_chord, 16)
  2. sweep = atan2(Δx, sqrt(Δy²+Δz²)) < 5°  AND no interior section at |y| < 1e-6
                                → s_space = −2.0
  3. min_gap over NON-coincident sections (gap > 1e-9)
                                → n_span = max(n_span, ceil(span/min_gap) + 2)
  ```

  - Legacy origin: `app/avl/spacing.py:17, :43-68, :71-106, :97, :101`
  - Definition of done: a flapped wing emits `n_chord ≥ 16`; a straight wing with
    a centreline break keeps `s_space = 1.0`; two sections 2 mm apart on a 1 m
    span raise `n_span`; two **coincident** sections do not drive `n_span` to
    infinity. Rules 2 and 3 must both be skippable via `auto_optimise = False`.
  - Confidence: 🟢

- [ ] **T-07 — CDCL injection.**
  Walk surfaces and sections in **parallel index order**, mutating in place.
  Preserve any section whose `cdcl` is present and not all-zero. Compute
  `Re = V · chord / ν(altitude)` from the ASB `Atmosphere`.
  - Legacy origin: `inject_cdcl` in `app/services/avl_geometry_service.py`
  - Definition of done: a hand-written non-zero `CDCL` survives injection
    byte-identically.
  - 🟢 **Deviation, decided (`Q-AV-5`):** the legacy only warns and truncates on
    a surface/wing count mismatch, leaving the truncated sections with **zero
    CDCL — no viscous drag at all**. Emit a `DesignWarning` (`result_truncated`,
    severity `error`, `P-WARN-0`/ADR 0020) instead, and the run must not be
    presented as a valid viscous result.
  - Confidence: 🟢

- [ ] **T-08 — NeuralFoil 3-point polar.**
  From an α sweep: point 2 at `argmin(CD)` (drag bucket), point 3 at
  `argmax(CL)` (positive stall), point 1 at `argmin(CL)` (negative stall);
  emitted as `CL1 CD1  CL2 CD2  CL3 CD3`. Non-finite values anywhere ⇒ a logged
  warning and an **all-zero** CDCL.
  - Legacy origin: `app/services/neuralfoil_cdcl_service.py`
  - Definition of done: the emitted triple is ordered exactly as above; a NaN in
    the sweep produces zeros, never a fabricated polar.
  - Confidence: 🟢

- [ ] **T-09 — The CDCL cache.**
  `@lru_cache(maxsize=128)` keyed on **hashable primitives only**: airfoil
  **name**, `Re`, `mach`, α range, `model_size`, `n_crit`, `xtr_upper`,
  `xtr_lower`, `include_360_deg_effects`.
  - Legacy origin: `app/services/neuralfoil_cdcl_service.py:25`
  - Definition of done: two identical requests issue one NeuralFoil call; no
    unhashable object (schema, airfoil instance) reaches the key.
  - 🟡 The cache is process-local; a multi-worker deployment recomputes per
    worker.
  - Confidence: 🟢

- [ ] **T-10 — Binary resolution.**
  `avl_binary.avl_path()` → `shutil.which("avl")` → the literal `"avl"`, with the
  import guarded (`except ImportError: _avl_path = None`).
  - Legacy origin: `app/services/avl_runner.py:30-38`
  - Definition of done: a fresh worktree after `poetry install` needs no
    symlink; the module imports cleanly when the wheel is absent.
  - Confidence: 🟢

- [ ] **T-11 — The keystroke builder.**
  Emit the exact sequence in [`design.md`](design.md) §Keystroke protocol,
  including `g 9.81` and the blank line that leaves the mass submenu. `V = 0`
  with non-zero rates logs a warning and zeroes the rates.
  - Legacy origin: `app/services/avl_runner.py:111-175, :143`
  - Definition of done: the generated stdin matches the documented block
    line-for-line; `V = 0` produces zeroed rates and no division by zero.
  - Confidence: 🟢

- [ ] **T-12 — The d-index invariant.**
  `build_control_deflection_commands` and `get_control_surface_index_map`
  perform **the same walk** (`wings → xsecs → control_surfaces`, first
  occurrence wins), so the emitted `d{i} d{i} {δ}` order and the 1-based index
  map cannot drift. Symmetric pairs share one ASB name and collapse to **one**
  d-index.
  - Legacy origin: `app/services/avl_strip_forces.py` (gh-529)
  - Definition of done: a property test asserts
    `commands[i]` always addresses `index_map`'s `i`-th name, for randomly
    generated aircraft; a symmetric aileron pair occupies one d-index.
  - 🟢 **`R1` RESOLVED — delete `build_yduplicate_sign_map`; do NOT wire it into this
    task as the sign source without resolving the open defect first.** Measured
    2026-08-15 (`Q-AV-3`/`Q-AV-4`): the legacy function is called **only** from
    the now-deleted `avl_artefact_service`, so the live strip-force path takes
    the index map but never applies a sign map. Whether mirrored-surface strip
    forces are correctly signed into spar loads is an open investigation — see
    [`avl-run-and-parse/tasks.md`](avl-run-and-parse/tasks.md) T-04.
  - Confidence: 🟢 for the index invariant, 🔴 for the mirrored-sign question

- [ ] **T-13 — Subprocess execution.**
  Write `airplane.avl` into a `TemporaryDirectory` (or a caller-supplied
  `working_directory`), spawn `[avl_command, "airplane.avl"]` with piped stdio,
  `communicate(keystrokes, timeout)`. `TimeoutExpired` → kill →
  `RuntimeError("AVL timed out after Ns")`. A missing `output.txt` →
  `FileNotFoundError` including the first **500** characters of stdout. A
  non-zero return code is **logged only**.
  - Legacy origin: `app/services/avl_runner.py:280-368, :302-303`, default
    timeout `:102`
  - Definition of done: a hanging AVL is killed and raises with the elapsed
    limit; a geometry error produces an exception carrying the stdout excerpt;
    two concurrent runs never collide on `airplane.avl`.
  - Confidence: 🟢

- [ ] **T-14 — `parse_stability_output`.**
  Scan for `" = "`, read the key backwards and the value forwards to the next
  space/newline, `float()` or `NaN`, **first occurrence wins**.
  - Legacy origin: `app/services/avl_runner.py:41-83`
  - Definition of done: it reproduces `asb.AVL.parse_unformatted_data_output` on
    every `.avl` fixture output; a repeated key yields the first value; an
    unparseable value yields `NaN`, not an exception.
  - Confidence: 🟢

- [ ] **T-15 — `_post_process_results`.**
  Implement the transform block verbatim:

  ```
  lowercase Alpha/Beta/Mach ; strip the "tot" suffix (CLtot → CL, Cl'tot → Cl')
  p = (pb/2V)·2V/b     q = (qc/2V)·2V/c     r = (rb/2V)·2V/b
  L = q·S·CL   Y = q·S·CY   D = q·S·CD
  l_b = q·S·b·Cl   m_b = q·S·c·Cm   n_b = q·S·b·Cn
  spiral parameter = "Clb Cnr / Clr Cnb"     (NaN on ZeroDivisionError)
  F_w = [−D, Y, −L] → F_b → F_g  and  M_b → M_g, M_w   via op.convert_axes
  ```

  - Legacy origin: `app/services/avl_runner.py:177-257`
  - Definition of done: the dimensional values match a hand-computed case; a
    zero denominator in the spiral parameter yields `NaN`, not an exception.
  - Confidence: 🟢

- [ ] **T-16 — `parse_strip_forces_output`.**
  The line state machine of [`design.md`](design.md) §Strip parsing, over the 15
  `_STRIP_COLUMNS`. Rows with fewer than 15 values are dropped.
  - Legacy origin: `app/services/avl_strip_forces.py:15-31, :127-147`
  - Definition of done: the output dict is **byte-for-byte** what
    `vlm_strip_forces` produces, so `_strip_surfaces_from_result` consumes either
    unchanged (this compatibility is what makes ADR 0003 possible).
  - 🟡 Short rows are dropped **silently**; consider counting and reporting them.
  - Confidence: 🟢

- [ ] **T-17 — Indirect-constraint commands.**

  ```
  _VARIABLE_TO_AVL = {alpha: a, beta: b, roll_rate: r, pitch_rate: p, yaw_rate: y}
  otherwise: the variable must be a control-surface name → "d{index}"
  unknown → ValueError listing BOTH valid sets
  TrimTarget values ARE AVL tokens: C, S, PM, RM, YM
  ```

  Inject them as `extra_keystrokes` **before** the `x` execute command.
  - Legacy origin: `build_indirect_constraint_commands` in
    `app/services/avl_strip_forces.py`; `AVLRunner.run_trim`
  - Definition of done: `pitch_rate` → `p`; a control name resolves through the
    index map; an unknown variable's error message names both sets.
  - Confidence: 🟢

- [ ] **T-18 — `trim_with_avl` result categorisation.**
  Split the flat result dict into `aero_coefficients`, `forces_and_moments`,
  `trimmed_state`, `stability_derivatives` and `trimmed_deflections` (keys ∈ the
  control-index map). Map `ValueError → 422`,
  `FileNotFoundError`/`RuntimeError → 500`. Compute enrichment best-effort for
  converged results.
  - Legacy origin: `app/services/avl_trim_service.py`
  - Definition of done: every raw key lands in exactly one block; an enrichment
    failure still returns the trim.
  - 🟢 **Deviation required, and the root cause is now known (`Q-AV-1`):** the
    legacy declares `converged = ("CL" in raw)`, and a non-converged AVL run
    (Newton loop past `EPS = 2e-5` rad, `Avl/src/aoper.f:1298-1319`) blocks its
    `ST` output command entirely (`LSOL = .FALSE.`), so no stability file is
    written and the runner raises `FileNotFoundError` before this line is ever
    reached — the inference is unreachable-false, not just weak. Parse AVL's
    own `Trim convergence failed` stdout marker (already captured by the
    runner) and map a non-converged trim to **422** with AVL's message,
    replacing today's 500 ("check avl_command and input geometry").
  - Confidence: 🟢 for the categorisation, 🟢 for the `converged` root cause and
    fix (not yet implemented)

- [ ] **T-19 — REVERSED: no replay artefact; parse the control-index map from
  every run instead (gh-529, `Q-AV-3`/`Q-AV-4`, ANSWERED by the maintainer
  2026-08-15).** `compute_geometry_hash`, `build_artefact`, `verify_avl_replay`
  and `AvlReplayMismatch` are **withdrawn and deleted** (`P-DEAD-0`/ADR 0021 —
  measured 2026-08-15, no production callers). AVL prints the surface name
  alongside the index in every output block (`STITLE(N)`,
  `src/aoutput.f:168-174`, `FS` `:290-323`, machine-readable `STRP`
  `src/aoutmrf.f:273-278`), so the index → name map is recoverable from every
  result and is parsed fresh per run — see
  [`avl-run-and-parse/tasks.md`](avl-run-and-parse/tasks.md) T-16/T-17 for the
  replacement task.
  - Legacy origin: `app/services/avl_artefact_service.py`,
    `app/schemas/avl_artefact.py` — **delete both files**.
  - Definition of done: neither file exists in the target implementation; a
    geometry edit between two runs produces correct results with no snapshot
    or hash check anywhere, because nothing was cached to go stale.
  - Confidence: 🟢 — decided, not yet executed

- [ ] **T-20 — Stored-geometry lifecycle.**
  One row per aeroplane (`UniqueConstraint(aeroplane_id)`, FK
  `ON DELETE CASCADE`, `cascade="all, delete-orphan"`) with `content`,
  `is_dirty`, `is_user_edited`. `get_user_avl_content` returns the content
  **only** when the row exists **and** `is_user_edited` **and not** `is_dirty`.
  - Legacy origin: `app/models/avl_geometry_file.py:27`,
    `app/services/avl_geometry_service.py`
  - Definition of done: a dirty row causes the caller to regenerate; a second
    save updates the same row rather than inserting.
  - 🟢 **Deviation, and it is now decided (`Q-AV-4`, ANSWERED by the maintainer
    2026-08-15):** `is_dirty` was never auto-cleared — only a user `PUT` or a
    regenerate reset it, so the user-edited file was bypassed permanently
    after any geometry edit. **Decision: a successful `POST …/regenerate`
    clears `is_dirty` automatically.** Not yet implemented.
  - Confidence: 🟢

- [ ] **T-21 — Geometry dirty listeners.**
  `after_insert/update/delete` on `WingModel`, `WingXSecModel`, `FuselageModel`
  set `avl_geometry_files.is_dirty = True`.
  - Legacy origin: `app/models/avl_geometry_events.py`
  - Definition of done: a wing edit flips the flag once.
  - 🟡 The legacy **also** attaches these three models in `stability_events.py` — factored out by `Q-AA-4`,
    so every geometry write fires twice. Register once, in one owning module;
    this module should subscribe to `GeometryChanged` rather than attach its own
    listeners
    (→ [`../aero-analysis/retrim-invalidation/tasks.md`](../aero-analysis/retrim-invalidation/tasks.md)
    T-03).
  - Confidence: 🟢

- [ ] **T-22 — The four HTTP routes.**
  `GET` / `PUT` / `POST …/regenerate` / `DELETE` on
  `/aeroplanes/{aeroplane_id}/avl-geometry`, with the status codes and
  semantics in [`contracts.md`](contracts.md) (note `DELETE` → **204**).
  - Legacy origin: `app/api/v2/endpoints/aeroplane/avl_geometry.py`
  - Definition of done: `GET` on an aeroplane with no row generates on the fly
    without persisting; `PUT` sets `is_user_edited` and clears `is_dirty`;
    `regenerate` deletes the row; `DELETE` on an absent row is 404.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Fixture round-trip.** Each of the repository's `.avl` fixtures
      parses and re-emits into an AVL-acceptable file.
- [ ] **TT-02 — gh-588 regression.** `naca23013.5` → `AFIL`, never `NACA`.
- [ ] **TT-03 — `CDp` suppression** at `cdp = 0.0`.
- [ ] **TT-04 — `YDUPLICATE` presence** exactly for symmetric wings.
- [ ] **TT-05 — `CLAF`** value and its `1.0` default.
- [ ] **TT-06 — Strip duplication.** One control → two `SECTION` blocks.
- [ ] **TT-07 — Name collision.** Cross-surface duplicate raises **before** any
      text is produced; intra-surface duplication does not raise.
- [ ] **TT-08 — Dual-role emission.** Two `CONTROL` variables, `+1`/`−1`,
      secondary baseline `0.0`.
- [ ] **TT-09 — Spacing rules.** Each of the three rules fires and is skippable
      via `auto_optimise = False`.
- [ ] **TT-10 — Coincident sections** do not explode `n_span` (gh-590
      regression).
- [ ] **TT-11 — CDCL preservation.** A user-edited non-zero block survives.
- [ ] **TT-12 — CDCL NaN** → all zeros plus a warning.
- [ ] **TT-13 — CDCL cache.** Two identical requests → one NeuralFoil call; the
      key contains no unhashable object.
- [ ] **TT-14 — Binary resolution.** Wheel present → its path; wheel absent →
      `PATH`; neither → the literal `"avl"`, and the module still imports.
- [ ] **TT-15 — Keystrokes.** Byte-compare against the documented block;
      `V = 0` zeroes the rates.
- [ ] **TT-16 — d-index property test.** Command order and index map agree for
      randomly generated aircraft; symmetric pairs occupy one index.
- [ ] **TT-17 — Timeout.** A hanging process is killed; the message names the
      limit.
- [ ] **TT-18 — Missing output.** `FileNotFoundError` carrying the first 500
      chars of stdout.
- [ ] **TT-19 — Non-zero exit tolerated** when `output.txt` exists.
- [ ] **TT-20 — Stability parsing.** First-occurrence-wins; `NaN` on
      unparseable; `CLtot` → `CL`.
- [ ] **TT-21 — Post-processing.** Dimensional values match a hand-computed
      case; the spiral parameter is `NaN` on a zero denominator.
- [ ] **TT-22 — Strip parsing compatibility.** The dict is byte-identical in
      shape to `vlm_strip_forces` output; a 13-column row is dropped without
      shifting the remaining rows.
- [ ] **TT-23 — Trim constraints.** Axis tokens map correctly; a control name
      resolves through the index map; an unknown variable's error lists both
      sets.
- [ ] **TT-24 — `converged` (T-18 deviation).** A run whose Newton loop fails
      to satisfy `EPS` writes no stability file and reports `converged = false`
      via 422 with AVL's `Trim convergence failed` message, not a 500.
- [ ] **TT-25 — REMOVED.** ~~Replay hash~~ — no hash exists to test
      (`Q-AV-3`/`Q-AV-4`); superseded by the index-map-from-output parsing test
      in [`avl-run-and-parse/tasks.md`](avl-run-and-parse/tasks.md) (new test
      task under §Control-index parsing).
- [ ] **TT-26 — Stored-file consumption rule.** All four combinations of
      `(is_user_edited, is_dirty)`.
- [ ] **TT-27 — Route semantics.** `GET` without a row does not persist;
      `regenerate` deletes; `DELETE` → 204 / 404.
- [ ] **TT-28 — No-AVL environment.** Every test above that does not actually
      execute the binary runs with the wheel uninstalled (import guards, error
      paths, emitters and parsers are all binary-free).

## Data Migration Tasks

- [ ] **TM-01 — `avl_geometry_files`** with `UniqueConstraint(aeroplane_id)`, FK
      `ON DELETE CASCADE`, `content` Text, `is_dirty` / `is_user_edited` Boolean
      defaulting to `False`, `created_at` / `updated_at`.
- [ ] **TM-02 — REMOVED.** ~~No migration for artefacts~~ — moot: `AvlArtefact`
      is deleted (`Q-AV-3`/`Q-AV-4`), not wired, so no table decision is
      needed.

## Suggested Order

1. **T-01 → T-03** — the emitter and airfoil routing are the foundation and are
   testable with no binary at all.
2. **T-04, T-05** — controls, then the uniqueness assertion. T-05 depends on
   `control_surface_mixing`
   (→ [`control-surface-naming/tasks.md`](control-surface-naming/tasks.md)).
3. **T-06** — spacing, independent of controls but applied to the same surfaces.
4. **T-07 → T-09** — CDCL, which is optional; the module must be complete
   without it.
5. **T-10 → T-13** — the runner: resolve, build keystrokes, guarantee the
   d-index invariant, then execute. T-12 must land before T-13 so the first real
   run cannot mis-map a deflection.
6. **T-14 → T-16** — parsers, against the fixtures.
7. **T-17, T-18** — trim, on top of a working runner and index map.
8. **T-19** — REVERSED: confirm the index map is parsed per run and no
   artefact is built (`Q-AV-3`/`Q-AV-4`), once the index map is stable.
9. **T-20 → T-22** — persistence, invalidation and transport.

Blocking edges: T-05 ⇠ T-04 · T-12 ⇠ T-04 · T-13 ⇠ T-10, T-11, T-12 ·
T-14, T-15, T-16 ⇠ T-13 · T-17, T-18 ⇠ T-12, T-13 · T-19 ⇠ T-12 ·
T-22 ⇠ T-20, T-01.

## Pending Gaps (🔴)

- ~~**`converged` is inferred from `"CL" in raw` (T-18).**~~ **RESOLVED
  (`Q-AV-1`).** AVL's actual signal is the `Trim convergence failed` stdout
  marker; residual-checking is not needed as a substitute because a
  non-converged run never reaches the inference at all (no stability file is
  written). Parse the marker; map to 422. Not yet implemented.
- ~~**`AvlBody` / `BFIL` exists but nothing builds one.**~~ **RESOLVED
  (`Q-AV-2`, ANSWERED by the maintainer 2026-08-15): deliberate and correct —
  AeroSandbox is the sole `Cnb` authority (ADR 0022), AVL's body model is
  unvalidated and one-way-coupled.** What this question *did* surface: a
  `y_root ≥ 0` invariant violation on the `Wing` surface (self-overlapping
  `YDUPLICATE` mirror, corrupting `Sref`/`CDi`/`e`) — see
  [`requirements.md`](requirements.md) `BR-AV2F`. Tracked as work, not a gap.
- ~~**`.mass` and `.run` files are never produced.**~~ **RESOLVED (`Q-AV-8`,
  ANSWERED by the maintainer 2026-08-15): stays out of scope for now, but
  deferred behind a genuine precondition (a per-component mass model with
  positions), not dropped.** Ship the spiral criterion and phugoid
  approximation instead (→ `aero-analysis`), which need no file support.
- ~~**`AvlArtefact` is dead code (T-19).**~~ **RESOLVED (`Q-AV-3`/`Q-AV-4`):
  delete it.** The index map is parsed per run instead; no persistence
  question arises because there is nothing to persist.
- ~~**`is_dirty` is never auto-cleared (T-20).**~~ **RESOLVED (`Q-AV-4`):
  yes — a successful `POST …/regenerate` clears it automatically.** Not yet
  implemented.
- **Duplicate listener registration (T-21).** Which module owns the three
  geometry listeners? (out of this fold-back's question set, still open)
- ~~**CDCL surface/wing pairing is by index (T-07).**~~ **RESOLVED (`Q-AV-5`):
  raise a `DesignWarning` (`result_truncated`, severity `error`) instead of
  warning-and-truncating** (`P-WARN-0`/ADR 0020). Not yet implemented.
- **`model_size` divergence.** This module defaults to `"large"`; the airfoil
  backfill uses `"xxxlarge"`. A section's CDCL and the catalogue's polar for the
  same airfoil are therefore not necessarily consistent. Which is authoritative?
  (out of this fold-back's question set, still open)
- ~~**`analyze_wing` never consults the stored file** while `analyze_airplane`
  does.~~ **RESOLVED (`Q-AV-6`, expert consensus endorsed by the maintainer
  2026-08-14): confirmed inconsistency; fix is to merge the stored
  `SURFACE` block with a freshly regenerated pruned-wing header, not to swap
  wholesale.** See [`requirements.md`](requirements.md) `BR-AV23`. Not yet
  implemented.
- **`build_yduplicate_sign_map` mirrored strip-force sign — R1.** Held pending
  a defect investigation (`Q-AV-3`/`Q-AV-4`): its only caller is the now-deleted
  artefact service, so the live strip-force path applies no sign map at all.
  Whether mirrored surfaces are summed with the wrong sign into spar loads
  (`/spanwise_loads_with_sizing`) is unresolved. **This is the one item in
  this fold-back — now resolved. 🟢**
- **Short strip rows are dropped silently (T-16).** A truncated AVL table is
  indistinguishable from a shorter wing.
