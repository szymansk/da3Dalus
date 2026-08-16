# avl-integration — Technical Design

> Focuses on HOW the module is built, read from the legacy code.
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Companion documents: [`requirements.md`](requirements.md),
> [`contracts.md`](contracts.md), [`tasks.md`](tasks.md).

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `build_avl_geometry_file` | `(plane_schema, spacing_config=None)` | `AvlGeometryFile` | `repr()` yields the file text 🟢 |
| `inject_cdcl` | `(avl_file, plane_schema, operating_point, cdcl_config)` | `None` (mutates in place) | preserves user values 🟢 |
| `get_user_avl_content` | `(db, aeroplane_id)` | `str \| None` | only when `is_user_edited and not is_dirty` 🟢 |
| `AVLRunner(avl_command=None, timeout=30)` | — | — | binary resolved by a 3-step chain 🟢 |
| `AVLRunner.run` | `(avl_file_content, operating_point, extra_keystrokes=None, working_directory=None, strip_forces=False)` | results dict | subprocess + parse + post-process 🟢 |
| `AVLRunner.run_trim` | `(…, constraints)` | results dict | injects constraint keystrokes before `x` 🟢 |
| `parse_stability_output` | `(text)` | `dict[str, float]` | first-occurrence-wins 🟢 |
| `parse_strip_forces_output` | `(stdout)` | `{surface: {...strips[]}}` | 15-column state machine 🟢 |
| `get_control_surface_index_map` | `(plane_schema)` | `{name: 1-based index}` | shares one walk with the deflection commands 🟢 |
| `build_control_deflection_commands` | `(plane_schema, overrides)` | `list[str]` | `d{i} d{i} {δ}` 🟢 |
| `build_yduplicate_sign_map` | `(plane_schema)` | `{name: ±1.0}` | `symmetric → +1` 🟢 |
| `build_indirect_constraint_commands` | `(constraints, index_map)` | `list[str]` | `<var> <target> <value>` 🟢 |
| `trim_with_avl` | `(db, aeroplane_uuid, request)` | `AVLTrimResult` | 🟢 `converged = "CL" in raw` is a confirmed, unreachable-false defect (`Q-AV-1`); fix identified, not yet implemented |
| ~~`compute_geometry_hash`~~ / ~~`verify_avl_replay`~~ | — | — | **Deleted** (`Q-AV-3`/`Q-AV-4`, ADR 0021) — the index → name map is parsed from AVL's own output every run instead |
| `axis_control_name` | `(role, axis, wing_key, xsec_index)` | `str` | `[{role}]{axis}_{wing}_{i}` 🟢 |
| `assert_unique_control_names` | `(names)` | `None` / raises | AVL collapses duplicates **silently** 🟢 |

HTTP: 4 routes on `app/api/v2/endpoints/aeroplane/avl_geometry.py` plus
`POST …/operating-points/avl-trim`. Full table in
[`contracts.md`](contracts.md).

## Main Flow — an AVL analysis

```
1. caller opts in:  analysis_tool = "avl"  |  ?solver=avl  |  the avl-trim route
2. content = get_user_avl_content(db, aeroplane_id)
       returns the stored text ONLY when it exists AND is_user_edited AND NOT is_dirty
   if content is None:
       geom = build_avl_geometry_file(plane_schema, spacing_config)
       inject_cdcl(geom, plane_schema, operating_point, cdcl_config)   # optional
       content = repr(geom)
3. analyse_aerodynamics(AVL, operating_point, airplane, avl_file_content=content)
       └─ array-valued alpha/beta → ValueError("AVL analysis does not support
                                                parameter sweeps")
4. AVLRunner(...).run(content, operating_point[, extra_keystrokes][, strip_forces])
       ├─ TemporaryDirectory / working_directory
       ├─ write airplane.avl
       ├─ spawn [avl_command, "airplane.avl"], piped stdio
       ├─ communicate(keystrokes, timeout)
       │     TimeoutExpired → kill → RuntimeError("AVL timed out after Ns")
       ├─ read output.txt
       │     missing → FileNotFoundError(+ first 500 chars of stdout)
       ├─ parse_stability_output(output.txt)
       ├─ [parse_strip_forces_output(stdout)]
       └─ _post_process_results(...)
5. AnalysisModel.from_avl_dict(results)              # → aero-analysis
```

## Geometry emission 🟢

