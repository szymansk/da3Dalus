# avl-run-and-parse — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `.avl` text available from
      [`../avl-geometry-generation/`](../avl-geometry-generation/tasks.md).
- [ ] `control_surface_mixing` names, so the index map keys match what the file
      contains
      (→ [`../control-surface-naming/tasks.md`](../control-surface-naming/tasks.md)).
- [ ] The `avl-binary` wheel for the integration tests; **every unit test in this
      file must pass without it**.
- [ ] AeroSandbox for `op.convert_axes`.
- [ ] The repository's `.avl` fixtures and captured AVL outputs as parser
      regression inputs.

## Tasks

- [ ] **T-01 — Binary resolution.**

  ```
  1. avl_binary.avl_path()          # import guarded: except ImportError → None
  2. shutil.which("avl")
  3. "avl"                          # the literal string
  ```

  - Legacy origin: `app/services/avl_runner.py:30-38`
  - Definition of done: the module imports cleanly with the wheel uninstalled;
    a worktree after `poetry install` resolves to the wheel path with no manual
    symlink (`.claude/rules/worktree-setup.md`).
  - Confidence: 🟢

- [ ] **T-02 — `get_control_surface_index_map`.**
  Walk `wings → xsecs → control_surfaces`, keeping the **first occurrence** of
  each name, assigning 1-based indices.
  - Legacy origin: `app/services/avl_strip_forces.py`
  - Definition of done: a symmetric pair sharing one name occupies **one** index;
    the order is deterministic for a given schema.
  - Confidence: 🟢

- [ ] **T-03 — `build_control_deflection_commands`.**
  The **same walk** as T-02, emitting `d{i} d{i} {δ}`; overrides applied **by
  name**.
  - Legacy origin: `app/services/avl_strip_forces.py` (replaces AeroSandbox's
    hard-coded `d1 d1 1`)
  - Definition of done: a property test over randomly generated aircraft asserts
    that command `i` always addresses the index map's `i`-th name; an override
    keyed by an absent name emits nothing and shifts no index.
  - Confidence: 🟢

- [ ] **T-04 — `build_yduplicate_sign_map`.**
  `symmetric = True → +1.0`, otherwise `−1.0`.
  - Legacy origin: `app/services/avl_strip_forces.py` (gh-529)
  - Definition of done: every name in the index map has a sign; the sign is a
    **flag**, never a magnitude (BR-10).
  - Confidence: 🟢

- [ ] **T-05 — `_build_keystrokes`.**
  Emit the sequence in [`design.md`](design.md) §Keystroke construction exactly,
  including `g 9.81` and the **blank line** that leaves the mass submenu.
  Non-dimensionalise the rates as `p·b/2V`, `q·c/2V`, `r·b/2V`. With `V = 0` and
  any non-zero rate: log a warning and emit zeros.
  - Legacy origin: `app/services/avl_runner.py:111-175, :143`
  - Definition of done: a byte-comparison against the documented block for a
    fixture operating point; `V = 0` produces zeroed rates and no division by
    zero. A comment must record why the blank line exists — without it every
    following keystroke is consumed as mass input.
  - Confidence: 🟢

- [ ] **T-06 — Subprocess execution.**
  Write `airplane.avl` into a `TemporaryDirectory` (or the caller's
  `working_directory`); spawn `[command, "airplane.avl"]` with piped stdio and
  `cwd=dir`; `communicate(keystrokes, timeout)`. `TimeoutExpired` → `kill()` →
  `RuntimeError(f"AVL timed out after {t}s")`.
  - Legacy origin: `app/services/avl_runner.py:280-368`, filenames `:302-303`,
    default timeout `:102`
  - Definition of done: a deliberately hanging fake binary is killed and raises
    with the limit named; two concurrent runs never collide on `airplane.avl`;
    a caller-supplied `working_directory` leaves both files behind for
    debugging.
  - Confidence: 🟢

