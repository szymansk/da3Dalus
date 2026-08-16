# avl-run-and-parse — Technical Design

> Focuses on HOW this use case is built, read from the legacy code.
> Parent module design: [`../design.md`](../design.md).
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `AVLRunner(avl_command=None, timeout=30)` | — | — | command resolved lazily 🟢 |
| `AVLRunner.run` | `(avl_file_content, operating_point, extra_keystrokes=None, working_directory=None, strip_forces=False)` | results dict | 🟢 |
| `AVLRunner.run_trim` | `(…, constraints)` | results dict | injects constraints before `x` 🟢 |
| `_resolve_default_avl_command` | `()` | `str` | wheel → `PATH` → `"avl"` 🟢 |
| `_build_keystrokes` | `(operating_point, deflection_commands, extra_keystrokes, strip_forces)` | `str` | 🟢 |
| `parse_stability_output` | `(text)` | `dict[str, float]` | first-occurrence-wins 🟢 |
| `_post_process_results` | `(raw, operating_point)` | `dict` | dimensional + axis transforms 🟢 |
| `parse_strip_forces_output` | `(stdout)` | `{surface: {...}}` | 15-column state machine 🟢 |
| `get_control_surface_index_map` | `(plane_schema)` | `{name: 1-based index}` | 🟢 |
| `build_control_deflection_commands` | `(plane_schema, overrides)` | `list[str]` | same walk as the index map 🟢 |
| `build_yduplicate_sign_map` | `(plane_schema)` | `{name: ±1.0}` | 🟢 |
| `build_indirect_constraint_commands` | `(constraints, index_map)` | `list[str]` | 🟢 |
| `trim_with_avl` | `(db, aeroplane_uuid, request)` | `AVLTrimResult` | 🟡 parse the literal verdict (`Q-AV-1`) |
| `compute_geometry_hash` / `verify_avl_replay` | `(airplane)` / `(artefact, airplane)` | `str` / `None \| AvlReplayMismatch` | gh-529 🟢 |

## Main Flow

```
run(avl_file_content, operating_point, extra_keystrokes, working_directory,
    strip_forces):

  1. command = self.avl_command or _resolve_default_avl_command()
         avl_binary.avl_path()          # guarded import; None when absent
         → shutil.which("avl")
         → "avl"
  2. dir = working_directory or TemporaryDirectory()
     write dir/"airplane.avl" = avl_file_content
  3. keystrokes = _build_keystrokes(operating_point,
                                    build_control_deflection_commands(...),
                                    extra_keystrokes, strip_forces)
  4. proc = Popen([command, "airplane.avl"],
                  stdin=PIPE, stdout=PIPE, stderr=PIPE, cwd=dir, text=True)
     out, err = proc.communicate(keystrokes, timeout=self.timeout)
         TimeoutExpired → proc.kill() → RuntimeError(f"AVL timed out after {t}s")
  5. if not exists(dir/"output.txt"):
         raise FileNotFoundError(f"... stdout: {out[:500]}")
     if proc.returncode != 0:  log.warning(...)          # 🟡 tolerated
  6. raw = parse_stability_output(read(dir/"output.txt"))
     if strip_forces:  raw["strip_forces"] = parse_strip_forces_output(out)
  7. return _post_process_results(raw, operating_point)
```

## Keystroke construction 🟢

```
OPER
m
  mn <mach>
  v  <velocity>
  d  <density>
  g  9.81
  <blank line>            # LEAVES the mass submenu — without it every following
                          # keystroke is consumed as mass input
a a <alpha>
b b <beta>
r r <p·b/2V>              # non-dimensional roll rate
p p <q·c/2V>              # non-dimensional pitch rate
y y <r·b/2V>              # non-dimensional yaw rate
d1 d1 <δ1>
d2 d2 <δ2>
…                         # build_control_deflection_commands, in index order
<extra keystrokes>        # trim constraints (run_trim only)
x                         # execute
st output.txt
o                         # overwrite
[fs]                      # strip forces to stdout, only when requested
quit
```

