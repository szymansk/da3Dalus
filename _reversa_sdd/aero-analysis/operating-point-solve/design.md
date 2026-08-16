# operating-point-solve — Technical Design

> Focuses on HOW this use case is built, read from the legacy code.
> Parent module design: [`../design.md`](../design.md).
> Confidence markers: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Interface

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `resolve_operating_point` | `(db, aircraft_pk, schema: OperatingPointSchema, require_trimmed: bool = True)` | `OperatingPointSchema` | gh-577 coherence guard 🟢 |
| `operating_point_model_to_schema` | `(model: OperatingPointModel)` | `OperatingPointSchema` | the **only** rad→deg conversion 🟢 |
| `_pick_deflections` | `(control_deflections \| None, controls)` | `dict[str, float]` | non-empty override wins 🟢 |
| `_require_field` | `(model, field)` | value / raises | never substitutes `0.0` 🟢 |
| `validate_deflections_against_airplane` | `(asb_airplane, deflections)` | `None` / raises 422 | BR-20 🟢 |
| `analyse_aerodynamics` | `(analysis_tool, operating_point, asb_airplane, avl_file_content=None, …)` | `(AnalysisModel, Figure \| None)` | 🟢 |
| `trim_with_aerobuildup` | `(asb_airplane, op, trim_variable, target_coefficient, target_value, bounds)` | result with `converged`, `deflection`, `warnings` | Brent 🟢 |
| `compute_enrichment` | `(result, controls, limits, trim_score, trim_method, status, …)` | `TrimEnrichment` | single entry point for **all three** trim paths 🟢 |
| `build_deflection_limits_from_schema` | `(aeroplane_schema)` | `{name: (max_pos, max_neg)}` | 🔴 keyed by the **DB TED name** (#955) |
| `decompose_dual_role` | `(role, δ_primary, δ_secondary, gains, differential_ratio)` | `MixerValues` | reporting-only kinematics 🟢 |

HTTP surface: `POST …/operating-points/trim`,
`POST …/operating-points/aerobuildup-trim`,
`POST …/operating-points/avl-trim`,
`POST /aeroplanes/{id}/wings/{wing}/{analysis_tool}`,
`POST /aeroplanes/{id}/operating_point/{analysis_tool}`,
`PATCH /operating_points/{op_id}/deflections`.
Full table in [`../contracts.md`](../contracts.md). 🟢

## Main Flow

```
1. body: OperatingPointSchema
   └─ field validator: |alpha| ≤ 180 and |beta| ≤ 180        (gh-577/gh-587)

2. resolve_operating_point(db, aircraft_pk, body, require_trimmed)
   ├─ operating_point_id is None → return body unchanged      (manual mode)
   └─ else
      ├─ SELECT … WHERE id = :op_id AND aircraft_id = :aircraft_pk
      │      (no row → NotFoundError; cross-aeroplane injection impossible)
      ├─ require_trimmed and status != TRIMMED → ValidationError
      └─ operating_point_model_to_schema(row)
         ├─ alpha_deg = degrees(row.alpha)      # row stores RADIANS
         ├─ beta_deg  = degrees(row.beta)
         ├─ _require_field(row, "velocity" | "altitude" | "xyz_ref" | …)
         └─ deflections = _pick_deflections(row.control_deflections, row.controls)
              non-empty override  → override
              empty / None        → controls        # {} must not erase a trim

3. validate_deflections_against_airplane(asb_airplane, deflections)
      unknown = set(deflections) - available
      unknown → ValidationError("unknown: …, available: …")  → 422

4. analyse_aerodynamics(tool, resolved, asb_airplane[, avl_file_content])
   ├─ op_point = asb.OperatingPoint(velocity, alpha, beta, p, q, r,
   │                                atmosphere=asb.Atmosphere(altitude))
   ├─ asb_airplane.xyz_ref = resolved.xyz_ref            # moment reference = CG
   ├─ if resolved.control_deflections:
   │        asb_airplane = asb_airplane.with_control_deflections(...)
   ├─ AEROBUILDUP     → AeroBuildup(...).run_with_stability_derivatives()
   ├─ VORTEX_LATTICE  → _remesh_airplane → VortexLatticeMethod(spanwise_resolution=1)
   └─ AVL             → AVLRunner(...).run(avl_file_content)
                         (array alpha/beta → ValueError)

5. AnalysisModel.from_abu_dict(...) | .from_avl_dict(...)
6. NonFiniteSafeJSONResponse → NaN/Inf as null
```

## Trim Flow (AeroBuildup)

```
residual(δ) = coeff(δ) − target
     coeff(δ): one AeroBuildup.run_with_stability_derivatives() with δ applied

1. resolve trim_variable
     tagged name  → itself
     display name → the surface's control variable
     role name    → that surface's PRIMARY (pitch | lift) axis      (gh-772)
       — AeroBuildup can only trim the symmetric axis; the antisymmetric axis
         carries deflection 0.0 on this path (ADR 0003, negative consequence)

2. bracket check
     if residual(lower) · residual(upper) > 0:
         return converged = False
                warning  = "root not bracketed on [lower, upper]", both residuals
         # deliberately NOT an exception

3. brentq(residual, lower, upper, xtol = 1e-6, maxiter = 50)

4. one final solve at the root → the AnalysisModel published to the caller
5. compute_enrichment(...)                      # best-effort; never fails the trim
6. persist: status, controls[name] = δ, trim_enrichment, warnings
```

## Enrichment Flow

```
limits  = build_deflection_limits_from_schema(aeroplane_schema)   # {name: (pos, neg)}
surface_deflections = dict.fromkeys(limits, 0.0) | controls       # gh-863 union

per surface:
    max_lim = resolver.limits_for(name)               🟢 Q-WD-1 (no ±25 fallback)
    usage   = |δ| / (max_pos if δ ≥ 0 else max_neg)
    usage > 0.95 → DesignWarning(critical, authority, name, "near mechanical limit")
    usage > 0.80 → DesignWarning(warning,  authority, name, "surface may be undersized")

trim quality:
    trim_score > 0.5 → critical (trim_quality) "failed to converge"
    trim_score > 0.1 → warning  (trim_quality)
    status == LIMIT_REACHED → critical (solver) "optimizer hit a constraint boundary"

stability:
    static_margin = −Cm_a / CL_a
    ≤ 0    → critical (stability) statically unstable
    < 0.05 → warning  (stability) marginal
    > 0.30 → warning  (stability) very nose-heavy

solver caveat:
    method == aerobuildup and any surface is dual-role
      → warning (solver): roll/yaw of mixed surfaces is AVL-only

mixer (per dual-role surface):
    d_sym  = mix_gain_primary   · δ_primary
    d_anti = mix_gain_secondary · δ_secondary
    right  =  d_anti ; left = −d_anti
    the negative (up-going) side is scaled by differential_ratio
    deflection_left/right = d_sym + left/right      # d_sym is never scaled
```

## Alternative Flows

- **Inline (manual) mode.** No `operating_point_id`: the body is used verbatim.
  This is the deliberate escape hatch for diagnostics. 🟢
- **`require_trimmed=False`.** A non-`TRIMMED` row is accepted for paths that
  explicitly want the untrimmed state. 🟢
- **AVL requested.** `avl_file_content` is mandatory; array `alpha`/`beta` are
  rejected with `ValueError("AVL analysis does not support parameter sweeps")`.
  The stored user geometry is consulted for `analyze_airplane` but **not** for
  `analyze_wing` (which prunes to a single wing). 🟡
- **Unbracketed trim.** `converged=False` + warning, HTTP 200. 🟢
- **Enrichment raises.** The trim response is still returned; the enrichment
  block is omitted or partial. 🟢
- **A surface exists in `limits` but never appears in `controls`.** It is
  reported at `0.0` (gh-863). 🟢
- **A control variable exists in `controls` but not in `limits`.** Its reserve
  falls back to `(25.0, 25.0)` — the #955 symptom on every dual-role aircraft.
  🔴

## Dependencies

- **`analysis_service` / `app/api/utils.py`** — the dispatcher and the
  `AnalysisModel` envelope.
- **AeroSandbox** — `AeroBuildup`, `VortexLatticeMethod`, `OperatingPoint`,
  `Atmosphere`, `Airplane.with_control_deflections`.
- **SciPy** — `optimize.brentq`.
- **`avl-integration`** — only when `analysis_tool = avl`.
- **`wing-design`** — `control_surface_mixing` supplies the axis decomposition
  and the canonical control names (gh-772); the TED rows supply the real hinge
  limits.
- **`aeroplane-core`** — the ASB airplane and the aeroplane schema behind
  `build_deflection_limits_from_schema`.
- **`platform-core`** — `get_db()` transaction boundary,
  `NonFiniteSafeJSONResponse`.

## Identified Design Decisions

| Decision | Evidence in code | Confidence |
|---|---|---|
| The OP row is queried **with** the aircraft PK, not filtered afterwards | `operating_point_resolver.py:138-213` | 🟢 |
| Radians in storage, degrees on the wire, converted in one function | `operating_point_model_to_schema` | 🟢 |
| An empty override dict is a no-op, not "clear the trim" | `_pick_deflections` | 🟢 |
| Missing NOT-NULL data raises rather than defaulting to `0.0` | `_require_field` | 🟢 |
| Unknown deflection names raise, because ASB drops them silently | `validate_deflections_against_airplane` | 🟢 |
| Non-convergence is a **return value**, not an exception | `aerobuildup_trim_service` | 🟢 |
| A role name resolves to the primary axis only, because ASB is single-axis | same (gh-772 / ADR 0003) | 🟢 |
| Every geometry surface is reported, including untrimmed ones | `dict.fromkeys(limits, 0.0)` (gh-863) | 🟢 |
| `differential_ratio` applies after trim, to the up-going side only | `decompose_dual_role` (BR-10) | 🟢 |
| `trim_residuals` is float-typed so the solver path cannot leak into it | `TrimEnrichment` (gh-627) | 🟢 |
| Enrichment limits keyed by the **DB TED name** | `build_deflection_limits_from_schema:72-118` | 🔴 defect (#955) |

## Internal State

- `operating_points.status` — see
  [`../retrim-invalidation/design.md`](../retrim-invalidation/design.md) for the
  full machine. This use case writes `TRIMMED`, `LIMIT_REACHED` and
  `NOT_TRIMMED`.
- `operating_points.controls` — the solver's output, `{control_name: degrees}`.
- `operating_points.control_deflections` — the **manual override**; `NULL` or
  `{}` means "no override".
- `operating_points.trim_enrichment` — the serialised `TrimEnrichment`.
- `operating_points.warnings` — an accumulating list; **not cleared** by a later
  successful trim. 🟡

## Observability

- `trim_method` records the solver path (`"opti"`, `"grid_fallback"`, or the
  Brent trim), never `trim_residuals` (gh-627). 🟢
- `DesignWarning{level, category, surface, message}` with
  `category ∈ {authority, trim_quality, stability, solver}` is the structured
  channel; nothing important is log-only. 🟢
- A non-bracketed trim emits a warning naming the interval and both residual
  signs. 🟢
- 🔴 On a dual-role aircraft the authority warnings are computed against ±25°
  and are therefore **silently wrong** rather than absent — the worst
  observability failure mode in this use case.

## Risks and Gaps

- 🟢 **Bug #955 is resolved structurally** (`Q-WD-1`, maintainer-answered): `control_surface_mixing` owns a resolver that trim, retrim and stability are **required** to call, and the silent ±25° fallback is removed. Keying on the raw DB TED name becomes impossible rather than merely discouraged. Previously `limits` keyed by the DB TED name vs `controls` keyed by the
  gh-772 mixing name. Fix: key both by the mixing name. Symptom: hard-coded
  ±25° reserves and a phantom 0° surface on every V-tail / elevon / flaperon
  aircraft.
- 🔴 **The `(25.0, 25.0)` default is indistinguishable from a real ±25° limit**
  in the response — nothing marks the reserve as "computed against a fallback".
- 🟡 **`analyze_wing` never consults the stored AVL geometry** while
  `analyze_airplane` does, because the wing path prunes the airplane. Two callers
  of the "same" analysis can therefore run against different geometry.
- 🟡 **The operating-point router is a plain `APIRouter()`**, so a NaN in a trim
  response is not neutralised the way it is on the analysis router.
- 🟡 **Direct `/operating_points/{id}` CRUD is not aircraft-scoped** — only the
  resolver applies the `aircraft_pk` constraint.
- 🟡 **Warnings accumulate and are never cleared**, so a row can carry a stale
  `NOT_TRIMMED` warning while its status is `TRIMMED`.