`app/avl/geometry.py` is a dataclass hierarchy where each `__repr__` emits its
block. `repr(AvlGeometryFile(...))` is therefore the complete file — there is no
serialiser, no template, and no place for the format to drift from the model.

```
AvlGeometryFile(title, mach, symmetry, reference, surfaces[], bodies[], cdp=0.0)
├── AvlSymmetry(iy_sym=0, iz_sym=0, z_sym=0.0)          → "Iysym Izsym Zsym"
├── AvlReference(s_ref, c_ref, b_ref, xyz_ref(3))       → "Sref Cref Bref" + "Xref Yref Zref"
├── AvlSurface(name, n_chord, c_space, sections[], n_span, s_space,
│              yduplicate, component, scale, translate, angle,
│              nowake, noalbe, noload, cdcl)            → "SURFACE"
│   └── AvlSection(xyz_le(3), chord, ainc=0.0, n_span, s_space,
│                  airfoil, claf, cdcl, controls[], designs[])  → "SECTION"
│       ├── AvlNaca(digits) | AvlAfile(filepath) | AvlAirfoilInline(name, coords)
│       ├── AvlCdcl(cl_min, cd_min, cl_0, cd_0, cl_max, cd_max)  → "CDCL"
│       ├── AvlControl(name, gain, xhinge, xyz_hvec(3), sgn_dup)  → "CONTROL"
│       └── AvlDesign(name, weight)                               → "DESIGN"
└── AvlBody(name, n_body, b_space, bfile, yduplicate, scale, translate)
                                                        → "BODY" + "BFIL"
                                       🟢 never built — accepted (Q-AV-2), see §Risks and Gaps
```

Emission rules:

- `CDp` only when `not math.isclose(cdp, 0, abs_tol=1e-12)`;
- `yduplicate = 0.0` when `wing.symmetric`, else the block is omitted;
- airfoil routing: `_NACA_RE = ^naca\s*(\d{4,5})$` (**integers only**, gh-588) →
  `AvlNaca`; otherwise `_resolve_airfoil_reference` → `AvlAfile`; last resort
  `AvlNaca("0012")`;
- `CLAF = 1 + 0.77 · max_thickness`, default `1.0`.

## Control emission 🟢

```
per wing, per xsec with a control surface:
    axes = control_surface_mixing.resolve_axes(role, ...)
             single-axis role → 1 ControlAxis (existing tagged name, ±1 verbatim)
             dual-role        → 2 ControlAxis:
                 primary   (pitch|lift)  sgn_dup +1  gain mix_gain_primary
                                          symmetric True   deflection = surface's
                 secondary (roll|yaw)    sgn_dup −1  gain mix_gain_secondary
                                          symmetric False  deflection = 0.0
    for each axis: append AvlControl to sections i AND i+1     # panel-strip duplication

after all surfaces:
    dedup within each surface       (duplication inside one surface is legitimate)
    assert_unique_control_names(across surfaces) → ValueError on a collision
```

The cross-surface assertion exists because **AVL silently collapses identically
named `CONTROL` variables into a single DOF** (avl_doc 778-789), which would
couple unrelated surfaces with no error message anywhere.

## Panel spacing 🟢

```
start: SpacingConfig(n_chord=12, c_space=1.0, n_span=20, s_space=1.0, auto_optimise=True)

if auto_optimise:
  1. any control surface on this surface
         → n_chord = max(n_chord, 16)
  2. sweep = atan2(Δx, sqrt(Δy² + Δz²)) < 5°
     and no interior section at |y| < 1e-6
         → s_space = −2.0          # −sine: panels dense at root and tip
  3. min_gap over NON-coincident sections (gap > 1e-9)
         → n_span = max(n_span, ceil(span / min_gap) + 2)
```

Rule 3 exists because AVL aborts with
`Cannot adjust spanwise spacing at section N` /
`Insufficient number of spanwise vortices` when sections are closer together
than the panel width (gh-590). Coincident sections — chord or twist
discontinuities at the same `y` — are excluded, otherwise `min_gap → 0` drives
`n_span → ∞`.

## CDCL injection 🟢