Guard: `V = 0` with any non-zero rate logs a warning and **zeroes the rates**,
because each non-dimensionalisation divides by `V`.

## The d-index invariant 🟢

```
walk = wings → xsecs → control_surfaces, keeping the FIRST occurrence of each name

get_control_surface_index_map(schema)      → {name: 1, 2, 3, …}   (1-based)
build_control_deflection_commands(schema, overrides)
                                           → ["d1 d1 0.0", "d2 d2 -3.5", …]

  · the two functions perform the SAME walk, so index i and command i always
    describe the same control
  · a symmetric pair shares one ASB name and therefore collapses to ONE d-index
    (gh-529 YDUPLICATE dedup)
  · build_yduplicate_sign_map: symmetric → +1.0, else −1.0
  · overrides are applied BY NAME; an override for an absent name is a no-op and
    does not shift any index
```

This coupling replaces AeroSandbox's hard-coded `d1 d1 1`, which assumed a single
control surface at index 1.

## Parsing 🟢

### Stability file

```
parse_stability_output(text):
    for each occurrence of " = " in the text:
        key   = read backwards from the "=" to the preceding whitespace
        value = read forwards from the "=" to the next space or newline
        try:   float(value)
        except: NaN
        FIRST occurrence of a key wins   (later ones are ignored)
```

This deliberately re-implements `asb.AVL.parse_unformatted_data_output` rather
than importing it, so the parser is stable against AeroSandbox internals.

### `FS` strip table

```
state = {surface: None, in_table: False}

line matches  Surface\s+#\s*(\d+)\s+(.*)        → open a new surface dict
line contains "# Chordwise =" / "# Spanwise ="  → metadata
line contains "Surface area  Ssurf ="           → metadata
line starts with "j" AND contains "Xle" AND "cl"→ in_table = True
in_table and line starts with a digit           → split on whitespace
        len(values) == 15 → append a strip row
        otherwise         → DROP silently                        🟡
blank line                                      → in_table = False

_STRIP_COLUMNS = [j, Xle, Yle, Zle, Chord, Area, c_cl, ai, cl_norm,
                  cl, cd, cdv, cm_c/4, cm_LE, C.P.x/c]
```

### Post-processing

```
lowercase Alpha/Beta/Mach
strip the "tot" suffix:  CLtot → CL ,  Cl'tot → Cl'

p = (pb/2V)·2V/b     q = (qc/2V)·2V/c     r = (rb/2V)·2V/b     # re-dimensionalise
L = q·S·CL           Y = q·S·CY           D = q·S·CD
l_b = q·S·b·Cl       m_b = q·S·c·Cm       n_b = q·S·b·Cn
spiral parameter = "Clb Cnr / Clr Cnb"            → NaN on ZeroDivisionError
F_w = [−D, Y, −L]  →  F_b  →  F_g                 via op.convert_axes
M_b                →  M_g, M_w                    via op.convert_axes
```

## Trim flow 🟢

```
build_indirect_constraint_commands(constraints, index_map):
    for c in constraints:
        if c.variable in _VARIABLE_TO_AVL:            # alpha→a beta→b
            var = _VARIABLE_TO_AVL[c.variable]        # roll_rate→r pitch_rate→p
        elif c.variable in index_map:                 # yaw_rate→y
            var = f"d{index_map[c.variable]}"
        else:
            raise ValueError(f"unknown trim variable … valid axes: {…}; "
                             f"valid controls: {…}")
        emit f"{var} {c.target.value} {c.value}"      # target.value IS the AVL token

run_trim(...):  extra_keystrokes = those commands, injected BEFORE "x"

trim_with_avl(...):
    raw = runner.run_trim(...)
    aero_coefficients     = {CL CD CY Cm Cl Cn CDind CDff e CLff CYff} ∩ raw
    forces_and_moments    = {L D Y l_b m_b n_b} ∩ raw
    trimmed_state         = {alpha beta mach} ∩ raw
    stability_derivatives = {CL_a CL_b CY_a CY_b Cm_a Cn_b Cl_b Clb Cnr Clr Cnb} ∩ raw
    trimmed_deflections   = {k: v for k, v in raw if k in index_map}
    converged  = parse 'Trim convergence failed' (Q-AV-1)     # 🟡
    enrichment            = compute_enrichment(...) best-effort when converged
    ValueError → 422 ; FileNotFoundError / RuntimeError → 500
```

