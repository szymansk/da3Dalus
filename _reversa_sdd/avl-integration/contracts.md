# avl-integration — External Contracts

> REST contract as captured in `code-analysis.md` §Module: avl-integration and
> verified against the route decorators in
> `app/api/v2/endpoints/aeroplane/avl_geometry.py` and
> `app/api/v2/endpoints/operating_points.py`.
> 🟢 Routes are mounted at the **application root** (`prefix=""`,
> `app/main.py:211, :227`); there is no `/api/v2` path segment.
> 🟢 `{aeroplane_id}` is the public **UUID**, never the integer PK.
>
> This module also owns a **file-format contract** (the `.avl` text) and an
> **inter-module contract** (the gh-772 control-variable names). Both are
> specified below, because both are consumed outside this module.

## Global error contract 🟢

| Exception | HTTP | Envelope `code` |
|---|---|---|
| `NotFoundError` | 404 | `not_found` |
| `ValidationError` / `ValidationDomainError` | 422 | `validation_error` |
| `ConflictError` | 409 | `conflict` |
| `InternalError` | 500 | `internal_error` |
| bare `ServiceException` | 500 | `service_error` |

Module-specific mappings 🟢:

| Cause | HTTP |
|---|---|
| unknown trim variable (not an axis token and not a control-surface name) | **422** — the error lists both valid sets |
| duplicate control-variable name across surfaces | **422** (`ValueError` from `assert_unique_control_names`) |
| array-valued `alpha`/`beta` with AVL | **422** — "AVL analysis does not support parameter sweeps" |
| `RuntimeError("AVL timed out after Ns")` | **500** |
| `FileNotFoundError` — AVL wrote no `output.txt` (message carries the first 500 chars of stdout) | **500** — 🟢 for a trim run this is today's symptom of a non-converged run (`Q-AV-1`); decided fix is a **422** carrying AVL's own `Trim convergence failed` message instead, not yet implemented |
| `DELETE` on an absent stored geometry row | **404** |
| AVL binary unresolvable (wheel absent, not on `PATH`) | 🟢 **decided (`Q-AV-7`): a clean `capability_unavailable` → 503**, the same pattern as CadQuery/AeroSandbox (ADR 0017, `P-WARN-0`), replacing today's undeclared fall-through to a `FileNotFoundError` from `Popen` deep inside a run. Not yet implemented. |

---

## Stored-geometry routes — `app/api/v2/endpoints/aeroplane/avl_geometry.py` 🟢

| Method | Path | Request | Response | Status |
|---|---|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/avl-geometry` | — | `AvlGeometryResponse` | 200 · 404 · 500 |
| PUT | `/aeroplanes/{aeroplane_id}/avl-geometry` | `AvlGeometryUpdateRequest` | `AvlGeometryResponse` | 200 · 404 · 422 · 500 |
| POST | `/aeroplanes/{aeroplane_id}/avl-geometry/regenerate` | — | `AvlGeometryResponse` | 200 · 404 · 500 |
| DELETE | `/aeroplanes/{aeroplane_id}/avl-geometry` | — | — | **204** · 404 · 500 |

Semantics 🟢:

| Route | Effect |
|---|---|
| `GET` | returns the stored row when one exists, otherwise generates the file **on the fly** (nothing is persisted) |
| `PUT` | saves the user's content, setting `is_user_edited = True` **and** `is_dirty = False` |
| `POST …/regenerate` | **deletes** the stored row and returns freshly generated content |
| `DELETE` | deletes the row; 404 when absent; returns **204 No Content** |

`AvlGeometryResponse` carries the `content` text plus the row's `is_dirty` and
`is_user_edited` flags — those two booleans are the **only** signal a client has
that the served text may not describe the current geometry. 🟡

### `avl_geometry_files` — the persisted row 🟢

`UniqueConstraint(aeroplane_id)` → `uq_avl_geometry_files_aeroplane_id`
(**one row per aeroplane**).

| Column | Type | Default | Note |
|---|---|---|---|
| `aeroplane_id` | Integer FK `aeroplanes.id` `ON DELETE CASCADE`, INDEXED | — | backref `avl_geometry_file`, `cascade="all, delete-orphan"` |
| `content` | Text | — | the full `.avl` file |
| `is_dirty` | Boolean | `False` | set by the geometry listeners; 🟢 **REVERSED (`Q-AV-4`, ANSWERED by the maintainer 2026-08-15): a successful regenerate now clears it automatically** — was never auto-cleared, confirmed defect, not yet implemented |
| `is_user_edited` | Boolean | `False` | |
| `created_at` / `updated_at` | DateTime(tz) | `now()` / `onupdate now()` | |

**The consumption rule** (`get_user_avl_content`, called by every solver path):
the stored content is used **only** when the row exists **and**
`is_user_edited` **and not** `is_dirty`; otherwise the caller regenerates. 🟢

🟢 `analyze_wing` and the single-wing strip-force path never consult the stored
file at all (they prune the airplane to one wing), while `analyze_airplane`,
`trim_with_avl` and the full-airplane strip-force path do. **`Q-AV-6`,
expert consensus endorsed by the maintainer 2026-08-14: confirmed
inconsistency, not defensible — the fix is to merge (lift the stored
`SURFACE` block verbatim, always regenerate `Sref`/`Cref`/`Bref`/`Xref`/
`Yref`/`Zref` from the pruned wing), not to swap wholesale**, because AVL's
header (`Sref`/`Cref`/`Bref`, CG reference) is whole-aircraft while the
per-`SURFACE` content (spacing, `CDCL`, `CONTROL`) is not. Acceptable minimum:
report `avl_source: "user_surface+generated_header" | "generated"` on the
response so a client can at least tell. See
[`requirements.md`](requirements.md) `BR-AV23`. Not yet implemented.

---

## AVL trim — `POST /aeroplanes/{aeroplane_id}/operating-points/avl-trim` 🟢

| | |
|---|---|
| Handler | `avl_trim_operating_point` (`operating_points.py:176-202`) |
| Request | `AVLTrimRequest` — operating point + `constraints: list[TrimConstraint]` |
| Response | `AVLTrimResult` |
| Status | 200 · 404 · **422 unknown trim variable** · 500 |

### `TrimConstraint` 🟢

| Field | Type | Note |
|---|---|---|
| `variable` | `alpha` \| `beta` \| `roll_rate` \| `pitch_rate` \| `yaw_rate`, **or** a control-surface name matching `^[a-zA-Z][a-zA-Z0-9_]*$` | mapped to `a`/`b`/`r`/`p`/`y` or `d{index}` |
| `target` | `TrimTarget` | **the enum values are AVL's own tokens** |
| `value` | float | default `0.0` |

```
TrimTarget:  CL = "C"   CY = "S"   PITCHING_MOMENT = "PM"
             ROLLING_MOMENT = "RM" YAWING_MOMENT   = "YM"

