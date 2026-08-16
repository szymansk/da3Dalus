# avl-integration

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Cluster C / §Module:
> avl-integration, `_reversa_sdd/data-dictionary.md` §Module: avl-integration,
> `_reversa_sdd/domain.md` §2.3 and BR-15, `_reversa_sdd/state-machines.md` §9,
> ADR 0003, ADR 0008.

## Overview

`avl-integration` is everything AVL: a pure-Python `.avl` geometry emitter whose
`__repr__` **is** the file format, panel-spacing heuristics, NeuralFoil-derived
CDCL viscous polars, the vendored-binary subprocess runner with its keystroke
protocol and unformatted-stdout parsers, native indirect-constraint trim, and
the `avl_geometry_files` cache of user-edited geometry. 🟢 The control-index
map that ties `d{i}` deflection commands to control-surface names is **parsed
from AVL's own output on every run**, not cached or snapshotted — see
`BR-AV20` (`Q-AV-3`/`Q-AV-4`, 2026-08-15); the geometry-hash replay artefact
this document previously described has been withdrawn and deleted.

It is deliberately **the exception, not the default**: AeroSandbox owns every
automatic path (ADR 0003). AVL survives because three capabilities have no ASB
equivalent — native indirect constraints (`d1 PM 0`-style trim), per-section
CDCL viscous polars, and the lateral-directional (roll/yaw) axis of mixed
control surfaces. 🟢

## Responsibilities

- Emit a complete, valid `.avl` geometry file from an aircraft schema. 🟢
- Route each section's airfoil to `NACA`, `AFIL` or an inline `AIRFOIL` block,
  and compute `CLAF` per section. 🟢
- Emit `CONTROL` variables per section, duplicated across the panel strip, with
  the gh-772 role→axis decomposition and globally unique names. 🟢
- Choose panel spacing (`n_chord`, `c_space`, `n_span`, `s_space`) by three
  documented heuristics. 🟢
- Inject 3-point CDCL polars derived from NeuralFoil, preserving user-edited
  values. 🟢
- Resolve the AVL binary, drive the interactive keystroke protocol, run the
  subprocess under a timeout, and parse the stability file and `FS` stdout. 🟢
- Post-process the raw AVL scalars into dimensional forces, moments and axis
  transforms. 🟢
- Trim with AVL's native indirect constraints. 🟢
- Parse the control-surface index map fresh from every AVL result (`Q-AV-3`),
  not from a stored snapshot. 🟢
- Store, serve, regenerate and invalidate one user-editable `.avl` file per
  aeroplane. 🟢

**Explicitly NOT this module's responsibility:** the default solver stack and
the aero context (→ `aero-analysis`), the wing geometry and TED data
(→ `wing-design`), airfoil `.dat` files and low-Re polars
(→ `airfoil-catalog`), mission sizing (→ `mission-and-sizing`).

## Business Rules