```
walk surfaces and sections in PARALLEL INDEX ORDER, mutating in place:
    if section.cdcl is present and not all-zero:  PRESERVE (user edit wins)
    Re = V · chord / ν(altitude)                  # ASB Atmosphere
    polar = NeuralFoilCdclService.compute_cdcl(airfoil_name, Re, mach, cfg)
        α sweep → point 2 = argmin(CD)   (drag bucket)
                  point 3 = argmax(CL)   (positive stall)
                  point 1 = argmin(CL)   (negative stall)
        emitted as  CL1 CD1  CL2 CD2  CL3 CD3
    non-finite anywhere → warning + an ALL-ZERO CDCL
cache: @lru_cache(maxsize=128) keyed on hashable primitives only —
       airfoil NAME, Re, mach, α range, model_size, n_crit, xtr_upper/lower,
       include_360_deg_effects
```

🟢 A surface/wing count mismatch is a confirmed `error`-severity defect, not a
log line (`Q-AV-5`): the truncated sections carry **zero CDCL — no viscous drag
at all**, which is `result_truncated` under `P-WARN-0`/ADR 0020. The run must
emit a `DesignWarning` and must not be presented as a valid viscous result;
silent truncation, as today, is not compatible with the policy.

`CdclConfig` defaults: α sweep bounds with `alpha_step_deg = 1.0` (range 0–10),
`model_size = "large"` (note: the airfoil backfill in `airfoil-catalog` uses
`"xxxlarge"`), `n_crit`, `xtr_upper`/`xtr_lower`, `include_360_deg_effects`.

## The runner 🟢

### Binary resolution

```
_resolve_default_avl_command():
    1. avl_binary wheel → avl_path()          (guarded: except ImportError → None)
    2. shutil.which("avl")
    3. the literal string "avl"
```

### Keystroke protocol

```
OPER
m
  mn <mach>
  v  <velocity>
  d  <density>
  g  9.81
  <blank line>              # leave the mass submenu
a a <alpha>
b b <beta>
r r <p·b/2V>                # non-dimensional roll rate
p p <q·c/2V>                # non-dimensional pitch rate
y y <r·b/2V>                # non-dimensional yaw rate
d1 d1 <δ1>
d2 d2 <δ2>
…                           # build_control_deflection_commands, in index order
<extra keystrokes>          # trim constraints (run_trim only)
x                           # execute
st output.txt
o                           # overwrite
[fs]                        # strip forces to stdout, only when requested
quit
```

`V = 0` with non-zero rates logs a warning and zeroes the rates (the
non-dimensionalisation would divide by zero).

### The d-index invariant

`build_control_deflection_commands` and `get_control_surface_index_map` perform
**the same walk** — `wings → xsecs → control_surfaces`, keeping the **first
occurrence** of each name — so the emitted `d{i}` commands and the 1-based index
map can never drift. Symmetric pairs share one ASB name and therefore collapse
to **one** AVL d-index (gh-529 YDUPLICATE dedup).

🟢 **RESOLVED (`R1`) — `build_yduplicate_sign_map`
does not feed this live path.** This document previously implied it supplies
the collapsed pair's sign here; measured 2026-08-15, its only caller is
`avl_artefact_service`, which nothing in production calls. The live
strip-force path (`avl_strip_forces.py:216`) uses the **index** map only.
Whether mirrored-surface strip forces are summed with the correct sign into
spar loads (`/spanwise_loads_with_sizing`) is an **open defect investigation**
— AVL's own mirror sign convention was not established from source. The
function is **deleted with the rest of the artefact service**: it is a second producer of the `CONTROL`-card `SgnDup`, which `control_surface_mixing.py:45` already owns (ADR 0022), and AVL needs no per-surface sign on output forces at all.

### Execution and parsing

```
run():
    dir = working_directory or TemporaryDirectory()
    write dir/airplane.avl
    proc = Popen([avl_command, "airplane.avl"], stdin/stdout/stderr=PIPE, cwd=dir)
    out, err = proc.communicate(keystrokes, timeout=timeout)
        TimeoutExpired → proc.kill() → RuntimeError(f"AVL timed out after {t}s")
    if not exists(dir/output.txt):
        raise FileNotFoundError(... + out[:500])
    non-zero returncode → LOG ONLY                       🟡 AVL routinely exits non-zero
    results = parse_stability_output(read(output.txt))
    if strip_forces: results["strip_forces"] = parse_strip_forces_output(out)
    return _post_process_results(results, operating_point)
```

`parse_stability_output` re-implements `asb.AVL.parse_unformatted_data_output`:
scan for `" = "`, read the key backwards and the value forwards to the next
space/newline, `float()` or `NaN`, **first occurrence wins**.

### Post-processing