emitted keystroke:  "<variable> <target> <value>"      e.g.  "d1 PM 0"
```

An unknown `variable` raises a `ValueError` listing **both** valid sets → 422. 🟢

⚠ The control-surface name in `variable` must be a name AVL knows — i.e. a
**gh-772 mixing name** for a dual-role surface. A raw DB TED name will not
resolve. 🟢 (`Q-WD-1` — the resolver makes this impossible; see
[`control-surface-naming/`](control-surface-naming/requirements.md))

### `AVLTrimResult` 🟢

| Field | Content |
|---|---|
| `converged` | 🟢 **inferred from `"CL" in raw`, and the inference is unreachable-false, not merely weak (`Q-AV-1`)** — AVL blocks its `ST` output command on a non-converged run (`LSOL = .FALSE.`), so today's `FileNotFoundError → 500` is the actual symptom, before this line ever runs. Decided fix: parse AVL's own `Trim convergence failed` stdout marker and report a genuine `converged: false` via **422** with AVL's message. Not yet implemented. |
| `trimmed_deflections` | keys ∈ the control-index map |
| `trimmed_state` | `alpha`, `beta`, `mach` |
| `aero_coefficients` | `CL CD CY Cm Cl Cn CDind CDff e CLff CYff` |
| `forces_and_moments` | `L D Y l_b m_b n_b` |
| `stability_derivatives` | `CL_a CL_b CY_a CY_b Cm_a Cn_b Cl_b Clb Cnr Clr Cnb` |
| `raw_results` | every numeric key parsed from the stability file |
| `trim_enrichment` | computed **best-effort** for converged results (→ `aero-analysis`) |

---

## Opt-in AVL on shared routes 🟢

These routes belong to `aero-analysis`
([`../aero-analysis/contracts.md`](../aero-analysis/contracts.md)) but expose
AVL as an explicit caller choice (ADR 0003):

| Route | Parameter | Default | AVL value |
|---|---|---|---|
| `POST /aeroplanes/{id}/wings/{wing}/{analysis_tool}` | path | — | `avl` |
| `POST /aeroplanes/{id}/operating_point/{analysis_tool}` | path | — | `avl` |
| `POST /aeroplanes/{id}/stability_summary/{analysis_tool}` | path | — | `avl` |
| `POST /aeroplanes/{id}/strip_forces` · `…/wings/{wing}/strip_forces` | `?solver` | `vlm` | `avl` |
| `POST /aeroplanes/{id}/spanwise_loads` · `…_with_sizing` | `?solver` | `vlm` | `avl` |
| `POST /aeroplanes/{id}/forward-cg/recompute` | `?solver` | `asb` | `avl` |

Hard-coded ASB, **no** AVL option: α sweep, simple sweep, streamlines,
three-view, `recompute_assumptions`, operating-point generation, background
retrim. 🟢

`OperatingPointSchema.cdcl_config` and `.spacing_config` are **AVL-only** fields
— they are ignored on every AeroSandbox path. 🟢

### `SpacingConfig` 🟢

| Field | Type | Default | Bounds |
|---|---|---|---|
| `n_chord` | int | `12` | 4–100 |
| `c_space` | float | `1.0` | `1` = cosine |
| `n_span` | int | `20` | 4–200 |
| `s_space` | float | `1.0` | auto-set to `−2.0` (−sine) for unswept surfaces |
| `auto_optimise` | bool | `True` | applies the three spacing rules |

### `CdclConfig` 🟢

| Field | Type | Default |
|---|---|---|
| `alpha_start_deg` / `alpha_end_deg` / `alpha_step_deg` | float | sweep bounds; step `1.0` (range 0–10) |
| `model_size` | str | `"large"` (🟡 the airfoil backfill uses `"xxxlarge"`) |
| `n_crit` | float | NeuralFoil transition criterion |
| `xtr_upper` / `xtr_lower` | float | forced-transition positions |
| `include_360_deg_effects` | bool | |

---

## File-format contract — the `.avl` text 🟢

`repr(AvlGeometryFile(...))` **is** the file. Block structure:

```
<title>
<mach>
<Iysym> <Izsym> <Zsym>
<Sref> <Cref> <Bref>
<Xref> <Yref> <Zref>
[CDp <cdp>]                       # emitted only when cdp is not ~0
SURFACE
<name>
<n_chord> <c_space> [<n_span> <s_space>]
[COMPONENT <n>]
[YDUPLICATE 0.0]                  # only when the wing is symmetric
[SCALE …] [TRANSLATE …] [ANGLE …]
[NOWAKE | NOALBE | NOLOAD]
[CDCL <cl_min> <cd_min> <cl_0> <cd_0> <cl_max> <cd_max>]
SECTION
<Xle> <Yle> <Zle> <chord> <ainc> [<n_span> <s_space>]
NACA
<digits>                          # integer NACA names only
   -- or --