## Replay artefacts 🟢

```
compute_geometry_hash(airplane):
    canonical = [
      [ (control.name, control.symmetric, round(control.hinge_point, 6))
        for control in xsec.controls ]
      for wing in airplane.wings for xsec in wing.xsecs
    ]
    return sha256(json(canonical)).hexdigest()
    # coordinates are EXCLUDED: they do not affect control indexing and they
    # drift on every model edit, which would invalidate every artefact

AvlArtefact = {
  index_snapshot: {name_to_index, yduplicate_sign, captured_at, geometry_hash},
  run_state:      {alpha_deg, beta_deg, velocity_mps, mach, x_cg_m,
                   control_deflections_deg, run_case_constraints},
  avl_version:    str,
}

verify_avl_replay(artefact, airplane):
    if compute_geometry_hash(airplane) != artefact.index_snapshot.geometry_hash:
        return AvlReplayMismatch("geometry_hash_mismatch", expected, actual, …)
    if get_control_surface_index_map(airplane) != artefact.index_snapshot.name_to_index:
        return AvlReplayMismatch("index_map_drift", …)
    return None
```

🟢 `verify_avl_replay` is deleted (`Q-AV-3`/`Q-AV-4`); no production path called it.

## Alternative Flows

- **The wheel is not installed.** The guarded import sets `_avl_path = None`;
  resolution falls through to `PATH` and then the literal `"avl"`. The module
  still imports. 🟢
- **No binary anywhere.** `Popen` raises `FileNotFoundError` → 500 at run time,
  not at import time. 🟡
- **`working_directory` supplied by the caller.** The temporary directory is not
  used, and `airplane.avl` / `output.txt` persist after the call — the debugging
  affordance. 🟢
- **`strip_forces = False`.** The `fs` keystroke is omitted and stdout carries
  only AVL's banner and menu echoes. 🟢
- **AVL exits non-zero but wrote `output.txt`.** Parsed normally; the code is
  logged. 🟡
- **A repeated key in the stability file.** The first value wins. 🟢
- **A short strip row.** Dropped; the remaining rows still parse. 🟡
- **A zero denominator in the spiral parameter.** `NaN`. 🟢
- **An unknown trim variable.** `ValueError` listing both valid sets → 422. 🟢
- **A drifted replay artefact.** `AvlReplayMismatch`; the caller must treat it as
  a hard failure. 🟢 (the artefact path is withdrawn — `Q-AV-3`/`Q-AV-4`)

## Dependencies

- **`avl-binary` wheel** — the vendored executable (import-guarded).
- **[`../avl-geometry-generation/`](../avl-geometry-generation/requirements.md)**
  — supplies `avl_file_content`.
- **[`../control-surface-naming/`](../control-surface-naming/requirements.md)** —
  the names that appear in the index map and in `TrimConstraint.variable`.
- **`aero-analysis`** — `analyse_aerodynamics` is the only analysis caller;
  `AnalysisModel.from_avl_dict` consumes the results; `compute_enrichment`
  enriches trims.
- **AeroSandbox** — `op.convert_axes` in post-processing.
- **Python stdlib** — `subprocess`, `tempfile`, `shutil`, `hashlib`, `json`.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| Three-step binary resolution with a guarded import | `avl_runner.py:30-38` | 🟢 |
| The keystroke sequence is the integration surface | `_build_keystrokes:111-175` | 🟢 |
| Rates are zeroed rather than the run being refused at `V = 0` | same | 🟢 |
| One walk produces both the index map and the deflection commands | `avl_strip_forces.py` (gh-529) | 🟢 |
| Symmetric pairs collapse to one d-index | `build_yduplicate_sign_map` | 🟢 |
| Runs are isolated in a `TemporaryDirectory` | `run:280-368` | 🟢 |
| A timeout kills; a missing output raises with a stdout excerpt | same | 🟢 |
| A non-zero exit code is tolerated | same | 🟡 |
| The stability parser is re-implemented rather than imported from ASB | `parse_stability_output:41-83` | 🟢 |
| The strip dict shape is the shared contract with the VLM path | `parse_strip_forces_output` (gh-674) | 🟢 |
| `TrimTarget` enum values **are** AVL tokens | `app/schemas/aeroanalysisschema.py:22-97` | 🟢 |
| The replay hash excludes coordinates | `avl_artefact_service` | 🟢 |
| Convergence read from AVL's literal verdict (`Q-AV-1`) | `avl_trim_service` | 🟡 |

