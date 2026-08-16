# cg-mass-computation — Technical Design

> Use-case design, nested under the module [`mass-and-balance`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Pure functions (no session) 🟢

| Symbol | Signature | Line |
|---|---|---|
| `compute_recommended_cg` | `(np_x: float, mac: float, target_static_margin: float) -> float` | 36 |
| `compute_design_metrics` | `(mass_kg, s_ref, cl_max, rho, velocity) -> DesignMetricsResponse` | 41 |
| `aggregate_weight_items` | `(Sequence[WeightItemData]) -> tuple[float\|None, float\|None, float\|None, float\|None]` | 78 |

### DB-aware functions 🟢

| Symbol | Signature | Line | Raises |
|---|---|---|---|
| `_get_aeroplane` | `(db, uuid) -> AeroplaneModel` | 105 | `NotFoundError` |
| `get_effective_assumption_value` | `(db, uuid, param_name) -> float` | 112 | `NotFoundError` |
| `get_cg_comparison` | `(db, uuid) -> CGComparisonResponse` | 224 | `NotFoundError` |
| `get_s_ref_for_aeroplane` | `(db, uuid) -> float` | 252 | `ValidationError`, `InternalError` |
| `get_design_metrics_for_aeroplane` | `(db, uuid, velocity, altitude) -> DesignMetricsResponse` | 271 | the union of the above |

### Constants 🟢

| Constant | Value | Meaning |
|---|---|---|
| `GRAVITY` | `9.81` m/s² | used by `compute_design_metrics` only |
| `CG_TOLERANCE_M` | `0.01` m | the `within_tolerance` threshold |

### REST surface 🟢

| Method | Path | In | Out |
|---|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/design_metrics` | `DesignMetricsRequest{velocity=15 (gt 0), altitude=0 (ge 0)}` | `DesignMetricsResponse` |
| GET | `/aeroplanes/{aeroplane_id}/cg_comparison` | — | `CGComparisonResponse` |

## Main Flow

### F1 — Aggregation (`aggregate_weight_items`, l.78-97) 🟢

```
if not items:            return None, None, None, None
total_mass = Σ it["mass_kg"]
if total_mass <= 0:      return None, None, None, None

cg_x = Σ (mᵢ · xᵢ) / total_mass
cg_y = Σ (mᵢ · yᵢ) / total_mass
cg_z = Σ (mᵢ · zᵢ) / total_mass
return total_mass, cg_x, cg_y, cg_z
```

Two early returns, one arithmetic block, no rounding. The input is a sequence of
`WeightItemData` dicts (`TypedDict{mass_kg, x_m, y_m, z_m}`), never ORM
instances — the callers map their rows down to that shape first
(`:201-203, 231`). 🟢

### F2 — Effective value (`get_effective_assumption_value`, l.112-128) 🟢

```
aeroplane = _get_aeroplane(db, uuid)                       # NotFoundError
row = design_assumptions WHERE aeroplane_id=? AND parameter_name=?
if row is None:
    raise NotFoundError(entity="DesignAssumption", resource_id=param_name)
if row.active_source == "CALCULATED" and row.calculated_value is not None:
    return row.calculated_value
return row.estimate_value
```

The `and row.calculated_value is not None` clause is load-bearing: an assumption
that was switched to CALCULATED and then had its value cleared (an empty mass
producer, BR-MB3) falls back to the estimate rather than returning `None`. 🟢

🟡 The sibling resolver `design_assumptions_service.get_effective_assumption`
returns a `PARAMETER_DEFAULTS` fallback and `None` instead of raising. Two
resolvers, two contracts, one database.

### F3 — CG comparison (`get_cg_comparison`, l.224-249) 🟢

```
_get_aeroplane(db, uuid)                                   # 404 on unknown
design_cg_x = get_effective_assumption_value(db, uuid, "cg_x")   # 404 if unseeded

rows  = weight_items WHERE aeroplane_id = aeroplane.id
items = [{mass_kg, x_m, y_m, z_m}, …]
total, cg_x, cg_y, cg_z = aggregate_weight_items(items)

delta_x = within_tolerance = None
if cg_x is not None:
    delta_x          = design_cg_x - cg_x
    within_tolerance = abs(delta_x) < CG_TOLERANCE_M       # strict <

return CGComparisonResponse(design_cg_x, cg_x, cg_y, cg_z, total,
                            delta_x, within_tolerance)
```

The comparison reads the **inventory only** — the component tree's masses have
no positions in this path, so an aircraft built entirely in the tree gets a
`null` comparison even though its mass is known. 🟡 `Q-MB-4` routes it through the tree.

Sign convention: `delta_x > 0` ⇒ the *design* CG sits aft of the *component*
CG, i.e. the built aircraft is nose-heavy relative to the stability
requirement. 🟡 inferred from the subtraction order; the code does not say so.

### F4 — Reference area (`get_s_ref_for_aeroplane`, l.252-268) 🟢

```
from app.converters.model_schema_converters import aeroplane_schema_to_asb_airplane_async
from app.services.analysis_service import get_aeroplane_schema_or_raise   # both lazy

plane_schema = get_aeroplane_schema_or_raise(db, uuid)
try:
    asb_airplane = aeroplane_schema_to_asb_airplane_async(plane_schema=plane_schema)
except Exception as e:
    logger.error(...); raise InternalError(f"Could not compute wing reference area: {e}")

s_ref = float(getattr(asb_airplane, "s_ref", 0.0) or 0.0)
if s_ref <= 0:
    raise ValidationError("Wing reference area (s_ref) is zero or negative — add wings first")
return s_ref
```

The `getattr(..., 0.0) or 0.0` double-default tolerates both a missing attribute
and a `None`, funnelling every degenerate case into the single actionable
`ValidationError`. 🟢

Note what this function does **not** do: it does not read
`assumption_computation_context["s_ref_m2"]`, which the gh-924 context already
carries and which `powertrain_solution_space_service` uses. Two paths to one
number. 🟡

### F5 — Design metrics (`get_design_metrics_for_aeroplane`, l.271-282) 🟢

```
import aerosandbox as asb                                  # lazy (ADR 0017)

mass_kg = get_effective_assumption_value(db, uuid, "mass")
cl_max  = get_effective_assumption_value(db, uuid, "cl_max")
s_ref   = get_s_ref_for_aeroplane(db, uuid)
rho     = asb.Atmosphere(altitude=altitude).density()
return compute_design_metrics(mass_kg, s_ref, cl_max, rho, velocity)
```

### F6 — The metric block (`compute_design_metrics`, l.41-75) 🟢

```
reject mass_kg <= 0   -> "mass_kg must be positive"
reject s_ref   <= 0   -> "s_ref must be positive"
reject cl_max  <= 0   -> "cl_max must be positive"
reject rho     <= 0   -> "rho must be positive"
reject velocity<= 0   -> "velocity must be positive"

weight       = mass_kg * GRAVITY                 # 9.81
wing_loading = weight / s_ref
stall_speed  = sqrt(2 * weight / (rho * s_ref * cl_max))
q            = 0.5 * rho * velocity**2
required_cl  = weight / (q * s_ref)
cl_margin    = cl_max - required_cl
```

Five guards for five denominators/roots — after them, none of the six
expressions can divide by zero or take the root of a negative. That is why the
response has no nullable field. 🟢

### F7 — The top-down rule (`compute_recommended_cg`, l.36-38) 🟢

```
return np_x - target_static_margin * mac
```

One line, fully tested — and it becomes the single authority with a production caller (`Q-MB-2`). 🟢

## Alternative Flows

- **Unknown aeroplane UUID:** `NotFoundError` → **404** on both routes. 🟢
- **Missing `cg_x` / `mass` / `cl_max` assumption row:** `NotFoundError` →
  **404**, indistinguishable from "aeroplane not found" in the bare
  `{"detail": …}` envelope. 🟢 One envelope everywhere (`Q-CC-3`).
- **Assumption switched to CALCULATED with a cleared value:** falls back to the
  estimate (F2). 🟢
- **Empty or zero-mass inventory:** four `None`s from F1 ⇒ `delta_x` and
  `within_tolerance` are `None`; `design_cg_x` is still returned. 🟢
- **Aeroplane with no wings:** `ValidationError` → **422** *"… add wings
  first"*. 🟢
- **ASB conversion raises:** logged, wrapped in `InternalError` → **500**
  *"Could not compute wing reference area: …"*. 🟢
- **`aerosandbox` not installed (`linux/aarch64`):** the lazy import raises
  `ImportError`, which is not a `ServiceException`, so `_call` answers **500**
  *"Unexpected error: …"* rather than a 501/503. 🟡
- **Δx exactly `CG_TOLERANCE_M`:** `within_tolerance` is `False` — the
  comparison is strict. 🟢
- **NaN/Inf in a metric:** unreachable given F6's guards, but the router does
  **not** use `NonFiniteSafeJSONResponse`, so it would serialise as invalid
  JSON. 🟡

## Dependencies

- **`mission-and-sizing` (`design_assumptions`)** — read-only, through the local
  resolver. This use case never writes an assumption.
- **[`weight-items`](../weight-items/design.md)** — supplies the rows the
  aggregation consumes; both the comparison and the sync map them to
  `WeightItemData`.
- **`aero-analysis` (`analysis_service.get_aeroplane_schema_or_raise`)** and
  **`app/converters/model_schema_converters`** — the `s_ref` path; both imported
  inside the function.
- **AeroSandbox** — `asb.Atmosphere` (ISA ρ) and the airplane builder; lazy
  (ADR 0017).
- **ADR 0011** — the reason `compute_recommended_cg` and
  `aggregate_weight_items` are separate functions with separate destinations.
- **ADR 0012** — the reason absent values are `None` and bad inputs raise.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Requirement CG and status CG are different formulas with different destinations | `:36` vs `:78`; ADR 0011 | 🟢 |
| The aggregation is pure and dict-typed, not ORM-bound | `WeightItemData:24`, `:78-80` | 🟢 |
| An absent aggregate produces `None` verdicts, not `False` | `:235-239` | 🟢 |
| The tolerance comparison is strict `<`, so the boundary value fails | `:239` | 🟢 |
| Every metric input is validated up front so the response has no nullable field | `:49-58` | 🟢 |
| A degenerate `s_ref` produces a remediation sentence, not a stack trace | `:265-267` | 🟢 |
| `s_ref` is recomputed from geometry rather than read from the gh-924 context | `:252-268` | 🟡 read from the gh-924 context, not rebuilt (ADR 0022) (duplication) |
| The local effective-value resolver raises where the shared one defaults | `:123-124` | 🟢 |
| Heavy imports live inside the functions that need them | `:254-255, 275` | 🟢 |
| `GRAVITY = 9.81` here, `9.80665` in the powertrain stack | `:20` | 🟢 |

## Internal State

None. Every function in this use case is either pure or a read-only resolver:
no row is created, updated or deleted, and nothing is cached between requests.
The CG comparison and the design metrics are recomputed from scratch on every
call — including the ASB airplane build. 🟢

## Observability

- `logger.error("Error building ASB airplane for s_ref: %s", e)` — the only log
  line in the whole use case. 🟢
- The `mass_cg` router's `_call` logs its catch-all with `exc_info=True` before
  raising the 500. 🟢
- Nothing records how often a CG comparison lands outside tolerance, how far
  outside, or how long the ASB build takes. The one number a designer would
  most want trended — Δx over time — is computed per request and discarded. 🟡

## Risks and Gaps

- 🟢 **The comparison reads the component tree** (`Q-MB-4`, derived from `Q-MB-1`), which ultimately becomes the only CG source. Previously only `weight_items` had
  positions, so an aircraft built entirely in the tree has a known mass and no
  CG — the comparison returns `null` with no explanation of why.
- 🟡 **Two resolvers for one effective value**, one raising and one defaulting — ADR 0022 requires one.
- 🟢 **One implementation** (`Q-MB-2`): `compute_recommended_cg` is the authority and the duplicates are removed. Previously two in production plus this third,
  uncalled one.
- 🟡 **Two `s_ref` paths** — ADR 0022 and the gh-924 single-source ruling (`Q-AA-*`) require reading the context rather than rebuilding. This ASB rebuild and the gh-924 context's
  `s_ref_m2`; nothing asserts they agree.
- 🟡 **Two gravity constants** (`9.81` / `9.80665`) — collapse into one physical-constants module (`Q-MB-8`, derived).
- 🟢 **`cg_y` / `cg_z` reach consumers** (`Q-MB-3`): aileron trim and thrust-line arm.
- 🟡 **A missing assumption row and a missing aeroplane are the same 404** — the single envelope (`Q-CC-3`) requires distinguishable `code` values to
  the client, because the envelope carries no entity code.
- 🟡 **The ASB build is uncached and unbounded.** Every `design_metrics` call
  pays for a full geometry conversion to read one float; a UI that polls the
  metrics panel pays it repeatedly.
- 🟡 **The sign convention of `delta_x` is undocumented** in the code and
  therefore easy to invert in a UI.
- 🟡 **`ImportError` on ASB-less platforms surfaces as a generic 500** rather
  than a capability signal.
</content>