AFIL
<filepath>                        # everything else, incl. decimal-bearing names
   -- or --
AIRFOIL
<x> <y> …                         # inline coordinates
[CLAF <1 + 0.77·max_thickness>]
[CDCL …]
CONTROL
<name> <gain> <xhinge> <hvec_x> <hvec_y> <hvec_z> <SgnDup>
[DESIGN <name> <weight>]
BODY                              # 🟢 emitter exists, nothing constructs one — accepted (Q-AV-2)
<name>
<n_body> <b_space>
BFIL
<bfile>
```

Guarantees consumers may rely on 🟢:

- integer NACA names (`^naca\s*(\d{4,5})$`) produce `NACA`; **everything else**,
  including `naca23013.5`, produces `AFIL` (gh-588);
- `CLAF` defaults to `1.0` when the airfoil cannot be built;
- each control appears in **two** consecutive `SECTION` blocks (`i` and `i+1`);
- `CONTROL` names are globally unique — a collision raises **before** any text is
  produced;
- `YDUPLICATE` is present exactly when the wing is symmetric — 🟢 **but see
  `Q-AV-2`: a negative `y_root` on a `YDUPLICATE` surface makes the mirror
  overlap the original instead of closing a gap; the invariant a consumer
  should actually rely on is `y_root ≥ 0` for any such surface, not yet
  asserted at build time (`requirements.md` `BR-AV2F`);**
- `CDp` is absent when zero;
- **no `BODY` block is ever emitted in production** — AVL runs are wing-only.
  🟢 **Accepted, not a gap (`Q-AV-2`, ANSWERED by the maintainer 2026-08-15):
  AeroSandbox is the sole authority for `Cnb`** (ADR 0022); AVL's `BODY` is
  one-way-coupled, essentially zero-drag by construction, and flagged
  unvalidated by its own author. A consumer must never blend or average AVL's
  wing-only `Cnb` with ASB's surfaces+body `Cnb` — they answer different
  questions.

---

## Inter-module contract — control-variable names (gh-772, ADR 0008) 🟢

`control_surface_mixing.py` is the **single source of truth** shared by the AVL
builder, the ASB airplane builder and the trim-enrichment service.

```
_DUAL_ROLE_AXES = { elevon:      (pitch, roll),
                    flaperon:    (lift,  roll),
                    ruddervator: (pitch, yaw)  }
PRIMARY_AXES   = {pitch, lift}     # symmetric      SgnDup = +1
SECONDARY_AXES = {roll,  yaw}      # antisymmetric  SgnDup = −1