> `BR-9`…`BR-15` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-AV*` are module-local.

### Policy

- **BR-15 — AeroSandbox is the default solver; AVL is the exception
  (ADR 0003).** 🟢 Actual call sites:

  | Path | Default | AVL reachable? |
  |---|---|---|
  | `analyze_wing` / `analyze_airplane` | caller-selected | yes — `analysis_tool=avl` |
  | `get_stability_summary` | caller-selected | yes — `analysis_tool=avl` |
  | strip forces (`analyze_*_strip_forces`) | `solver="vlm"` (ASB) | yes — `solver="avl"` |
  | spanwise loads | `solver="vlm"` | yes — `solver="avl"` |
  | forward-CG recompute | `solver="asb"` | yes — `solver="avl"` |
  | streamlines / four-view | `VORTEX_LATTICE` (hard-coded) | **no** |
  | α sweep / simple sweep | `AEROBUILDUP` (hard-coded) | **no** — AVL rejects array sweeps |
  | `recompute_assumptions` (gh-924 context) | `AEROBUILDUP` | **no** |
  | OP generation + background retrim | AeroBuildup / `asb.Opti` | **no** |
  | `trim_with_avl` | — | this endpoint **is** the AVL path |

  AVL's retained advantages, as encoded in the code: **indirect constraints**,
  per-section **CDCL** viscous polars, and the **roll/yaw axis of mixed
  surfaces** — `compute_enrichment` warns explicitly that an AeroBuildup trim
  solved only the symmetric axis.

### Geometry emission

- **BR-AV1 — `repr()` *is* the file format.** 🟢 `app/avl/geometry.py` is a
  dataclass hierarchy where every `__repr__` emits its AVL block, so
  `repr(AvlGeometryFile(...))` produces the complete `.avl` text. There is no
  separate serialiser and no template.

  ```
  AvlGeometryFile(title, mach, symmetry, reference, surfaces[], bodies[], cdp)
  ├── AvlSymmetry(iy_sym, iz_sym, z_sym)
  ├── AvlReference(s_ref, c_ref, b_ref, xyz_ref)
  ├── AvlSurface(name, n_chord, c_space, [n_span, s_space], [COMPONENT],
  │              [YDUPLICATE], [SCALE], [TRANSLATE], [ANGLE],
  │              [NOWAKE|NOALBE|NOLOAD], [CDCL], sections[])
  │   └── AvlSection(xyz_le, chord, ainc, [n_span, s_space],
  │                  airfoil, [CLAF], [CDCL], controls[], designs[])
  │       ├── AvlNaca(digits) | AvlAfile(filepath) | AvlAirfoilInline(name, coords)
  │       ├── AvlCdcl(cl_min cd_min  cl_0 cd_0  cl_max cd_max)
  │       └── AvlControl(name, gain, xhinge, xyz_hvec, sgn_dup)
  └── AvlBody(name, n_body, b_space, bfile, …)
  ```

  `CDp` is emitted **only** when non-zero
  (`math.isclose(cdp, 0, abs_tol=1e-12)`). `yduplicate = 0.0` when
  `wing.symmetric`, else the block is omitted entirely.

  🟢 **`AvlBody`/`BODY`/`BFIL` is never constructed, and that is correct
  (`Q-AV-2`, ANSWERED by the maintainer 2026-08-15).** See `BR-AV2F` below for
  the accepted-limitation ruling and the defect it did surface.
- **BR-AV2F — The `YDUPLICATE` invariant this document previously described as
  missing is the *opposite* defect (`Q-AV-2`).** 🟢 The AVL 3.40 primer requires
  a fictitious carry-through wing portion between two half-wings when the
  fuselage is omitted (`avl_doc.txt:117-118`) — but **measured against the live
  database, 2026-08-15, that case does not occur here**: `_build_surface` sets
  `yduplicate=0.0` for symmetric wings (`avl_geometry_service.py:162`), and
  where the root sits on `y = 0`, mirror and original meet with no gap. 74 of
  82 wing roots do; the 8 that do not are all **deliberately off-centre**
  structural members (struts, vertical surfaces) for which `YDUPLICATE` is
  correct and a carry-through would be **wrong** — except one: the `Wing`
  surface, `y_root = −0.205 m`, **crosses the centreline**. Mirroring it
  therefore makes it **overlap itself by 0.41 m** — a *doubled* centre section,
  not a missing one — silently inflating `Sref`, corrupting `CDi` and
  falsifying the reported `e = (CL²+CY²)/(π·A·CDi)`, with no warning anywhere.
  Both affected `Wing` rows have a 4 m chord, consistent with an OpenVSP import
  rather than a native RC design (ADR 0018) — a reminder that imported geometry
  reaches the AVL path unvalidated.

  **The invariant AVL geometry generation actually needs is `y_root ≥ 0` for
  any surface carrying `YDUPLICATE`**, asserted at build time and emitting a
  `DesignWarning` of severity `error` (ADR 0020) naming the surface and the
  overlap width. The primer's carry-through rule is the *other* half of the
  same invariant and applies only when a genuine gap exists — not the failure
  mode present in this codebase. **Tracked as work, not as an open gap**
  (residual register): the assertion is not yet implemented.
- **BR-AV2 — NACA vs AFIL routing accepts integers only (gh-588).** 🟢
  `_NACA_RE = ^naca\s*(\d{4,5})$`. The earlier `\d{4,5}(?:\.\d+)?` over-matched
  and routed `naca23013.5` into an `AvlNaca`, crashing AVL with
  `Read error on line N`. Decimal-bearing names are custom `.dat` files and fall
  through to `_resolve_airfoil_reference` → `AvlAfile`; the last resort is
  `AvlNaca("0012")`.
- **BR-AV3 — `CLAF = 1 + 0.77 · max_thickness`** per section, computed from the
  ASB airfoil, defaulting to `1.0` when the airfoil cannot be built. 🟢
- **BR-AV4 — `CONTROL` blocks are duplicated across the panel strip.** 🟢
  `_build_controls_for_wing` appends each x-section's control(s) to sections `i`
  **and** `i+1`, replicating what AeroSandbox does, so AVL interpolates the
  deflection across the strip.
- **BR-11 — Control-variable names must be globally unique.** 🟢 AVL silently
  collapses identically named `CONTROL` variables into a single DOF
  (avl_doc 778-789), which would couple unrelated surfaces.
  `build_avl_geometry_file` dedups **per surface** (panel duplication
  legitimately repeats a name inside one surface) and then calls
  `assert_unique_control_names` **across** surfaces, raising `ValueError` on a
  collision — before any file is written.
- **BR-9 — A role decomposes into control axes (gh-772, ADR 0008).** 🟢
  `control_surface_mixing.py` is the single source of truth shared by the AVL
  builder, the ASB airplane builder and the enrichment service.

  ```
  _DUAL_ROLE_AXES = { elevon:      (pitch, roll),
                      flaperon:    (lift,  roll),
                      ruddervator: (pitch, yaw)  }
  PRIMARY_AXES   = {pitch, lift}     # symmetric      SgnDup = +1
  SECONDARY_AXES = {roll,  yaw}      # antisymmetric  SgnDup = −1

  name = f"[{role}]{axis}_{sanitize(wing_key)}_{xsec_index}"
         e.g. "[ruddervator]pitch_htail_1"
  _ROLE_TAG_RE = ^\[(\w+)\](.*)$
  ```

  A dual-role surface emits **two** `CONTROL` variables on the same section; a
  single-axis role keeps its existing tagged name and `±1` sign verbatim. The
  **secondary axis carries `deflection = 0.0`** so the AeroBuildup fallback never
  feeds a roll/yaw deflection into the single-axis ASB model.
- **BR-10 — `SgnDup` is a sign flag, never a magnitude.** 🟢 `differential_ratio`
  is a reporting-only kinematic applied *after* trim; it never reaches the
  `.avl` file.

### Panel spacing

- **BR-AV5 — Three spacing heuristics, applied only when `auto_optimise`.** 🟢
  `optimise_surface_spacing` (`app/avl/spacing.py:71-106`) starts from
  `SpacingConfig(n_chord=12, c_space=1.0, n_span=20, s_space=1.0,
  auto_optimise=True)` and then:

  1. **Control surfaces present** → `n_chord = max(n_chord, 16)` (hinge-line
     resolution).
  2. **Unswept** (`atan2(Δx, sqrt(Δy²+Δz²)) < 5°`) **and no centreline break**
     (no interior section at `|y| < 1e-6`) → `s_space = −2.0` (−sine: panels
     concentrated at root and tip, where the induced-drag gradient is steepest).
  3. **Tight section density (gh-590)** →
     `n_span = max(n_span, ceil(span / min_gap) + 2)`. AVL otherwise aborts with
     `Cannot adjust spanwise spacing at section N` /
     `Insufficient number of spanwise vortices`. **Coincident sections**
     (chord/twist discontinuities at the same `y`, gap ≤ 1e-9) are excluded from
     `min_gap` so they cannot force `n_span → ∞`.

### CDCL

- **BR-AV6 — User-edited CDCL wins.** 🟢 `inject_cdcl` walks surfaces and
  sections **in parallel index order** and mutates in place; a section whose
  `cdcl` is present and **not** all-zero is **preserved**.
- **BR-AV7 — CDCL is a 3-point polar in AVL's order.** 🟢
  `NeuralFoilCdclService.compute_cdcl` fits from a NeuralFoil α sweep:
  point 2 at `argmin(CD)` (drag bucket), point 3 at `argmax(CL)` (positive
  stall), point 1 at `argmin(CL)` (negative stall) — emitted as
  `CL1 CD1  CL2 CD2  CL3 CD3`. `Re = V · chord / ν(altitude)`
  (`compute_reynolds_number`, ASB `Atmosphere`).
- **BR-AV8 — The polar cache is keyed on hashable primitives only.** 🟢
  `@lru_cache(maxsize=128)` over airfoil **name**, `Re`, `mach`, α range, model
  size, `n_crit`, `xtr_upper/lower`, `include_360_deg_effects`.
- **BR-AV9 — NaN/Inf from NeuralFoil yields an all-zero CDCL and a warning.** 🟢
  Never a fabricated polar.
- 🟢 **BR-AV10 — A surface/wing count mismatch is a truncated-result defect, not
  a log line (`Q-AV-5`).** A surface/section count mismatch leaves later
  sections with **zero CDCL — no viscous drag at all** — which is not a
  degraded-but-usable number, it is a physically meaningless one. Under
  `P-WARN-0` / ADR 0020 this is `result_truncated` severity `error`: the run
  emits a `DesignWarning` and must not be presented as a valid viscous result.
  Continuing silently, as today, is incompatible with the policy.

### Runner

- **BR-AV11 — Binary resolution is a three-step chain.** 🟢
  `_resolve_default_avl_command` (`avl_runner.py:30-38`): the `avl_binary`
  wheel's `avl_path()` → `shutil.which("avl")` → the literal string `"avl"`. The
  import is guarded (`except ImportError: _avl_path = None`). The wheel is the
  documented delivery mechanism, so no manual symlink is needed after
  `poetry install`.
- **BR-AV12 — The keystroke protocol is the API.** 🟢 `_build_keystrokes`
  (`avl_runner.py:111-175`) emits, in order:

  ```
  OPER
  m  →  mn <mach>, v <V>, d <ρ>, g 9.81, <blank>
  a a <alpha>   b b <beta>
  r r <p·b/2V>  p p <q·c/2V>  y y <r·b/2V>       # non-dimensional rates
  d1 d1 <δ1>    d2 d2 <δ2> …                     # build_control_deflection_commands
  <extra keystrokes>                             # trim constraints
  x                                              # execute
  st <output.txt> o                              # write the stability file, overwrite
  [fs]                                           # strip forces to stdout
  quit
  ```

  `V = 0` with non-zero rates logs a warning and zeroes the rates.
- **BR-AV13 — The d-index order is derived once and shared.** 🟢
  `build_control_deflection_commands` replaces ASB's hard-coded `d1 d1 1`: it
  walks `wings → xsecs → control_surfaces`, keeps the **first occurrence** of
  each name, applies overrides by name and emits `d{i} d{i} {δ}` in that order —
  the same order `get_control_surface_index_map` assigns 1-based indices, so the
  two can never drift. Symmetric pairs share one ASB name and therefore collapse
  to **one** AVL d-index (gh-529 YDUPLICATE dedup).

  🟢 **RESOLVED (`R1`) — `build_yduplicate_sign_map`
  does NOT supply the `SgnDup` on this live path**, contrary to what this
  document previously implied. Measured 2026-08-15: its only caller is
  `avl_artefact_service`, which **no production path invokes**. The live
  strip-force path (`avl_strip_forces.py:216`) consumes the **index** map but
  never calls the **sign** map. Whether mirrored-surface strip forces are
  therefore summed with the wrong sign into spar loads
  (`/spanwise_loads_with_sizing`) is an **open defect investigation** — AVL's
  mirror sign convention was not established from source during this interview.
  `build_yduplicate_sign_map` is **held, not deleted**, pending that
  investigation — **resolved 2026-08-15**: the sign map is a CONTROL-card *input*, not a strip-force correction, and it duplicates `control_surface_mixing.py:45`. Delete it. 🟢
- **BR-AV14 — Timeouts kill; missing output raises; a non-zero exit only logs.**
  🟢 (`run`, `:280-368`) Write `airplane.avl` into a `TemporaryDirectory` (or a
  caller-supplied `working_directory`), spawn `[avl_command, "airplane.avl"]`
  with piped stdio, `communicate(input, timeout)`. A `TimeoutExpired` kills the
  process and raises `RuntimeError("AVL timed out after Ns")`; a missing
  `output.txt` raises `FileNotFoundError` including the first 500 chars of
  stdout as a hint. 🟡 A non-zero return code is **only logged** — deliberate
  leniency, because AVL routinely exits non-zero.
- **BR-AV15 — Parsing is first-occurrence-wins.** 🟢
  `parse_stability_output` (`:41-83`) re-implements
  `asb.AVL.parse_unformatted_data_output`: scan for `" = "`, read the key
  backwards and the value forwards to the next space/newline, `float()` or
  `NaN`, **first occurrence wins**.
- **BR-AV16 — Post-processing is a fixed transform block.** 🟢 (`:177-257`)

  ```
  lowercase Alpha/Beta/Mach ; strip the "tot" suffix (CLtot → CL, Cl'tot → Cl')
  p = (pb/2V)·2V/b     q = (qc/2V)·2V/c     r = (rb/2V)·2V/b
  L = q·S·CL   Y = q·S·CY   D = q·S·CD
  l_b = q·S·b·Cl   m_b = q·S·c·Cm   n_b = q·S·b·Cn
  "Clb Cnr / Clr Cnb"  (spiral parameter; NaN on ZeroDivisionError)
  F_w = [−D, Y, −L] → F_b → F_g  and  M_b → M_g, M_w   via op.convert_axes
  ```

- **BR-AV17 — Strip parsing is a line state machine over 15 fixed columns.** 🟢
  `parse_strip_forces_output` (`avl_strip_forces.py:127-147`):
  `Surface\s+#\s*(\d+)\s+(.*)` opens a surface dict;
  `# Chordwise = N  # Spanwise = M` and `Surface area  Ssurf = X` fill metadata;
  a header line starting with `j` **and** containing `Xle` **and** `cl` turns on
  table mode; subsequent lines starting with a digit are split into
  `_STRIP_COLUMNS` = `j Xle Yle Zle Chord Area c_cl ai cl_norm cl cd cdv cm_c/4
  cm_LE C.P.x/c`; a blank line closes the table. **Rows with fewer than 15
  values are dropped silently.** 🟡 The resulting dict shape is what
  `vlm_strip_forces` mimics byte-for-byte, so `_strip_surfaces_from_result`
  consumes either unchanged.