```
lowercase Alpha/Beta/Mach ; strip the "tot" suffix (CLtot → CL, Cl'tot → Cl')
p = (pb/2V)·2V/b     q = (qc/2V)·2V/c     r = (rb/2V)·2V/b
L = q·S·CL           Y = q·S·CY           D = q·S·CD
l_b = q·S·b·Cl       m_b = q·S·c·Cm       n_b = q·S·b·Cn
spiral parameter = "Clb Cnr / Clr Cnb"       (NaN on ZeroDivisionError)
F_w = [−D, Y, −L] → F_b → F_g ;  M_b → M_g, M_w      via op.convert_axes
```

### Strip parsing

A line state machine over AVL's `FS` stdout:

```
Surface\s+#\s*(\d+)\s+(.*)              → open a new surface dict
"# Chordwise = N  # Spanwise = M"       → metadata
"Surface area  Ssurf = X"               → metadata
header starting with "j" AND containing "Xle" AND "cl"   → table mode ON
lines starting with a digit             → split into the 15 _STRIP_COLUMNS
blank line                              → table mode OFF

_STRIP_COLUMNS = j Xle Yle Zle Chord Area c_cl ai cl_norm cl cd cdv cm_c/4 cm_LE C.P.x/c
rows with fewer than 15 values are DROPPED SILENTLY                        🟡
```

The output dict is byte-for-byte what `vlm_strip_forces` mimics, so
`_strip_surfaces_from_result` in `aero-analysis` consumes either unchanged —
this is the compatibility strategy that made ADR 0003 possible.

## Indirect-constraint trim 🟢

```
_VARIABLE_TO_AVL = {alpha: a, beta: b, roll_rate: r, pitch_rate: p, yaw_rate: y}
otherwise: the variable must be a control-surface name → "d{index}"
unknown   → ValueError listing BOTH valid sets

TrimTarget enum values ARE AVL's own tokens:
    CL = "C"   CY = "S"   PITCHING_MOMENT = "PM"
    ROLLING_MOMENT = "RM" YAWING_MOMENT   = "YM"

emitted as: "<variable> <target> <value>"      e.g.  "d1 PM 0"
injected as extra_keystrokes BEFORE the "x" execute command
```