- [ ] **T-07 — Missing-output and exit-code handling.**
  A missing `output.txt` raises `FileNotFoundError` including the **first 500**
  characters of stdout. A non-zero return code is **logged only**.
  - Legacy origin: `app/services/avl_runner.py:280-368`
  - Definition of done: a geometry-error run produces an exception carrying the
    stdout excerpt (this is the primary diagnostic for a rejected file); a
    non-zero exit with a valid `output.txt` parses normally.
  - 🟡 The leniency is deliberate (AVL routinely exits non-zero) but means a
    genuinely failed run that wrote an output is treated as a success. Consider
    recording the exit code on the result.
  - Confidence: 🟢

- [ ] **T-08 — `parse_stability_output`.**
  Scan for `" = "`, read the key backwards and the value forwards to the next
  space/newline, `float()` or `NaN`, **first occurrence wins**.
  - Legacy origin: `app/services/avl_runner.py:41-83`
  - Definition of done: it reproduces
    `asb.AVL.parse_unformatted_data_output` on every captured AVL output in the
    fixtures; a repeated key yields the first value; an unparseable value yields
    `NaN` without raising. Do **not** import the ASB implementation — the
    re-implementation is deliberate insulation from ASB internals.
  - Confidence: 🟢

- [ ] **T-09 — `_post_process_results`.**

  ```
  lowercase Alpha/Beta/Mach ; strip the "tot" suffix (CLtot → CL, Cl'tot → Cl')
  p = (pb/2V)·2V/b     q = (qc/2V)·2V/c     r = (rb/2V)·2V/b
  L = q·S·CL   Y = q·S·CY   D = q·S·CD
  l_b = q·S·b·Cl   m_b = q·S·c·Cm   n_b = q·S·b·Cn
  spiral parameter = "Clb Cnr / Clr Cnb"       (NaN on ZeroDivisionError)
  F_w = [−D, Y, −L] → F_b → F_g  and  M_b → M_g, M_w   via op.convert_axes
  ```

  - Legacy origin: `app/services/avl_runner.py:177-257`
  - Definition of done: the dimensional values match a hand-computed case; a
    zero denominator yields `NaN` rather than an exception; the wind→body→geometry
    chain is exercised for a non-zero β.
  - Confidence: 🟢

- [ ] **T-10 — `parse_strip_forces_output`.**
  The line state machine of [`design.md`](design.md) §`FS` strip table over the
  15 `_STRIP_COLUMNS`. Rows with fewer than 15 values are dropped.
  - Legacy origin: `app/services/avl_strip_forces.py:15-31, :127-147`
  - Definition of done: the output dict is **byte-for-byte** the shape
    `vlm_strip_forces` produces, so `_strip_surfaces_from_result` in
    `aero-analysis` consumes either unchanged — assert this with a shared
    structural test over both producers.
  - 🟡 Short rows are dropped **silently**; consider counting them and reporting
    the count, so a truncated table is distinguishable from a shorter wing.
  - Confidence: 🟢

- [ ] **T-11 — `build_indirect_constraint_commands`.**

  ```
  _VARIABLE_TO_AVL = {alpha: a, beta: b, roll_rate: r, pitch_rate: p, yaw_rate: y}
  otherwise: the variable must be a control-surface name → "d{index}"
  unknown → ValueError listing BOTH valid sets
  emitted: "<variable> <target> <value>"     # target.value IS the AVL token
  ```

  - Legacy origin: `app/services/avl_strip_forces.py`
  - Definition of done: `pitch_rate` + `PITCHING_MOMENT` + `0` → `"p PM 0"`; a
    control at index 2 → a command starting with `"d2"`; an unknown variable's
    error names both the axis tokens and the available control names.
  - Confidence: 🟢

- [ ] **T-12 — `TrimConstraint` / `TrimTarget` / `AVLTrimResult` schemas.**
  `variable` matches `^[a-zA-Z][a-zA-Z0-9_]*$` when it is a control name;
  `TrimTarget` values **are** AVL's tokens
  (`C`, `S`, `PM`, `RM`, `YM`); `value` defaults to `0.0`.
  - Legacy origin: `app/schemas/aeroanalysisschema.py:22-97`
  - Definition of done: the enum's `.value` is used verbatim in the keystroke —
    a test asserts no translation table exists between the enum and the emitted
    token.
  - Confidence: 🟢

- [ ] **T-13 — `run_trim`.**
  Inject the constraint commands as `extra_keystrokes` **before** the `x`
  execute command.
  - Legacy origin: `app/services/avl_runner.py`
  - Definition of done: the constraint lines appear before `x` in the generated
    stdin.
  - Confidence: 🟢

