# avl-run-and-parse

> Use-case specification, nested under the module
> [`avl-integration`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: avl-integration
> (Binary resolution, AVLRunner, Strip-force parsing, Indirect-constraint trim,
> Replay artefacts), `_reversa_sdd/data-dictionary.md` §`TrimConstraint` /
> `AVLTrimResult` / `AvlArtefact`.

## Overview

`avl-run-and-parse` is the subprocess side of AVL: resolving the vendored
binary, driving AVL's interactive keystroke menus, running it under a timeout in
a temporary directory, parsing the unformatted stability file and the `FS` strip
table, post-processing the raw scalars into dimensional forces and moments, and
trimming through AVL's native indirect constraints. It also owns the replay
artefact that makes a stored AVL case safe to re-run. 🟢

## Responsibilities

- Resolve the AVL executable through a three-step chain. 🟢
- Build the keystroke sequence for a given operating point, including
  non-dimensional rates, control deflections and trim constraints. 🟢
- Guarantee that the emitted `d{i}` order matches the 1-based control-index map.
  🟢
- Run the subprocess in an isolated directory under a timeout, killing it on
  expiry. 🟢
- Parse the stability output (`first occurrence wins`) and the 15-column `FS`
  strip table. 🟢
- Post-process into dimensional forces, moments, body rates and axis transforms.
  🟢
- Map a `TrimConstraint` to AVL's `<variable> <target> <value>` form and
  categorise the trim result. 🟢
- Snapshot and verify a replay artefact (index map + geometry hash). 🟢

**Explicitly NOT this use case's responsibility:** producing the `.avl` text
(→ [`../avl-geometry-generation/`](../avl-geometry-generation/requirements.md)),
the control-name decomposition
(→ [`../control-surface-naming/`](../control-surface-naming/requirements.md)),
the `AnalysisModel` envelope and trim enrichment (→ `aero-analysis`).

## Business Rules

- **BR-AV11 — Binary resolution is a three-step chain.** 🟢
  `_resolve_default_avl_command` (`avl_runner.py:30-38`): the `avl_binary`
  wheel's `avl_path()` → `shutil.which("avl")` → the literal string `"avl"`. The
  import is guarded (`except ImportError: _avl_path = None`), so the module
  imports cleanly without the wheel. The wheel is the documented delivery
  mechanism (`.claude/rules/worktree-setup.md`) — **no manual symlink is needed
  after `poetry install`**.
- **BR-AV12 — The keystroke protocol is the API.** 🟢
  `_build_keystrokes` (`:111-175`):

  ```
  OPER
  m  →  mn <mach>, v <V>, d <ρ>, g 9.81, <blank>
  a a <alpha>   b b <beta>
  r r <p·b/2V>  p p <q·c/2V>  y y <r·b/2V>       # non-dimensional rates
  d1 d1 <δ1>    d2 d2 <δ2> …                     # in index-map order
  <extra keystrokes>                             # trim constraints
  x                                              # execute
  st <output.txt> o                              # write the stability file, overwrite
  [fs]                                           # strip forces to stdout
  quit
  ```

  `V = 0` with non-zero rates **logs a warning and zeroes the rates** — the
  non-dimensionalisation would otherwise divide by zero.
- **BR-AV13 — The d-index order is derived once and shared.** 🟢
  `build_control_deflection_commands` replaces AeroSandbox's hard-coded
  `d1 d1 1`: it walks `wings → xsecs → control_surfaces`, keeps the **first
  occurrence** of each name, applies overrides by name and emits
  `d{i} d{i} {δ}` in that order — **the same walk** that
  `get_control_surface_index_map` uses to assign 1-based indices, so the two can
  never drift. Symmetric pairs share one ASB name and therefore collapse to
  **one** AVL d-index (gh-529 YDUPLICATE dedup); their `SgnDup` comes from
  `build_yduplicate_sign_map` (`symmetric=True → +1`, else `−1`).
- **BR-AV14 — Timeouts kill; a missing output raises; a non-zero exit only
  logs.** 🟢 (`run`, `:280-368`) `airplane.avl` is written into a
  `TemporaryDirectory` (or a caller-supplied `working_directory`), the process is
  spawned with piped stdio and driven by `communicate(input, timeout)`.
  A `TimeoutExpired` kills the process and raises
  `RuntimeError("AVL timed out after Ns")`. A missing `output.txt` raises
  `FileNotFoundError` including the **first 500 characters of stdout** as a hint.
  🟡 A non-zero return code is **only logged** — deliberate leniency, because
  AVL routinely exits non-zero.
- **BR-AV15 — Parsing is first-occurrence-wins.** 🟢
  `parse_stability_output` (`:41-83`) re-implements
  `asb.AVL.parse_unformatted_data_output`: scan for `" = "`, read the key
  backwards and the value forwards to the next space/newline, `float()` or
  `NaN`, first occurrence wins.
- **BR-AV16 — Post-processing is a fixed transform block.** 🟢 (`:177-257`)

  ```
  lowercase Alpha/Beta/Mach ; strip the "tot" suffix (CLtot → CL, Cl'tot → Cl')
  p = (pb/2V)·2V/b     q = (qc/2V)·2V/c     r = (rb/2V)·2V/b
  L = q·S·CL   Y = q·S·CY   D = q·S·CD
  l_b = q·S·b·Cl   m_b = q·S·c·Cm   n_b = q·S·b·Cn
  spiral parameter = "Clb Cnr / Clr Cnb"       (NaN on ZeroDivisionError)
  F_w = [−D, Y, −L] → F_b → F_g  and  M_b → M_g, M_w   via op.convert_axes
  ```

- **BR-AV17 — Strip parsing is a line state machine over 15 fixed columns.** 🟢
  (`avl_strip_forces.py:127-147`)

  ```
  Surface\s+#\s*(\d+)\s+(.*)                     → open a new surface dict
  "# Chordwise = N  # Spanwise = M"              → metadata
  "Surface area  Ssurf = X"                      → metadata
  header starting with "j" AND containing "Xle" AND "cl"  → table mode ON
  lines starting with a digit                    → split into _STRIP_COLUMNS
  blank line                                     → table mode OFF

  _STRIP_COLUMNS = j Xle Yle Zle Chord Area c_cl ai cl_norm cl cd cdv cm_c/4 cm_LE C.P.x/c
  ```

  Rows with fewer than 15 values are **dropped silently**. 🟡 The resulting dict
  shape is byte-for-byte what `vlm_strip_forces` mimics, so
  `_strip_surfaces_from_result` in `aero-analysis` consumes either unchanged —
  this compatibility is what made ADR 0003 possible.
- **BR-AV18 — Indirect constraints map to AVL's own tokens.** 🟢

  ```
  _VARIABLE_TO_AVL = {alpha: a, beta: b, roll_rate: r, pitch_rate: p, yaw_rate: y}
  otherwise: the variable must be a control-surface name → "d{index}"
  unknown → ValueError listing BOTH valid sets
  TrimTarget values ARE AVL tokens:
      CL = "C"  CY = "S"  PITCHING_MOMENT = "PM"
      ROLLING_MOMENT = "RM"  YAWING_MOMENT = "YM"
  ```

  `AVLRunner.run_trim` injects them as `extra_keystrokes` **before** `x`.
- **BR-AVR1 — Trim results are categorised into five blocks.** 🟢
  `trim_with_avl` splits the flat result dict into `aero_coefficients`,
  `forces_and_moments`, `trimmed_state`, `stability_derivatives` and
  `trimmed_deflections` (keys ∈ the control-index map). `ValueError → 422`;
  `FileNotFoundError` / `RuntimeError → 500`. Enrichment is computed
  best-effort for converged results.
- 🟡 **AVL prints the literal `Trim convergence failed` on stdout** (`Q-AV-1`, resolved by code lookup), so the inference `"CL" in raw` is replaceable with a real verdict. Derived from the lookup rather than decided, so INFERRED. Previously BR-AV19: convergence inferred, not reported.
  `converged = ("CL" in raw)` — a partially converged AVL run that still printed
  coefficients is reported as converged, and no caller can tell.
- **BR-AV20 — Replay verification is a hard gate (gh-529).** 🟢

  ```
  compute_geometry_hash(airplane) = sha256(json(canonical))
  canonical = per wing_index → per xsec_index → [(name, symmetric, hinge_point[6dp])]
    — coordinates are deliberately EXCLUDED (irrelevant to indexing, and they
      drift on every model edit)
  verify_avl_replay → None | AvlReplayMismatch(geometry_hash_mismatch | index_map_drift)
  ```

  A non-`None` result **must** be treated as a hard failure: replaying against
  drifted geometry produces silently mis-mapped surfaces (epic gh-525, finding
  C4). 🟢 The service is deleted (`Q-AV-3`/`Q-AV-4`) — the map is parsed per run.
- **BR-AA2 — AVL rejects array-valued `alpha`/`beta`.** 🟢 The guard lives
  upstream in `analyse_aerodynamics`
  (`ValueError("AVL analysis does not support parameter sweeps")`), but it is a
  property of this use case: AVL's `OPER` menu takes one scalar α per run.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Resolve the binary from the wheel, then `PATH`, then `"avl"` | Must | A fresh worktree after `poetry install` needs no symlink |
| RF-02 | Import cleanly when the wheel is absent | Must | `import` succeeds; the failure surfaces only at run time |
| RF-03 | Emit the documented keystroke sequence | Must | The generated stdin matches BR-AV12 line for line |
| RF-04 | Non-dimensionalise the body rates | Must | `r r` receives `p·b/2V`, `p p` receives `q·c/2V`, `y y` receives `r·b/2V` |
| RF-05 | Zero the rates (with a warning) when `V = 0` | Must | No division by zero; a warning is logged |
| RF-06 | Emit `g 9.81` and the blank line that leaves the mass submenu | Must | AVL returns to `OPER` rather than consuming later keystrokes as mass input |
| RF-07 | Emit `d{i} d{i} {δ}` in index-map order | Must | Command `i` always addresses the index map's `i`-th name |
| RF-08 | Collapse a symmetric pair onto one d-index | Must | A symmetric aileron pair occupies one AVL DOF |
| RF-09 | Apply deflection overrides **by name** | Must | An override for a name not present is a no-op, not a shifted index |
| RF-10 | Run in an isolated directory | Must | Two concurrent runs never collide on `airplane.avl` |
| RF-11 | Kill the process and raise on timeout | Must | `RuntimeError("AVL timed out after Ns")` |
| RF-12 | Raise with a stdout excerpt when `output.txt` is missing | Must | The message carries the first 500 characters of stdout |
| RF-13 | Tolerate a non-zero exit code when the output exists | Should | Results are parsed; the code is logged |
| RF-14 | Parse the stability file first-occurrence-wins, `NaN` on unparseable | Must | A repeated key yields the first value; `CLtot` normalises to `CL` |
| RF-15 | Post-process into dimensional forces and moments | Must | `L = q·S·CL`, `m_b = q·S·c·Cm` |
| RF-16 | Convert wind-axis forces to body and geometry axes | Must | `F_w = [−D, Y, −L]` passed through `op.convert_axes` |
| RF-17 | Emit `NaN` for the spiral parameter on a zero denominator | Should | No `ZeroDivisionError` escapes |
| RF-18 | Parse the `FS` table into 15 named columns | Must | The dict shape equals `vlm_strip_forces` output |
| RF-19 | Drop a short strip row without shifting the rest | Must | A 13-column row is skipped; the following rows parse correctly |
| RF-20 | Map a `TrimConstraint` to `<variable> <target> <value>` | Must | `pitch_rate` → `p`; `PITCHING_MOMENT` → `PM` |
| RF-21 | Reject an unknown trim variable, listing both valid sets | Must | The 422 body names the axis tokens and the available control names |
| RF-22 | Inject constraint keystrokes before `x` | Must | The constraint is set before the run executes |
| RF-23 | Categorise the trim result into the five blocks | Must | Every raw key lands in exactly one block |
| RF-24 | Report a genuine convergence verdict | **Must** | 🟡 `Q-AV-1`: parse AVL's literal `Trim convergence failed`; today it is `"CL" in raw` |
| RF-25 | Compute a coordinate-free geometry hash | Should | Moving a section does not change it; renaming a control does |
| RF-26 | Verify a replay artefact and refuse a drifted one | Should | A mismatch returns `AvlReplayMismatch`, never a silent run |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Reliability | Every run is bounded by a timeout and the process is killed on expiry | `avl_runner.py:102, :280-368` | 🟢 |
| Reliability | Runs are isolated in a `TemporaryDirectory`, so concurrency is safe | `run` | 🟢 |
| Reliability | A non-zero exit code alone does not fail the run, because AVL routinely returns one | `run` | 🟡 |
| Correctness | The d-index map and the deflection commands come from one walk, so they cannot drift | `avl_strip_forces.py` (gh-529) | 🟢 |
| Correctness | The replay hash excludes coordinates, which drift on every model edit and do not affect indexing | `avl_artefact_service` | 🟢 |
| Diagnosability | A missing `output.txt` carries the first 500 chars of stdout — the single most useful signal when AVL rejects a file | `run` | 🟢 |
| Portability | The binary ships as a Python wheel; no system install and no symlink | `_resolve_default_avl_command` | 🟢 |
| Interoperability | The strip dict is byte-compatible with the VLM path, so downstream consumers are solver-agnostic | `parse_strip_forces_output` (gh-674) | 🟢 |
| Performance | A run costs ~1–3 s for a three-surface aircraft, which is why it is off every default path | ADR 0003 (measured) | 🟢 |
| Testability | Parsers and keystroke builders are pure functions over text, testable without the binary | module structure | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Binary resolution

  Scenario: The wheel provides the binary
    Given the avl_binary wheel is installed
    Then the resolved command is the wheel's avl_path

  Scenario: The module imports without the wheel
    Given the avl_binary wheel is not installed
    When the runner module is imported
    Then the import succeeds
    And the resolved command falls through to PATH and then to "avl"

Feature: Keystrokes

  Scenario: Rates are non-dimensionalised
    Given a roll rate p, a span b and a velocity V
    Then the "r r" keystroke receives p times b divided by 2V

  Scenario: Zero velocity zeroes the rates
    Given V = 0 and a non-zero pitch rate
    Then the emitted rates are zero
    And a warning is logged
    And no division by zero occurs

  Scenario: The mass submenu is left correctly
    Given a mass block is written
    Then a blank line follows the g 9.81 keystroke
    And the subsequent alpha keystroke is interpreted by OPER

Feature: Control indexing

  Scenario: Command order matches the index map
    Given an aircraft with four distinct control names
    When the deflection commands are built
    Then the i-th command addresses the index map's i-th name

  Scenario: A symmetric pair collapses to one index
    Given a symmetric aileron pair sharing one name
    Then exactly one d-index is emitted for the pair
    And its SgnDup is +1

  Scenario: An override for an absent name is a no-op
    Given an override keyed by a name the aircraft does not have
    Then no command is emitted for it
    And the remaining indices are unchanged

Feature: Execution

  Scenario: A timeout kills the process
    Given an AVL run exceeding the timeout
    Then the process is killed
    And a RuntimeError mentioning "AVL timed out after" is raised

  Scenario: A missing output file is explained
    Given AVL exits without writing output.txt
    Then a FileNotFoundError is raised
    And its message contains the first 500 characters of stdout

  Scenario: A non-zero exit alone is tolerated
    Given AVL exits with code 1 but wrote output.txt
    Then the results are parsed normally
    And the exit code is only logged

  Scenario: Concurrent runs are isolated
    Given two runs started at the same time
    Then each writes its own airplane.avl in its own directory

Feature: Parsing

  Scenario: First occurrence wins
    Given a stability file containing CLtot twice
    Then the first value is used
    And the key is normalised to CL

  Scenario: An unparseable value becomes NaN
    Given a value that does not parse as a float
    Then NaN is stored
    And no exception is raised

  Scenario: A short strip row is dropped
    Given an FS table row with 13 of the 15 columns
    Then that row is skipped
    And the following rows parse into the correct columns

  Scenario: The strip dict is VLM-compatible
    Given an AVL strip parse and a VLM strip build for the same aircraft
    Then both dicts have the same keys and structure

Feature: Post-processing

  Scenario: Dimensional forces
    Given q, S, b, c and the coefficient set
    Then L equals q times S times CL
    And m_b equals q times S times c times Cm

  Scenario: The spiral parameter degrades to NaN
    Given Clr times Cnb equal to zero
    Then the spiral parameter is NaN
    And no ZeroDivisionError escapes

Feature: Trim

  Scenario: An axis variable maps to its token
    Given a constraint on pitch_rate targeting PITCHING_MOMENT at 0
    Then the keystroke is "p PM 0"

  Scenario: A control-surface variable maps to a d-index
    Given a constraint on a control surface at index 2
    Then the keystroke begins with "d2"

  Scenario: An unknown variable is refused
    Given a constraint on "elevater"
    Then a ValueError is raised
    And the message lists both the axis tokens and the available control names

  Scenario: Constraints precede execution
    Then the constraint keystrokes appear before the x command

Feature: Replay safety

  Scenario: Coordinates do not affect the hash
    Given a section moved 10 mm aft
    Then the geometry hash is unchanged

  Scenario: A control rename does affect the hash
    Given a control renamed
    Then the geometry hash changes

  Scenario: A drifted replay is refused
    Given an artefact whose hash does not match the current airplane
    When the replay is verified
    Then an AvlReplayMismatch with reason "geometry_hash_mismatch" is returned
    And the caller must treat it as a hard failure
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Binary resolution + import safety (RF-01, RF-02) | Must | Nothing else in the module is reachable, and the whole app must start without AVL |
| Keystroke protocol (RF-03…RF-06) | Must | It **is** the API; a wrong blank line silently feeds later keystrokes into the mass submenu |
| d-index invariant (RF-07…RF-09) | Must | A drift applies a deflection to the wrong surface with no error anywhere |
| Timeout + missing output (RF-11, RF-12) | Must | A hanging subprocess would block a request thread indefinitely |
| Isolation (RF-10) | Must | Concurrency safety |
| Stability parsing (RF-14) | Must | The only way scalar results leave AVL |
| Post-processing (RF-15, RF-16) | Must | Consumers expect dimensional values in body/geometry axes |
| Strip parsing + compatibility (RF-18, RF-19) | Must | Shared shape with the VLM path — the basis of ADR 0003 |
| Trim constraints (RF-20…RF-23) | Must | AVL's genuine advantage over AeroSandbox |
| Non-zero exit tolerance (RF-13) | Should | Matches AVL's actual behaviour |
| Spiral-parameter guard (RF-17) | Should | Robustness for a rarely-read diagnostic |
| Replay artefacts (RF-25, RF-26) | **Won't** | 🟢 withdrawn (`Q-AV-3`/`Q-AV-4`): parse, don't cache. Previously built and verified by a service **no production path calls** |
| A genuine convergence verdict (RF-24) | **Must** | 🟡 `Q-AV-1`: AVL prints `Trim convergence failed`; today a partial run reports success |
| `.mass` / `.run` file emission | Won't | Never produced; mass goes through `OPER → m`, run cases through keystrokes |
| Fuselage (`BODY`) modelling | **Won't** | 🟢 decided (`Q-AV-2`): ASB is the sole `Cnb` authority; building `BODY` would be a second producer with no physics gained |
| Sweeps through AVL | Won't | AVL's `OPER` takes one scalar α per run (BR-AA2) |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/avl_runner.py` | `AVLRunner`, `_resolve_default_avl_command` (`:30-38`), `parse_stability_output` (`:41-83`), `_build_keystrokes` (`:111-175`), `_post_process_results` (`:177-257`), `run` (`:280-368`), `run_trim`, default timeout (`:102`), filenames (`:302-303`), `g 9.81` (`:143`) | 🟢 |
| `app/services/avl_strip_forces.py` | `parse_strip_forces_output` (`:127-147`), `_STRIP_COLUMNS` (`:15-31`), `get_control_surface_index_map`, `build_control_deflection_commands`, `build_yduplicate_sign_map`, `build_indirect_constraint_commands` | 🟢 |
| `app/services/avl_trim_service.py` | `trim_with_avl`, result categorisation, `converged` | 🟢 / 🔴 |
| `app/services/avl_artefact_service.py` | `compute_geometry_hash`, `build_artefact`, `verify_avl_replay` | 🟢 (🔴 uncalled) |
| `app/schemas/aeroanalysisschema.py` | `TrimConstraint`, `TrimTarget`, `AVLTrimResult` (`:22-97`) | 🟢 |
| `app/schemas/avl_artefact.py` | `AvlArtefact`, `AvlIndexSnapshot`, `AvlRunState`, `AvlReplayMismatch` | 🟢 |
| `app/api/utils.py` | the AVL branch of `analyse_aerodynamics` (sweep rejection) | 🟢 |
| `app/api/v2/endpoints/operating_points.py` | `avl_trim_operating_point` | 🟢 |