axis_control_name(role, axis, wing_key, xsec_index)
    → f"[{role}]{axis}_{sanitize(wing_key)}_{xsec_index}"
      e.g. "[ruddervator]pitch_htail_1"
_ROLE_TAG_RE = ^\[(\w+)\](.*)$
```

`ControlAxis` (`control_surface_mixing.py:41`):

| Field | Type | Note |
|---|---|---|
| `name` | str | the mixing name for dual roles; the existing tagged name otherwise |
| `sgn_dup` | float | `+1` symmetric, `−1` antisymmetric — a **sign flag**, never a magnitude |
| `gain` | float | the AVL `gain` column (`mix_gain_primary` / `_secondary`) |
| `symmetric` | bool | `True` → pitch/lift axis |
| `hinge_point` | float | chord fraction |
| `deflection` | float | baseline; the antisymmetric dual axis is forced to **`0.0`** |
| `role` | str | `elevator`\|`stabilator`\|`aileron`\|`rudder`\|`flap`\|`elevon`\|`flaperon`\|`ruddervator`\|`other` |
| `axis` | str | `pitch`\|`lift`\|`roll`\|`yaw`\|`""` |

Dual-role emission table 🟢:

| axis | `SgnDup` | gain | `symmetric` | baseline deflection |
|---|---|---|---|---|
| primary (`pitch` \| `lift`) | `+1.0` | `mix_gain_primary` | `True` | the surface's deflection |
| secondary (`roll` \| `yaw`) | `−1.0` | `mix_gain_secondary` | `False` | **`0.0`** |

🟢 **Bug #955 is resolved structurally** (`Q-WD-1`): the consumers obtain names through the mixing layer's resolver. These names are the contract, and previously
`trim_enrichment_service`, `retrim_service` and `stability_service` still key on
the **raw DB TED name**. Any client or module resolving a control surface **must
use the mixing name**.

---

## Control-index contract (gh-529) — REVERSED, replaces "Replay artefact contract" 🟢

**`Q-AV-3`/`Q-AV-4`, ANSWERED by the maintainer, 2026-08-15: there is no
replay artefact and none is needed.** `AvlArtefact`, `AvlIndexSnapshot`,
`AvlRunState` and `AvlReplayMismatch` are **withdrawn and deleted**
(`P-DEAD-0`/ADR 0021 — measured 2026-08-15, no production callers).

Not exposed over HTTP. The contract any AVL-consuming caller can rely on
instead: **the control-surface index → name mapping is parsed from every AVL
result, never cached.** AVL prints the surface name alongside the index in
every output block — `STITLE(N)` (`src/aoutput.f:168-174`, `FS`
`:290-323`, machine-readable `STRP` `src/aoutmrf.f:273-278`) — so a caller
never needs to persist or verify a snapshot; a geometry edit between two runs
cannot produce a stale mapping, because nothing is cached to go stale.
`get_control_surface_index_map` remains the live producer of this map on the
trim path (`avl_trim_service.py:134`) and in
`build_indirect_constraint_commands` (`avl_strip_forces.py:216`) — unaffected
by this decision.

**Not resolved by this decision — `R1`:** whether mirrored (`YDUPLICATE`)
surfaces' strip forces are summed with the correct **sign** into spar loads
(`/spanwise_loads_with_sizing`) is a separate, still-open question.
`build_yduplicate_sign_map` is **deleted** — a duplicate of `control_surface_mixing.py:45`'s `sgn_dup` (ADR 0022) 🟢 — see
[`requirements.md`](requirements.md) `BR-AV13`.

## Not part of this contract

- The default solver stack, the aero context, sweeps, the operating-point
  lifecycle → `aero-analysis`
  ([`../aero-analysis/contracts.md`](../aero-analysis/contracts.md)).
- Wing geometry, TED CRUD, hinge points and mixing gains → `wing-design`
  ([`../wing-design/contracts.md`](../wing-design/contracts.md)).
- Airfoil `.dat` files and low-Re polars → `airfoil-catalog`.
- `.mass` and `.run` files — **never produced anywhere**. 🟢 **Deferred, not
  dropped (`Q-AV-8`, ANSWERED by the maintainer 2026-08-15):** blocked behind
  a real per-component mass model with positions; the spiral criterion and
  Lanchester phugoid ship as free, inertia-light substitutes for the dynamic
  results that matter at RC/UAV scale → `aero-analysis` / dynamic-stability.
- Fuselage modelling in AVL — the `AvlBody` emitter exists but nothing
  constructs one. 🟢 **Accepted (`Q-AV-2`)** — AeroSandbox is the sole `Cnb`
  authority; see §File-format contract above for the invariant this question
  did surface as a genuine defect.