- [ ] **T-14 — `trim_with_avl` result categorisation.**
  Split the flat dict into `aero_coefficients`
  (`CL CD CY Cm Cl Cn CDind CDff e CLff CYff`), `forces_and_moments`
  (`L D Y l_b m_b n_b`), `trimmed_state` (`alpha beta mach`),
  `stability_derivatives`
  (`CL_a CL_b CY_a CY_b Cm_a Cn_b Cl_b Clb Cnr Clr Cnb`) and
  `trimmed_deflections` (keys ∈ the index map). Keep `raw_results`. Map
  `ValueError → 422`, `FileNotFoundError` / `RuntimeError → 500`. Compute
  enrichment best-effort for converged results.
  - Legacy origin: `app/services/avl_trim_service.py`
  - Definition of done: every raw key lands in exactly one block; an enrichment
    failure still returns the trim with HTTP 200.
  - Confidence: 🟢

- [ ] **T-15 — A real convergence verdict.**
  - Legacy origin: `app/services/avl_trim_service.py` (`converged = "CL" in raw`)
  - Definition of done: a run that printed coefficients but did **not** satisfy
    its constraints reports `converged = false`. Minimum viable implementation:
    evaluate each `TrimConstraint`'s residual from the parsed results against its
    target within a stated tolerance, and report the residuals alongside the
    verdict.
  - Confidence: 🟡 (deliberate deviation; the legacy behaviour is a confirmed
    defect)

- [ ] **T-16 — `compute_geometry_hash` (gh-529).**
  `sha256(json(per wing_index → per xsec_index → [(name, symmetric,
  round(hinge_point, 6))]))` — **coordinates excluded**.
  - Legacy origin: `app/services/avl_artefact_service.py`
  - Definition of done: moving a section 10 mm aft leaves the hash unchanged;
    renaming a control or flipping `symmetric` changes it. A comment must record
    why coordinates are excluded: they do not affect control indexing and they
    drift on every model edit.
  - Confidence: 🟢

- [ ] **T-17 — `AvlArtefact` and `verify_avl_replay`.**
  Build `{index_snapshot{name_to_index, yduplicate_sign, captured_at,
  geometry_hash}, run_state{alpha, beta, velocity, mach, x_cg, deflections,
  run_case_constraints}, avl_version}`; verify by comparing the hash and then the
  index map, returning `AvlReplayMismatch(reason, expected, actual, details)`.
  - Legacy origin: `app/services/avl_artefact_service.py`,
    `app/schemas/avl_artefact.py`
  - Definition of done: a hash mismatch and an index drift each produce their own
    reason; the caller treats a non-`None` result as a **hard failure**.
  - 🟢 **Do not wire it up — delete it** (`Q-AV-3`/`Q-AV-4`). The map is parsed from AVL's output per run, so the safety gate is
    dead code. Either call it from the AVL analysis and trim paths (and decide
    whether the artefact needs persistence), or delete it.
  - Confidence: 🟢 for the mechanism, 🔴 for its absence from production

## Test Tasks

- [ ] **TT-01 — Import without the wheel.** The runner module imports; resolution
      falls through.
- [ ] **TT-02 — Resolution order.** Wheel present → wheel path; wheel absent but
      `PATH` hit → that path; neither → `"avl"`.
- [ ] **TT-03 — Keystroke byte-comparison** against the documented block for a
      fixture operating point.
- [ ] **TT-04 — Rate non-dimensionalisation** for `p`, `q`, `r`.
- [ ] **TT-05 — `V = 0`** zeroes the rates and logs a warning.
- [ ] **TT-06 — Index-map property test.** Command `i` addresses index-map name
      `i`, over randomly generated aircraft.
- [ ] **TT-07 — Symmetric pair** occupies one d-index with `SgnDup = +1`.
- [ ] **TT-08 — Absent-name override** emits nothing and shifts no index.
- [ ] **TT-09 — Timeout.** A hanging fake binary is killed; the message names the
      limit.
- [ ] **TT-10 — Isolation.** Two concurrent runs each use their own directory.
- [ ] **TT-11 — Missing output.** `FileNotFoundError` carrying the first 500
      chars of stdout.