### Trim and replay

- **BR-AV18 — Indirect constraints map to AVL's own tokens.** 🟢

  ```
  _VARIABLE_TO_AVL = {alpha: a, beta: b, roll_rate: r, pitch_rate: p, yaw_rate: y}
  otherwise: the variable must be a control-surface name → "d{index}"
  unknown → ValueError listing both valid sets
  TrimTarget enum values ARE AVL tokens:
      CL="C"  CY="S"  PITCHING_MOMENT="PM"  ROLLING_MOMENT="RM"  YAWING_MOMENT="YM"
  ```

  `AVLRunner.run_trim` injects them as `extra_keystrokes` before `x`.
- 🟢 **BR-AV19 — Convergence is inferred, and the inference is inert-false
  (`Q-AV-1`).** `trim_with_avl` declares `converged = ("CL" in raw)`. AVL prints
  a genuine convergence marker on stdout — `Trim convergence failed` on the
  Newton loop's failure branch (`Avl/src/aoper.f:1298-1319`, criterion: every
  update over α, β, the three rates and every control deflection below
  `EPS = 2e-5` rad) — but on that same failure `LSOL = .FALSE.` blocks every
  output command (`:594-611`), so the `ST` command this wrapper uses writes
  **no stability file at all** and the runner raises `FileNotFoundError` before
  `converged = ("CL" in raw)` is ever evaluated. The inference is therefore not
  merely weak, it is **unreachable-false**: `FileNotFoundError` maps to
  `InternalError` → **HTTP 500** ("check avl_command and input geometry") for
  what is actually a user-fixable ill-posed trim, and the `if not
  trimmed.converged` warning path is dead code.

  **The fix is available without new plumbing:** both AVL markers are on
  stdout, which the runner already captures. Parse them, return convergence as
  a first-class field, and map a non-converged trim to **422** carrying AVL's
  own message instead of a generic 500. One latent hazard for the
  implementation: with a reused `working_directory` a stale `output.txt` from a
  previous run could be parsed as the current result — no production caller
  passes one today, but the parser must not silently trust a leftover file.
  `ValueError → 422`, `FileNotFoundError` / `RuntimeError → 500` (both
  superseded by the new AVL-message-carrying 422 once implemented). Enrichment
  is computed best-effort for converged results.