`trim_with_avl` then categorises the flat result dict into
`aero_coefficients` / `forces_and_moments` / `trimmed_state` /
`stability_derivatives` / `trimmed_deflections` (keys ∈ the control-index map),
and declares `converged = ("CL" in raw)` — convergence is **inferred from the
presence of coefficients**, not from an AVL flag. 🟢 **`Q-AV-1`: this is
inert-false, not merely weak** — AVL's own failure branch (`LSOL = .FALSE.`)
blocks the `ST` output command entirely, so a non-converged run writes no
stability file and the runner raises `FileNotFoundError` before `"CL" in raw`
is ever evaluated. AVL prints a genuine `Trim convergence failed` marker on
stdout, which the runner already captures but does not parse. `ValueError →
422`; `FileNotFoundError` / `RuntimeError → 500` (the latter is today's
symptom for what is really a user-fixable ill-posed trim — fix: parse the
stdout marker and map a non-converged run to 422 with AVL's own message).
Enrichment (→ `aero-analysis`) is computed best-effort for converged results.

## Control-index parsing (gh-529) — REVERSED, replaces "Replay artefacts" 🟢

**`Q-AV-3`/`Q-AV-4`, ANSWERED by the maintainer, 2026-08-15.** The
geometry-hash replay artefact this section previously described is
**withdrawn and deleted**. AVL prints the surface name alongside the index in
every output block (`STITLE(N)`, `src/aoutput.f:168-174`, also in `FS`
`:290-323` and the machine-readable `STRP` block `src/aoutmrf.f:273-278`), so
the index → name map is **recoverable from every result file** and is parsed
fresh on every run instead of being cached and checked for drift:

```
# withdrawn — kept for the historical record, do not implement
compute_geometry_hash(airplane) = sha256(json(canonical))
canonical = per wing_index → per xsec_index → [(name, symmetric, hinge_point[6dp])]
AvlArtefact = {index_snapshot, run_state, avl_version}
verify_avl_replay(artefact, airplane) → None | AvlReplayMismatch(...)
```

**Why a hash could not have been trusted anyway:** `YDUPLICATE` toggled
shifts every later index by ±1 (`src/amake.f:718`) and `NSPAN` changed
renumbers strips silently — both leave the old hash **unchanged** while
invalidating the index map. A sufficient hash would have needed name, file
position, `Nchord`, `Cspace`, `Nspan`, `Sspace`, every per-section
`Nspan`/`Sspace`, `YDUPLICATE` **and** the control-name declaration order.
Parsing two fields per run is cheaper and cannot drift by construction.

**Disposition (`P-DEAD-0`/ADR 0021):** `compute_geometry_hash`, `build_artefact`,
`verify_avl_replay` and `AvlReplayMismatch` have **no production callers**
(measured 2026-08-15) and are **deleted**, not left inert.
`get_control_surface_index_map` is **unaffected** — it is **live**
(`avl_trim_service.py:134`, `avl_strip_forces.py:216`) and stays exactly as
is; index correctness was never a future-feature concern, it is relied on
today.

**Implementation notes carried forward for the parser:** prefer the
undocumented **`MRF`** machine-readable output (`ES23.15`, `src/aoper.f:103,
693-698`) over the text `FN` format (`F8.4`, which quantises small RC-scale
coefficients — `MRF` is absent from the primer). Parse the axis-orientation
line: `LSA` flips `Cl`/`Cn` on output via `DIR = ∓1`
(`src/aoutput.f:1669-1675`), printed at the head of every `FN`/`FS`/`FB`
block. Per-surface **force** signs need no correction — AVL applies `IMAGS`
internally.

**Not resolved by this decision:** `build_yduplicate_sign_map` — see
§The d-index invariant above, residual `R1`.

## Stored-geometry lifecycle 🟢

```
GET    /aeroplanes/{id}/avl-geometry             stored row, else generated on the fly
PUT    …                                         save user content
                                                   → is_user_edited = True
                                                   → is_dirty       = False
POST   …/regenerate                              DELETE the row, return fresh content
DELETE …                                         delete (404 when absent)

get_user_avl_content(db, id):
    return content only when row exists AND is_user_edited AND NOT is_dirty
    else None → the caller regenerates
```

`is_dirty` is set by the `after_insert/update/delete` listeners on `WingModel`,
`WingXSecModel` and `FuselageModel` in `avl_geometry_events.py`, which also call
`mark_ops_dirty` and publish `GeometryChanged`.
🟢 **`Q-AV-4`, ANSWERED by the maintainer 2026-08-15: `is_dirty` now clears
automatically on a successful `POST …/regenerate`.** Confirmed as a defect
first — previously nothing cleared it except a user `PUT` or an explicit
regenerate, so after any geometry edit the user-edited file was bypassed
**permanently** until the user intervened, in violation of ADR 0020. The
regenerate-clears-it decision combines with the parse-not-cache index map
(above) to close the gap without a separate hash guard.
🟡 Those same three models are **also** attached in `stability_events.py` — factored out by `Q-AA-4`, so
every geometry write fires the chain twice (out of this fold-back's question
set).

## Alternative Flows

- **No stored file / dirty / not user-edited.** The caller regenerates from the
  schema. 🟢
- **`analyze_wing` or the single-wing strip-force path.** These prune the
  airplane to one wing and therefore **never** consult the stored file — they
  always build fresh. 🟢 **`Q-AV-6`, expert consensus endorsed by the
  maintainer 2026-08-14: confirmed inconsistency, not defensible — fix is to
  merge (lift the matching `SURFACE` block, always regenerate the header from
  the pruned wing), not to swap.** See `requirements.md` BR-AV23 for the full
  fix plan.
- **Array-valued `alpha`/`beta`.** Rejected upstream in `analyse_aerodynamics`
  with `ValueError("AVL analysis does not support parameter sweeps")`. 🟢
- **The AVL binary is absent.** `_resolve_default_avl_command` falls through to
  the literal `"avl"`, and `Popen` raises `FileNotFoundError` → 500. 🟢
  **`Q-AV-7`: decided — probe for the binary and report its absence as a clean
  `capability_unavailable` error (P-WARN-0, ADR 0017), the way CadQuery and
  AeroSandbox are handled**, instead of a `FileNotFoundError` surfacing deep
  inside a run. Not yet implemented — see
  [`avl-run-and-parse/design.md`](avl-run-and-parse/design.md).
- **AVL exits non-zero but wrote `output.txt`.** Parsed normally; the exit code
  is only logged. 🟡
- **NeuralFoil returns non-finite values.** All-zero CDCL plus a warning. 🟢
- **A control-name collision.** `ValueError` **before** any file text is
  produced. 🟢
- ~~**A replay hash mismatch.**~~ **Removed** (`Q-AV-3`/`Q-AV-4`) — there is no
  hash to mismatch; the index map is parsed fresh every run. See
  §Control-index parsing above.

## Dependencies

- **`avl-binary` wheel** — the vendored AVL executable, the documented delivery
  mechanism (`.claude/rules/worktree-setup.md`). Import-guarded.
- **`aero-analysis`** — `analyse_aerodynamics` is the only caller of `AVLRunner`
  for analysis; `AnalysisModel.from_avl_dict` consumes the results;
  `compute_enrichment` enriches AVL trims.
- **`wing-design`** — `control_surface_mixing` (shared with the ASB builder and
  the enrichment service), TED roles, hinge points and mixing gains.
- **`airfoil-catalog`** — `.dat` files behind `AvlAfile`, and NeuralFoil for the
  CDCL polars.
- **`aeroplane-core`** — the aeroplane schema the geometry is built from.
- **`platform-core`** — `get_db()`, the event bus, SQLAlchemy listeners.
- **AeroSandbox** — `Atmosphere` (for `ν` in the Reynolds number), `Airfoil`
  (for `max_thickness` → `CLAF`), `op.convert_axes` in post-processing.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| The file format lives in `__repr__`, not a template | `app/avl/geometry.py` | 🟢 |
| Integer-only NACA matching, everything else is a file (gh-588) | `_NACA_RE` (`avl_geometry_service.py:52`) | 🟢 |
| Control names asserted unique **before** writing, because AVL fails silently | `assert_unique_control_names` | 🟢 |
| One shared walk produces both the d-index map and the deflection commands | `avl_strip_forces.py` | 🟢 |
| Symmetric pairs collapse to one d-index (gh-529) | `get_control_surface_index_map` / `build_control_deflection_commands` | 🟢 |
| 🟢 Mirrored-pair forces need **no** caller-applied sign (AVL applies `IMAGS` internally); `build_yduplicate_sign_map` is the CONTROL-card `SgnDup`, duplicated from `control_surface_mixing.py:45`, and is deleted rather than deleted, reachable only through the deleted `avl_artefact_service` (`R1`) | measured 2026-08-15, `Q-AV-3`/`Q-AV-4` | 🔴 |
| Three documented spacing heuristics, opt-out via `auto_optimise` | `spacing.py:71-106` | 🟢 |
| Coincident sections excluded from `min_gap` (gh-590) | `spacing.py:43-68` | 🟢 |
| User-edited CDCL always wins over a computed polar | `inject_cdcl` | 🟢 |
| The CDCL cache key is primitives only, so it is safely hashable | `lru_cache(maxsize=128)` | 🟢 |
| Non-finite NeuralFoil output → all-zero CDCL, never a fabricated polar | `neuralfoil_cdcl_service` | 🟢 |
| Every run is timed out and killed; a missing output file is a hard error | `run:280-368` | 🟢 |
| A non-zero AVL exit code is tolerated | same | 🟡 |
| ~~The replay hash excludes coordinates~~ — withdrawn: the index map is parsed per run, never hashed (`Q-AV-3`/`Q-AV-4`) | `avl_geometry_service.py:162`, AVL `STITLE(N)` | 🟢 |
| A successful `POST …/regenerate` clears `is_dirty` automatically | `Q-AV-4`, 2026-08-15 (fix not yet implemented) | 🟢 |
| `analyze_wing` consultation gap is a confirmed inconsistency; fix is a header/surface merge, not a swap | `Q-AV-6` (fix not yet implemented) | 🟢 |
| Convergence is inferred from the presence of `CL`, and the inference is unreachable-false (a non-converged run writes no stability file at all) | `avl_trim_service`, `Q-AV-1` (fix identified, not yet implemented) | 🟢 |

## Internal State

- **`avl_geometry_files`** — one row per aeroplane
  (`uq_avl_geometry_files_aeroplane_id`), `content` (Text), `is_dirty`,
  `is_user_edited`, `created_at`/`updated_at`. FK `ON DELETE CASCADE` with
  `cascade="all, delete-orphan"`.
- **`@lru_cache(maxsize=128)`** on the NeuralFoil CDCL polar — process-local,
  lost on restart, not shared between workers. 🟡
- **`TemporaryDirectory`** per run: `airplane.avl` + `output.txt`. Nothing
  persists after the call unless the caller supplies `working_directory`. 🟢
- ~~**`AvlArtefact`**~~ — **deleted** (`Q-AV-3`/`Q-AV-4`); there is no
  in-memory artefact to track, because there is nothing to persist or verify —
  the index → name map is re-derived from every run's own output. 🟢

## Observability

- A timeout raises with the elapsed limit in the message. 🟢
- A missing `output.txt` raises with the first 500 characters of stdout — the
  single most useful diagnostic when AVL rejects a geometry file. 🟢
- 🟢 A surface/wing CDCL count mismatch is now `error`-severity `DesignWarning`
  material (`Q-AV-5`), not log-only — see §CDCL injection. A non-zero AVL exit
  code stays log-only (outside this fold-back's question set).
- 🟡 Strip rows with fewer than 15 columns are dropped **silently** — a truncated
  table looks like a shorter wing.
- 🟢 `converged` carries no diagnostic today, and the inference is
  unreachable-false (`Q-AV-1`): a non-converged run never reaches the
  `converged = ("CL" in raw)` check at all, because no stability file is
  written. AVL's own `Trim convergence failed` marker is available on stdout
  and unparsed.
- 🟢 `avl_geometry_files.is_dirty` is visible in the API response; it is no
  longer the *only* signal of staleness in the sense this document previously
  implied, since a successful regenerate now clears it (`Q-AV-4`).

## Constants 🟢

| Constant | Value | Where |
|---|---|---|
| `_NACA_RE` | `^naca\s*(\d{4,5})$` | `avl_geometry_service.py:52` |
| `CLAF` formula | `1 + 0.77 · max_thickness` | `:102` |
| `SpacingConfig` defaults | `n_chord 12`, `c_space 1.0`, `n_span 20`, `s_space 1.0`, `auto_optimise True` | `app/schemas/aeroanalysisschema.py:212-219` |
| control-surface `n_chord` floor | `16` | `spacing.py:97` |
| unswept threshold / `s_space` | `5°` / `−2.0` | `spacing.py:17, :101` |
| `n_span` safety margin | `+2` on `ceil(span / min_gap)` | `spacing.py:43-68` |
| coincident-section tolerance | gap `≤ 1e-9` | `spacing.py:43-68` |
| default AVL timeout | `30 s` (callers pass `60 s`) | `avl_runner.py:102` |
| AVL filenames | `airplane.avl`, `output.txt` | `avl_runner.py:302-303` |
| gravity in the mass block | `g 9.81` | `avl_runner.py:143` |
| `_STRIP_COLUMNS` | 15 columns | `avl_strip_forces.py:15-31` |
| CDCL cache | `lru_cache(maxsize=128)` | `neuralfoil_cdcl_service.py:25` |
| `_ROLE_TAG_RE` | `^\[(\w+)\](.*)$` | `control_surface_mixing.py:25` |
| stdout excerpt on a missing output file | first `500` chars | `avl_runner.py` |

## Risks and Gaps

- 🟢 **`converged` is inferred from `"CL" in raw`, and the inference is
  inert-false, not merely weak (`Q-AV-1`, confirmed defect, fix identified).**
  A non-converged AVL run writes no stability file at all (its `LSOL =
  .FALSE.` blocks the `ST` command), so the runner raises `FileNotFoundError`
  before the inference is ever reached — today's HTTP 500 ("check avl_command
  and input geometry") is a defect that masks a user-fixable ill-posed trim.
  Fix: parse AVL's own `Trim convergence failed` stdout marker, already
  captured, and map a non-converged trim to 422 with AVL's message.
- 🟢 **`AvlBody` / `BFIL` exists but nothing constructs one — and that is a
  correct, accepted limitation, not a gap (`Q-AV-2`, ANSWERED by the
  maintainer 2026-08-15).** AVL's body model is one-way-coupled (prescribed
  from onset flow, `src/asetup.f:418-423`), has essentially zero drag by
  construction (`src/aero.f:1346-1365`) and is flagged unvalidated by its own
  author. AeroSandbox's `AeroBuildup.fuselage_aerodynamics` is a strict
  superset (adds Jorgensen cross-flow, skin friction, base drag) and is the
  **sole authority for `Cnb`** (ADR 0022) — building `BODY` would be a second,
  weaker producer. **What this question did surface as a genuine defect:** a
  `y_root ≥ 0` invariant violation on the `Wing` surface (`y_root = −0.205 m`)
  that makes `YDUPLICATE` mirror it **onto itself**, doubling the centre
  section and corrupting `Sref`, `CDi` and the reported `e` — see
  [`requirements.md`](requirements.md) `BR-AV2F`. Tracked as work (residual
  register), not as an open gap.
- 🟢 **The `.mass` and `.run` file formats are never produced, and that stays
  true — but not unconditionally (`Q-AV-8`, ANSWERED by the maintainer
  2026-08-15).** Mass properties go through the `OPER → m` keystroke submenu
  and run cases through keystrokes. Deferred behind a genuine precondition — a
  real per-component mass model with positions — not dropped: without file
  input, `Ixy`/`Iyz`/`Izx` products of inertia are unreachable (no keystroke
  exists, `src/amass.f:343-345`), which is the one AVL capability ASB's
  `get_modes` lacks (decoupled analytic approximations only, ~3× error on its
  own test fixture). Two free, inertia-light dynamic results ship instead
  without new file support: the spiral criterion
  (`|C_lβ·C_nr|` vs `|C_lr·C_nβ|`, inertia-free, already available from a VLM
  run) and the Lanchester phugoid approximation — see → `aero-analysis` /
  dynamic-stability for where these land; this module's scope stays limited to
  not producing the files.
- ~~🔴 **`AvlArtefact` is built and verified by a service no production path
  calls.**~~ **Deleted** (`Q-AV-3`/`Q-AV-4`, ADR 0021) — see §Control-index
  parsing above. Superseded by parsing the index → name map from every run's
  own output.
- 🟢 **`avl_geometry_files.is_dirty` — REVERSED (`Q-AV-4`): a successful
  regenerate now clears it automatically.** Was a confirmed defect (only a
  user `PUT` or an explicit regenerate reset it, so the escape hatch silently
  stopped taking effect after any edit); the decision closes it, combined with
  the parse-not-cache index map removing the need for a separate staleness
  check. Not yet implemented.
- 🟡 **The duplicated listeners are factored out so a geometry write publishes `GeometryChanged` once** (`Q-AA-4`, derived): both modules attach to the same three models and call the same `mark_ops_dirty`, so "each module owns its own dirty flag" does not describe the code. ADR 0022 applied to invalidation paths. Previously duplicate registration (`avl_geometry_events.py` **and**
  `stability_events.py` attach the same three models) — out of this
  fold-back's question set, unresolved.
- 🟢 **CDCL injection pairs surfaces to wings by index; a mismatch is an
  `error`-severity `DesignWarning`, not a log line (`Q-AV-5`, confirmed
  defect).** Truncated sections carry zero CDCL — no viscous drag at all — which
  is `result_truncated` under `P-WARN-0`/ADR 0020; the run must not be
  presented as a valid viscous result.
- 🟢 **`analyze_wing` never consults the stored file while `analyze_airplane`
  does — confirmed inconsistency with a fix plan (`Q-AV-6`).** Fix is a
  merge, not a swap: lift the matching `SURFACE` block verbatim, always
  regenerate `Sref`/`Cref`/`Bref`/`Xref`/`Yref`/`Zref` from the pruned wing.
  See [`requirements.md`](requirements.md) `BR-AV23`. Not yet implemented.
- 🟡 **Strip rows shorter than 15 columns are dropped silently.**
- 🟡 **A non-zero AVL exit code is tolerated**; a genuinely failed run that
  happened to write an `output.txt` will be parsed as a result.
- 🟢 **A missing AVL binary is discovered only at run time — decided: probe
  and report as a clean capability error (`Q-AV-7`).** `_resolve_default_avl_
  command` falls through to the literal `"avl"`, so `Popen` raises
  `FileNotFoundError` deep inside a run. ADR 0017 / `P-WARN-0`
  (`capability_unavailable`) apply the same pattern used for CadQuery and
  AeroSandbox. Not yet implemented — see
  [`avl-run-and-parse/design.md`](avl-run-and-parse/design.md).
- 🟡 **The CDCL cache is process-local**, so a multi-worker deployment recomputes
  per worker.
- 🟡 **`model_size` defaults differ** between this module (`"large"`) and the
  airfoil backfill (`"xxxlarge"`), so a section's CDCL and the catalogue's polar
  for the same airfoil are not necessarily consistent.
- 🟢 **`build_yduplicate_sign_map` — R1 RESOLVED, delete it.** Previously held open by
  design.** See §The d-index invariant above. This is the one item from this
  fold-back's question set; resolved 2026-08-15.