- [ ] **TT-12 — Non-zero exit** with a valid output parses normally.
- [ ] **TT-13 — Stability parsing.** First-occurrence-wins; `NaN` on
      unparseable; `CLtot` → `CL`; matches ASB's parser on every fixture output.
- [ ] **TT-14 — Post-processing.** Dimensional values match a hand-computed
      case; the spiral parameter is `NaN` on a zero denominator; axis conversion
      is exercised at non-zero β.
- [ ] **TT-15 — Strip-shape compatibility.** A structural test asserts the AVL
      parser and `vlm_strip_forces` produce the same dict shape.
- [ ] **TT-16 — Short strip row** is dropped without shifting the following
      rows.
- [ ] **TT-17 — Constraint mapping.** Axis tokens, `d{index}`, and the unknown
      variable error listing both sets.
- [ ] **TT-18 — `TrimTarget` values are AVL tokens** — no translation table
      exists.
- [ ] **TT-19 — Constraints precede `x`** in the generated stdin.
- [ ] **TT-20 — Result categorisation.** Every raw key in exactly one block; an
      enrichment failure still returns 200.
- [ ] **TT-21 — Convergence (T-15).** A run that printed coefficients but missed
      its constraints reports `converged = false`.
- [ ] **TT-22 — Replay hash.** Coordinate moves are invisible; a control rename
      or `symmetric` flip is not.
- [ ] **TT-23 — Replay verification.** Hash mismatch and index drift produce
      distinct reasons.
- [ ] **TT-24 — Binary-free suite.** Every test above except the explicit
      integration ones runs with the wheel uninstalled, using a fake executable
      script for the process-lifecycle cases.

## Suggested Order

1. **T-01** first — nothing runs without a resolved command, and the import
   guard shapes the module's structure.
2. **T-02 → T-04** — the index map and its consumers. These are pure functions
   over a schema and must be correct before any real run, because a drift here
   applies a deflection to the wrong surface with no error anywhere.
3. **T-05** — keystrokes, on top of T-03's commands.
4. **T-06, T-07** — process lifecycle, testable with a fake executable.
5. **T-08 → T-10** — the parsers, against captured fixture output.
6. **T-11 → T-14** — trim, on top of a working runner and index map.
7. **T-15** — the convergence deviation, once the residuals are available from
   T-08/T-09.
8. **T-16, T-17** — replay artefacts, once the index map is stable.

Blocking edges: T-03 ⇠ T-02 · T-05 ⇠ T-03 · T-06 ⇠ T-01, T-05 ·
T-08, T-09, T-10 ⇠ T-06 · T-11 ⇠ T-02 · T-13 ⇠ T-11 · T-14 ⇠ T-13 ·
T-15 ⇠ T-09, T-14 · T-17 ⇠ T-02, T-16.

## Pending Gaps (🔴)

- **`converged` is inferred (T-15).** What is AVL's actual convergence signal?
  If none is machine-readable, is a constraint-residual check with a stated
  tolerance acceptable, and what tolerance?
- **`AvlArtefact` is dead code (T-17).** Wire it in or delete it. If wired: does
  a replay need to survive the process, i.e. does the artefact need a table?
- **A non-zero exit code is tolerated (T-07).** Should the exit code be recorded
  on the result so a consumer can decide, rather than being log-only?
- **Short strip rows are dropped silently (T-10).** A truncated table looks like
  a shorter wing. Report the dropped count?
- **No AVL health check.** A missing binary fails at request time. Should the
  health endpoint report AVL availability?
- **`.mass` and `.run` files are never produced.** Mass goes through the
  `OPER → m` submenu and run cases through keystrokes. Is file support wanted,
  or should the docs state plainly that it is out of scope?
- **AVL runs are wing-only.** No `BODY` block is ever emitted
  (→ [`../avl-geometry-generation/`](../avl-geometry-generation/tasks.md)), so
  every parsed result omits fuselage contributions — including the `Cnb` that a
  directional-stability check depends on.
- **`op.convert_axes` ties this path to AeroSandbox**, so the "AVL path" is not
  actually ASB-independent. Intended, or worth removing?