- 🟢 **BR-AV20 — REVERSED (`Q-AV-3`/`Q-AV-4`, ANSWERED by the maintainer,
  2026-08-15): there is no replay-artefact hard gate, and there never needs to
  be one — the index → name mapping is parsed from AVL's own output on every
  run, not cached, so the drift class this mechanism guarded against cannot
  occur.** This reverses the original finding below, which is preserved for the
  historical record.

  **What the source shows.** `avl_geometry_service.py:162` sets
  `yduplicate=0.0` for symmetric wings and this document's original premise —
  *"AVL returns results by surface index, not by name"* — is **half wrong**:
  AVL prints the surface name **alongside** the index in every output block —
  `STITLE(N)` is the trailing field of every `FN` line
  (`src/aoutput.f:168-174`, format `I2,1X,F9.3,8F8.4,3X,A`), appears in `FS`
  (`:290-323`) and has its own line in the machine-readable `STRP` block
  (`src/aoutmrf.f:273-278`). **The index → name mapping is recoverable from
  every single result file**, so a caller never needed to persist one.

  **Decision: parse, don't cache.** A map that is never stored cannot go stale
  — the entire class of drift bugs this artefact guarded against disappears by
  construction, not by a check. `compute_geometry_hash`, `build_avl_artefact`,
  `verify_avl_replay` and `AvlReplayMismatch` are **withdrawn**, and — per
  `P-DEAD-0` / ADR 0021, measured 2026-08-15 to have **no production
  callers** — **deleted** rather than left dead. `get_control_surface_index_map`
  is **not affected**: it stays, because it is already **live** on the trim path
  (`avl_trim_service.py:134`) and in `build_indirect_constraint_commands`
  (`avl_strip_forces.py:216`) — index correctness was never hypothetical, it is
  relied on today, just without a hash guard.

  **Why a hash could not have been trusted anyway.** Two edits leave the old
  hash intact while invalidating the index map: **`YDUPLICATE` toggled**
  (the mirror image is inserted right after its parent, so every later index
  shifts ±1, `src/amake.f:718`) and **`NSPAN` changed** (strip numbering
  renumbers silently). A control surface added breaks the **control** map
  instead, keyed by declaration order. A sufficient hash would have needed
  name, file position, `Nchord`, `Cspace`, `Nspan`, `Sspace`, every per-section
  `Nspan`/`Sspace`, the `YDUPLICATE` flag **and** the control-name list in
  declaration order — parsing two fields per run is cheaper and cannot drift.

  **Implementation notes for the parser** (`avl-run-and-parse`): prefer the
  undocumented **`MRF`** machine-readable output (`src/aoper.f:103, 693-698`,
  `ES23.15`) over the text `FN` format (`F8.4`, which quantises small RC-scale
  coefficients — `MRF` is absent from the primer); parse the **axis-orientation
  line**, since `LSA` flips the sign of `Cl`/`Cn` on output via `DIR = ∓1`
  (`src/aoutput.f:1669-1675`) and is printed at the head of every
  `FN`/`FS`/`FB` block. Per-surface **force** signs need no correction — AVL
  applies `IMAGS` internally. (The still-open question is the **strip-force
  mirror sign**, `build_yduplicate_sign_map` — see `BR-AV13`, residual `R1`,
  unrelated to this index-parsing decision.)

  _Original finding, now reversed — kept for record:_ `avl_artefact_service`
  implemented `compute_geometry_hash` (deliberately excluding coordinates),
  `build_artefact` and `verify_avl_replay` returning `AvlReplayMismatch`, and no
  production path persisted or checked one. A non-`None` result would have had
  to be treated as a hard failure, because replaying against drifted geometry
  produces silently mis-mapped surfaces (epic gh-525, finding C4) — this
  concern is now moot, because there is nothing to replay against: the map is
  recomputed every run.