## Internal State

- **Per run:** a `TemporaryDirectory` containing `airplane.avl` and
  `output.txt`. Nothing survives the call unless the caller supplies
  `working_directory`. 🟢
- **`AVLRunner` instance:** `avl_command` and `timeout` only — no connection, no
  warm process, no reuse between runs. 🟢
- **`AvlArtefact`:** 🟢 deleted (`Q-AV-3`/`Q-AV-4`) — parse the index→name map from AVL's output instead of caching it.
- No database state of its own; the stored `.avl` row belongs to
  [`../avl-geometry-generation/`](../avl-geometry-generation/requirements.md).

## Observability

- A timeout raises with the elapsed limit in the message. 🟢
- A missing `output.txt` raises with the first 500 characters of stdout — the
  single most useful diagnostic when AVL rejects a geometry file. 🟢
- 🟡 A non-zero exit code, a `V = 0` rate zeroing and a dropped short strip row
  are **log-only**; the last of these is invisible in the response, so a
  truncated table looks like a shorter wing.
- 🟡 `converged` carries no diagnostic — `Q-AV-1` supplies one: an inferred `True` is indistinguishable
  from a genuine one, and there is no residual report to check it against.
- 🔴 Nothing records the AVL version actually used at run time. **Not addressed by the validation interview.** (The field exists
  on `AvlArtefact`, which nothing builds in production).

## Risks and Gaps

- 🟡 **AVL prints the literal `Trim convergence failed` on stdout** (`Q-AV-1`, resolved by code lookup), so the inference `"CL" in raw` is replaceable with a real verdict. Derived from the lookup rather than decided, so INFERRED.
  The minimum fix is to verify each constraint's residual against its target.
- 🟢 **The artefact service is deleted** (`Q-AV-3`/`Q-AV-4`): AVL prints the surface name alongside the index in every output block (`STITLE(N)`, `src/aoutput.f:168-174`), so the map is parsed per run and never cached — the whole class of drift bugs disappears by construction. Previously dead code — the replay-safety
  gate exists but no production path calls it, so a stored case can be replayed
  against drifted geometry with silently mis-mapped surfaces (epic gh-525,
  finding C4).
- 🟡 **A non-zero exit code is tolerated.** A genuinely failed run that happened
  to write an `output.txt` is parsed as a result.
- 🟡 **Short strip rows are dropped silently**, so a truncated table is
  indistinguishable from a shorter wing.
- 🟡 **A missing binary fails at run time, not at startup.** There is no health
  check that reports "AVL is unavailable" before a user requests an AVL run.
- 🟡 **No warm process or batching.** Every run pays full process startup; this
  is accepted because AVL is off every hot path (ADR 0003), but it caps AVL's
  usefulness for any sweep-like workflow.
- 🟡 **`op.convert_axes` ties post-processing to AeroSandbox**, so the AVL path
  is not actually ASB-free.
- 🟢 **`.mass` / `.run` stay out for now, deferred behind a per-component mass model with positions** (`Q-AV-8`, maintainer-answered); the two free results — the inertia-free spiral criterion and the phugoid — are shipped instead. Products of inertia are settable only via those files, so eigenmodes wait on the precondition rather than being guessed (ADR 0020). Previously never produced — mass goes
  through the `OPER → m` submenu and run cases through keystrokes. A user
  expecting those files will not find them.