### Stored geometry

- **BR-AV21 — One `.avl` row per aeroplane, served only when trustworthy.** 🟢
  `avl_geometry_files` has `UniqueConstraint(aeroplane_id)` and columns
  `content`, `is_dirty`, `is_user_edited`. `get_user_avl_content` — the function
  every solver path calls — returns the stored content **only** when it exists
  **and** `is_user_edited` **and not** `is_dirty`; otherwise `None` and the
  caller regenerates.
- 🟢 **BR-AV22 — REVERSED (`Q-AV-4`, ANSWERED by the maintainer, 2026-08-15):
  a successful regenerate now clears `is_dirty` automatically.** Confirmed as a
  defect first: `is_dirty` is set by the geometry listeners
  (`avl_geometry_events.py:26`) and was cleared **only** by a user `PUT` or an
  explicit `POST …/regenerate`, while `get_user_avl_content` returns `None`
  whenever the flag is set (`:354-365`) — so after **any** geometry edit the
  user-edited file was bypassed **permanently** until the user intervened. The
  feature stopped taking effect without saying so, which is exactly the
  undeclared behaviour ADR 0020 forbids. **Decision:** `POST …/regenerate`
  clearing the row (already the case, RF-33) plus the parse-not-cache index map
  (`BR-AV20`) together remove the failure mode — a regenerate is now trusted
  the same run it happens, with no separate hash guard needed.
- 🟢 **BR-AV23 — REVERSED, with a fix plan, not merely confirmed
  (`Q-AV-6`, expert consensus endorsed by the maintainer 2026-08-14): the
  asymmetric consultation is an inconsistency, not a defensible design — but the
  fix is a merge, not a swap.** `analyze_wing` and the single-wing strip-force
  path **never** consult the stored file (they prune the airplane to one wing
  and always build fresh), while `analyze_airplane`, `trim_with_avl` and the
  full-airplane strip-force path do.

  The AVL 3.40 primer splits the file exactly along the line that decides this:
  **global header** (`Mach`, symmetry, `Sref Cref Bref`, `Xref Yref Zref`,
  `CDp`) is *"assumed to correspond to the total geometry"* and moments are
  taken about the aircraft CG (`avl_doc.txt:243-289`, `:272-274`); **per-surface**
  (spacing, `COMPONENT`, `YDUPLICATE`, `CDCL`, `CLAF`, `CONTROL`, airfoil
  references) is not. So a hand-edited full-airplane file genuinely **cannot**
  be reused for a single-wing run by deleting surfaces — the coefficients would
  still be normalised against whole-aircraft `Sref/Cref/Bref` (the same failure
  shape as gh-788's "`s_ref` from the first wing → 8× wrong coefficients"). But
  that only justifies rewriting the **header**, not discarding the per-surface
  edits AVL's own primer instructs the user to make (spacing bunched at
  control-surface ends and wing tips, `Nchord` resolving the hinge-line kink).

  **Fix, for `analyze_wing` and the single-wing strip-force path:** (1) parse
  the stored user `.avl` and lift out the `SURFACE` block matching `wing_name`
  verbatim — spacing, `CDCL`, `CLAF`, `CONTROL`, airfoil references, `ANGLE`,
  `YDUPLICATE`; (2) always regenerate the header from the pruned wing alone,
  never inheriting the aircraft header; (3) if no matching `SURFACE` block
  exists, fall back to the generated file and emit a `DesignWarning`
  (`input_ignored`) naming what was dropped; (4) report
  `avl_source: "user_surface+generated_header" | "generated"` — today the
  client cannot tell, and that silence, not the pruning, is the actual
  complaint. **Acceptable minimum** if (1)–(2) is too much work: (3) and (4)
  alone; silence is the one option ADR 0012 rules out. At RC scale `CDCL` is
  the edit most likely to have been made and the one whose loss hurts most —
  preserving it outranks preserving the spacing parameters. Priority is capped
  by ADR 0003: this affects a secondary analysis route.
- 🟢 **BR-13 — resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Previously the canonical name was the gh-772 mixing name (open bug
  #955).** The AVL builder uses it correctly; `trim_enrichment_service`,
  `retrim_service` and `stability_service` do not. See
  [`control-surface-naming/`](control-surface-naming/requirements.md).

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Emit a complete `.avl` file from an aircraft schema via `repr()` | Must | The text parses in AVL without a `Read error` |
| RF-02 | Emit `CDp` only when non-zero | Should | `cdp = 0.0` produces no `CDp` line |
| RF-03 | Emit `YDUPLICATE 0.0` for symmetric wings and omit it otherwise | Must | An asymmetric surface has no `YDUPLICATE` block |
| RF-04 | Route integer NACA names to `NACA`, everything else to `AFIL` | Must | `naca23013.5` produces an `AFIL`, not a `NACA` |
| RF-05 | Fall back to `NACA 0012` when no airfoil can be resolved | Should | A missing `.dat` yields `NACA 0012`, not a crash |
| RF-06 | Compute `CLAF = 1 + 0.77·max_thickness` per section | Should | An unbuildable airfoil yields `CLAF 1.0` |
| RF-07 | Duplicate each control onto sections `i` and `i+1` | Must | A one-segment control appears in two `SECTION` blocks |
| RF-08 | Emit two `CONTROL` variables for a dual-role surface, primary `+1` / secondary `−1` | Must | An elevon yields `[elevon]pitch_…` (+1) and `[elevon]roll_…` (−1) |
| RF-09 | Force the secondary axis's baseline deflection to `0.0` | Must | The ASB fallback never receives a roll/yaw deflection |
| RF-10 | Dedup control names per surface and assert uniqueness across surfaces | Must | A cross-surface collision raises before any file is written |
| RF-11 | Raise `n_chord` to ≥ 16 when a surface carries control surfaces | Should | A flapped wing emits `n_chord ≥ 16` |
| RF-12 | Use `s_space = −2.0` for unswept surfaces without a centreline break | Should | A straight wing with a root break keeps `s_space = 1.0` |
| RF-13 | Raise `n_span` to `ceil(span/min_gap)+2`, excluding coincident sections | Must | Two sections at the same `y` do not drive `n_span` to infinity |
| RF-14 | Preserve a user-edited, non-zero CDCL block | Must | A hand-written `CDCL` survives injection |
| RF-15 | Compute a 3-point CDCL from NeuralFoil in AVL's order | Should | The emitted order is `CL1 CD1 CL2 CD2 CL3 CD3` with point 2 at `argmin(CD)` |
| RF-16 | Emit an all-zero CDCL and warn on non-finite NeuralFoil output | Must | NaN never reaches the file |
| RF-17 | Cache CDCL polars on hashable primitives, max 128 entries | Should | Two identical requests issue one NeuralFoil call |
| RF-18 | Resolve the AVL binary from the wheel, then `PATH`, then `"avl"` | Must | A worktree after `poetry install` needs no symlink |
| RF-19 | Drive AVL through the documented keystroke sequence | Must | The generated stdin matches the block in BR-AV12 |
| RF-20 | Zero the body rates (with a warning) when `V = 0` | Must | No division by zero in the non-dimensionalisation |
| RF-21 | Emit `d{i} d{i} {δ}` in the same order as the index map | Must | A renamed surface never shifts a deflection onto the wrong control |
| RF-22 | Collapse a symmetric pair onto one d-index | Must | A symmetric aileron pair occupies one AVL DOF |
| RF-23 | Kill the process and raise on timeout | Must | `RuntimeError("AVL timed out after Ns")` after the configured seconds |
| RF-24 | Raise with a stdout excerpt when `output.txt` is missing | Must | The error carries the first 500 chars of stdout |
| RF-25 | Parse the stability output first-occurrence-wins, `NaN` on unparseable | Must | A repeated key yields the first value |
| RF-26 | Post-process into dimensional forces, moments and axis transforms | Must | `L = q·S·CL`; `F_w = [−D, Y, −L]` converted through `op.convert_axes` |
| RF-27 | Parse `FS` strip output into 15 named columns | Must | A short row is dropped, not mis-aligned |
| RF-28 | Map a `TrimConstraint` to `<variable> <target> <value>` | Must | `pitch_rate` → `p`; an unknown variable raises listing both valid sets |
| RF-29 | Categorise AVL trim output into the five result blocks | Must | Keys land in `aero_coefficients`, `forces_and_moments`, `trimmed_state`, `stability_derivatives`, `trimmed_deflections` |
| RF-30 | ~~Snapshot and verify a replay artefact~~ — **Removed** (`Q-AV-3`/`Q-AV-4`, 2026-08-15) | — | 🟢 Superseded: the index → name map is parsed from AVL's own output every run instead, so there is nothing to snapshot or verify against |
| RF-31 | Store one `.avl` row per aeroplane with `is_dirty` / `is_user_edited` | Must | A second save updates the same row |
| RF-32 | Serve stored content only when user-edited and not dirty | Must | A dirty row causes the caller to regenerate |
| RF-33 | Regenerate by deleting the row and returning fresh content, and clear `is_dirty` on success | Must | `POST …/regenerate` removes the row; a subsequent edit is the only thing that can dirty it again |
| RF-34 | Parse AVL's own convergence markers instead of inferring | **Must (open)** | 🟢 `Q-AV-1` — today `converged = ("CL" in raw)` is unreachable-false; parse `Trim convergence failed` / the missing stability file and map a non-converged trim to 422 |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Performance | AVL is off every hot path; a run costs ~1–3 s vs ~58 ms for the in-process VLM | ADR 0003 (measured) | 🟢 |
| Performance | CDCL polars are memoised (`lru_cache(maxsize=128)`) on primitive keys | `neuralfoil_cdcl_service.py:25` | 🟢 |
| Reliability | Every run has a timeout (default 30 s; callers pass 60 s) and the process is killed on expiry | `avl_runner.py:102, :280-368` | 🟢 |
| Reliability | Runs happen in a `TemporaryDirectory`, so concurrent runs cannot collide on `airplane.avl` | `run` | 🟢 |
| Reliability | A non-zero AVL exit code is tolerated, because AVL routinely returns one | `run` | 🟡 |
| Correctness | Control names are asserted unique **before** the file is written, because AVL fails **silently** on a collision | `assert_unique_control_names` (BR-11) | 🟢 |
| Correctness | The d-index order and the deflection command order are derived from one walk | `build_control_deflection_commands` + `get_control_surface_index_map` | 🟢 |
| Correctness | ~~The replay hash excludes coordinates~~ — moot; `Q-AV-3`/`Q-AV-4` withdrew the hash entirely and deleted `avl_artefact_service` (gh-529), because the index → name map is parsed per run instead of cached | `avl_geometry_service.py:162` (yduplicate), AVL `STITLE(N)` on every output block | 🟢 |
| Robustness | Non-finite NeuralFoil output becomes an all-zero CDCL plus a warning, never a fabricated polar | `neuralfoil_cdcl_service` | 🟢 |
| Robustness | `n_span` is raised to avoid AVL's `Insufficient number of spanwise vortices` abort | `spacing.py:43-68` (gh-590) | 🟢 |
| Portability | The binary comes from a Python wheel, so no system install or symlink is required | `_resolve_default_avl_command`, `.claude/rules/worktree-setup.md` | 🟢 |
| Portability | A missing `avl_binary` import degrades to `None` and then to `PATH` lookup | guarded import | 🟢 |
| Maintainability | The file format lives in one dataclass hierarchy; there is no template to drift | `app/avl/geometry.py` | 🟢 |
| Testability | 57 `.avl` fixtures exist in the tree for parser regression | repository inventory | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Geometry emission

  Scenario: A symmetric wing emits YDUPLICATE
    Given a wing whose symmetric flag is true
    When the avl file is emitted
    Then its SURFACE block contains "YDUPLICATE" with value 0.0

  Scenario: A decimal NACA name is an AFIL, not a NACA
    Given a section whose airfoil is named "naca23013.5"
    When the section is emitted
    Then an AFIL block referencing a dat file is written
    And no NACA block is written
    # gh-588 — the old regex crashed AVL with "Read error on line N"

  Scenario: Zero parasite drag emits no CDp line
    Given cdp equal to 0.0
    Then the emitted file contains no CDp line

Feature: Control variables

  Scenario: A dual-role surface emits two control variables
    Given a trailing-edge device with role "elevon" and deflection 10 degrees
    When the avl geometry is built
    Then a CONTROL named "[elevon]pitch_<wing>_<i>" exists with SgnDup +1
    And a CONTROL named "[elevon]roll_<wing>_<i>" exists with SgnDup -1
    And the roll variable's baseline deflection is 0.0

  Scenario: Controls are duplicated across the strip
    Given a control on cross-section i
    Then the CONTROL block appears in sections i and i+1

  Scenario: A cross-surface name collision is refused
    Given two surfaces whose controls resolve to the same name
    When the geometry file is built
    Then a ValueError is raised
    And no file content is produced
    # AVL would silently collapse them into one DOF

  Scenario: Duplication inside one surface is allowed
    Given the same control name repeated across sections of ONE surface
    Then the build succeeds

Feature: Panel spacing

  Scenario: Control surfaces raise the chordwise count
    Given a surface carrying at least one control
    Then n_chord is at least 16

  Scenario: An unswept clean wing gets minus-sine spacing
    Given a surface whose sweep is below 5 degrees and which has no interior section at y = 0
    Then s_space is -2.0

  Scenario: A centreline break keeps cosine spacing
    Given the same surface with an interior section at y = 0
    Then s_space stays 1.0

  Scenario: Tight sections raise the spanwise count
    Given two sections 2 mm apart on a 1 m span
    Then n_span is at least ceil(span / min_gap) + 2

  Scenario: Coincident sections do not explode n_span
    Given two sections at the same y (a chord discontinuity)
    Then that pair is excluded from min_gap
    And n_span stays finite

Feature: CDCL

  Scenario: A user-edited CDCL is preserved
    Given a section whose CDCL is present and not all zero
    When injection runs
    Then the section keeps its values

  Scenario: NeuralFoil NaN yields an all-zero CDCL
    Given a NeuralFoil sweep returning NaN
    Then the emitted CDCL is all zeros
    And a warning is logged
    And no fabricated polar is written

Feature: Running AVL

  Scenario: Zero velocity zeroes the rates
    Given an operating point with V = 0 and a non-zero pitch rate
    When the keystrokes are built
    Then the rates are emitted as zero
    And a warning is logged

  Scenario: A timeout kills the process
    Given an AVL run exceeding the timeout
    Then the process is killed
    And a RuntimeError mentioning "AVL timed out after" is raised

  Scenario: A missing output file is explained
    Given AVL exits without writing output.txt
    Then a FileNotFoundError is raised
    And the message includes the first 500 characters of stdout

  Scenario: A non-zero exit code alone is tolerated
    Given AVL exits with code 1 but wrote output.txt
    Then the results are parsed normally
    And the exit code is only logged

  Scenario: Parsing takes the first occurrence
    Given a stability file with the key "CLtot" twice
    Then the first value wins
    And the key is normalised to "CL"

  Scenario: A short strip row is dropped
    Given an FS table row with 13 of the 15 columns
    Then that row is skipped
    And the remaining rows are parsed

Feature: Stored geometry

  Scenario: Stored content is served only when trustworthy
    Given a stored row with is_user_edited true and is_dirty false
    Then get_user_avl_content returns it
    But with is_dirty true it returns nothing and the caller regenerates

  Scenario: A geometry edit dirties the stored file
    Given a stored avl geometry row
    When a wing cross-section is updated
    Then is_dirty becomes true

  Scenario: Regeneration deletes the row
    When I POST to the regenerate route
    Then the stored row is removed
    And freshly generated content is returned

Feature: Convergence (Q-AV-1)

  Scenario: A partially converged trim is reported honestly
    Given an AVL trim whose Newton loop fails to satisfy EPS
    Then AVL writes "Trim convergence failed" and no stability file
    When trim_with_avl runs
    Then the response reports converged = false via a 422 carrying AVL's message
    # not the current 500 "check avl_command and input geometry"

Feature: Control-index parsing (Q-AV-3 / Q-AV-4 — replaces "Replay safety")

  Scenario: The index map is parsed fresh from every result, never cached
    Given an aeroplane whose geometry changed since the last AVL run
    When a new AVL run completes
    Then the surface-name-to-index map is read from that run's own output
    And no stored artefact or hash is consulted or required to be valid
    # there is nothing to drift, because nothing is cached
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Geometry emission incl. NACA/AFIL routing (RF-01, RF-04) | Must | A malformed file crashes AVL with an unhelpful `Read error on line N` |
| Control emission + uniqueness assertion (RF-07…RF-10) | Must | AVL fails **silently** on a name collision — the worst possible failure mode |
| Dual-role decomposition (RF-08, RF-09) | Must | The one capability AVL has that AeroSandbox does not (ADR 0003) |
| `n_span` safety margin (RF-13) | Must | Without it AVL aborts on tightly spaced sections (gh-590) |
| d-index / deflection-order coupling (RF-21, RF-22) | Must | A drift silently applies a deflection to the wrong surface |
| Timeout + missing-output handling (RF-23, RF-24) | Must | A subprocess that hangs would block a request thread indefinitely |
| Stability + strip parsing (RF-25…RF-27) | Must | The only way results leave AVL |
| Post-processing transforms (RF-26) | Must | Consumers expect dimensional forces in body/geometry axes |
| Stored-file lifecycle (RF-31…RF-33) | Must | The user-editable geometry escape hatch |
| Indirect-constraint trim (RF-28, RF-29) | Must | AVL's second genuine advantage |
| Binary resolution (RF-18) | Must | Everything else is unreachable without it |
| CDCL injection (RF-14…RF-17) | Should | AVL's third advantage, but every path works without it |
| Spacing heuristics 1 and 2 (RF-11, RF-12) | Should | Accuracy improvements, not correctness gates |
| `CLAF` (RF-06) | Should | A refinement with a documented default |
| `CDp` suppression (RF-02) | Should | Cosmetic file hygiene |
| ~~Replay artefacts (RF-30)~~ | **Removed** | 🟢 `Q-AV-3`/`Q-AV-4`, 2026-08-15 — deleted (ADR 0021): the index map is parsed per run instead, so nothing needs snapshotting |
| A real convergence flag (RF-34) | **Must (open)** | 🟢 `Q-AV-1` — parse AVL's own markers; fix is available, not yet implemented |
| `AvlBody` / `BFIL` fuselage modelling | Won't (accepted) | 🟢 `Q-AV-2`, ANSWERED by the maintainer 2026-08-15 — the wing-only model is correct, not a gap: AeroSandbox is the sole authority for `Cnb` (ADR 0022), and AVL's `BODY` is a one-way-coupled, essentially-zero-drag, author-flagged-unvalidated model that would add no physics. See `BR-AV2F` below for the defect this question *did* surface. |
| `.mass` and `.run` file emission | Won't (deferred, not scope-closed) | 🟢 `Q-AV-8`, ANSWERED by the maintainer 2026-08-15 — deferred behind a genuine precondition (a per-component mass model with positions), not dropped; see the new note under Business Rules and → `aero-analysis` for the two free dynamic results shipped in place of it |
| Making AVL a default on any path | Won't | ADR 0003 |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/avl/geometry.py` | `AvlGeometryFile`, `AvlSymmetry`, `AvlReference`, `AvlSurface`, `AvlSection`, `AvlControl`, `AvlCdcl`, `AvlNaca`, `AvlAfile`, `AvlAirfoilInline`, `AvlDesign`, `AvlBody` — every `__repr__` | 🟢 |
| `app/avl/spacing.py` | `optimise_surface_spacing` (`:71-106`), the unswept threshold (`:17`), the `n_span` margin (`:43-68`), `s_space = −2.0` (`:101`), `n_chord` floor (`:97`) | 🟢 |
| `app/services/avl_geometry_service.py` | `build_avl_geometry_file`, `_NACA_RE` (`:52`), `_resolve_airfoil_reference`, `CLAF` (`:102`), `_build_controls_for_wing`, `inject_cdcl`, `get_user_avl_content`, stored-file CRUD | 🟢 |
| `app/services/avl_runner.py` | `AVLRunner`, `_resolve_default_avl_command` (`:30-38`), `parse_stability_output` (`:41-83`), `_build_keystrokes` (`:111-175`), `_post_process_results` (`:177-257`), `run` (`:280-368`), `run_trim` | 🟢 |
| `app/services/avl_strip_forces.py` | `parse_strip_forces_output` (`:127-147`), `_STRIP_COLUMNS` (`:15-31`), `get_control_surface_index_map` (🟢 **live**, `avl_trim_service.py:134`), `build_control_deflection_commands`, `build_yduplicate_sign_map` (🟢 **R1 resolved** — deleted: it is a second producer of the `CONTROL`-card `SgnDup` already owned by `control_surface_mixing.py:45`, and AVL applies `IMAGS` internally so no per-surface sign is needed on forces), `build_indirect_constraint_commands` (🟢, `:216`) | 🟢 / 🔴 |
| `app/services/avl_trim_service.py` | `trim_with_avl` | 🟢 (categorisation) / 🟢 `Q-AV-1` (`converged` — confirmed defect, fix identified, not yet implemented) |
| `app/services/neuralfoil_cdcl_service.py` | `NeuralFoilCdclService.compute_cdcl`, the `lru_cache` (`:25`), `compute_reynolds_number` | 🟢 |
| ~~`app/services/avl_artefact_service.py`~~ | ~~`compute_geometry_hash`, `build_artefact`, `verify_avl_replay`~~ | **Deleted** (`Q-AV-3`/`Q-AV-4`, ADR 0021) — no production callers, superseded by per-run parsing of AVL's own `STITLE(N)` output |
| `app/services/control_surface_mixing.py` | `_DUAL_ROLE_AXES`, `PRIMARY_AXES`, `SECONDARY_AXES`, `axis_control_name`, `assert_unique_control_names`, `_ROLE_TAG_RE` (`:25`), `ControlAxis` (`:41`) | 🟢 |
| `app/models/avl_geometry_file.py` | `AvlGeometryFileModel`, `uq_avl_geometry_files_aeroplane_id` | 🟢 |
| `app/models/avl_geometry_events.py` | dirty listeners (🟡 factored out — `Q-AA-4` — previously duplicated with `stability_events.py` — out of this fold-back's question set) | 🔴 |
| `app/api/v2/endpoints/aeroplane/avl_geometry.py` | 4 routes | 🟢 |
| `app/api/v2/endpoints/operating_points.py` | `avl_trim_operating_point` | 🟢 |
| `app/schemas/aeroanalysisschema.py` | `SpacingConfig` / `CdclConfig` (`:187-219`), `TrimConstraint` / `TrimTarget` / `AVLTrimResult` (`:22-97`) | 🟢 |
| ~~`app/schemas/avl_artefact.py`~~ | ~~`AvlArtefact`, `AvlIndexSnapshot`, `AvlRunState`, `AvlReplayMismatch`~~ | **Deleted** alongside `avl_artefact_service.py` |
