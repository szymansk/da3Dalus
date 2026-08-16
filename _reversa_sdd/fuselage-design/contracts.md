# fuselage-design — External Contracts

> REST contract exactly as captured in `code-analysis.md` §Module:
> fuselage-design. All routes are mounted at the **application root** — there is
> no `/api/v2` segment. 🟢 `{aeroplane_id}` is always the **public UUID**. 🟢
> A fuselage is addressed by its **name**, a cross-section by its **index**.

## Global error contract 🟢

The shared `_raise_http_from_domain` mapping applies
(`app/api/v2/endpoints/aeroplane/base.py:52-67`):

| Exception | HTTP | Envelope `code` |
|---|---|---|
| `NotFoundError` | 404 | `not_found` |
| `ValidationError` / `ValidationDomainError` | 422 | `validation_error` |
| `ConflictError` | 409 | `conflict` |
| `InternalError` | 500 | `internal_error` |
| bare `ServiceException` | 500 | `service_error` |

```json
{ "error": { "code": "conflict", "message": "…", "details": { … } } }
```

**Duplicate-name contract: 409, confirmed correct (`Q-FD-1`).**
`create_fuselage` raises `ConflictError` → **409** for a name collision with
an existing sibling. This is the intended discriminator: a *create* whose
payload would succeed against a different aeroplane is a conflict with
persisted state, not an unreadable payload. `create_wing`'s
`ValidationError` → **422** for the same situation
(`wing_service.py:285-289`) was the divergent outlier and is being aligned to
409 — see `wing-design/contracts.md`. Both error messages must name the
colliding item. 🟢 CONFIRMED.

## Unit contract for this module 🟢

| Quantity | Unit |
|---|---|
| `xyz` (cross-section centre) | **metres** |
| `a` — **Y half-axis** (semi-width) | **metres** |
| `b` — **Z half-axis** (semi-height) | **metres** |
| `n` — superellipse exponent | dimensionless (`2` = ellipse) |
| `volume_ratio`, `area_ratio` | dimensionless ratios |
| `step_path`, `solid_step_path` | relative paths under `ARTIFACTS_BASE_DIR` |

There is **no** millimetre exception in this module — unlike
`wing_xsec_spares` (gh-402). `a` and `b` are **half-axes, not diameters**;
they map to ASB `FuselageXSec.width` / `.height` respectively (gh-706,
`app/schemas/aeroplaneschema.py:711-723`). 🟢

**Decided mechanism, not a bare assertion (`Q-FD-3`, expert consensus endorsed
by the maintainer 2026-08-14) — not yet implemented.** The two independent
`2.0 * a` conversions (`cad_designer/aerosandbox/slicing.py:1291-1300`,
`app/converters/openvsp_fuselage_handler.py:215`) collapse into one
`superellipse_to_asb_xsec(a, b, n)` seam so the convention holds by
construction; a swap (`a ↔ b`) is caught at import time against the source
STEP bounding box (`2a ≤ 1.02·Y_extent`, `2b ≤ 1.02·Z_extent`, whole-body
aspect ratio within 20 %), and where no source survives, `2a/2b ∈ [0.3, 3.0]`
is a `severity="warning"` plausibility band, never an exception — a
genuinely 4:1 flat foamie fuselage exists. 🟢

## Fuselage routes — `app/api/v2/endpoints/aeroplane/fuselages.py` 🟢

Base path: `/aeroplanes/{aeroplane_id}/fuselages`

| Method | Path suffix | Operation | Request | Response | Status |
|---|---|---|---|---|---|
| GET | `` | list fuselage names | — | `list[str]` | 200 · 404 · 500 |
| PUT | `/{fuselage_name}` | create | `FuselageSchema` | `FuselageSchema` | 201 · **409 duplicate name** · 404 · 422 · 500 |
| POST | `/{fuselage_name}` | update (**destructive replace**) | `FuselageSchema` | `FuselageSchema` | 200 · 404 · 422 · 500 |
| GET | `/{fuselage_name}` | read | — | `FuselageSchema` | 200 · 404 · 500 |
| DELETE | `/{fuselage_name}` | delete | — | `OperationStatusResponse` | 200 · 404 · 500 |
| GET | `/{fuselage_name}/step` | download the Surface STEP (l.198) | — | file | 200 · 404 · 500 |
| GET | `/{fuselage_name}/solid_step` | download the sewed Solid STEP (l.234) | — | file | 200 · 404 · 500 |

**Side effects.** Create and update drive `sync_group_for_fuselage`; delete calls
`delete_synced_nodes("fuselage:<name>")` (gh#108,
`fuselage_service.delete_fuselage:179-181`). 🟢

⚠ **`POST /{fuselage_name}` replaces rather than merges — today.** The old
`FuselageModel` is removed from the collection and a new one appended
(`fuselage_service.py:120-122`), so `step_path` and `solid_step_path` **not
echoed in the payload are lost**. Per `Q-FD-7` (answered by the maintainer,
2026-08-15) this is decided as a defect: the target contract **preserves**
`step_path` / `solid_step_path` when the payload omits them, the same
principle as issue #1094 — a partial update must not destroy what it does not
mention. 🟢 CONFIRMED behaviour; 🟢 CONFIRMED target, not yet implemented.

### `FuselageSchema` — request/response body 🟢

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `name` | `str` | yes | — | |
| `x_secs` | `list[FuselageXSecSuperEllipseSchema]` | yes | — | **`min_length=2`** |
| `symmetric` | `bool` | no | **`False`** | XZ-mirror flag (gh-715); consumers duplicate geometry with `y → −y`. Defaults `False` because the main fuselage sits on the symmetry plane — the **opposite** of `wings.symmetric` |
| `step_path` | `str \| None` | no | `None` | relative Surface STEP path |
| `solid_step_path` | `str \| None` | no | `None` | relative Solid STEP path; `None` when sewing failed or the fuselage was not VSP-imported |

(`app/schemas/aeroplaneschema.py:755`.)

### `FuselageXSecSuperEllipseSchema` 🟢

| Field | Type | Required | Unit | Notes |
|---|---|---|---|---|
| `xyz` | `list[float]` | yes | metres | section centre `[x, y, z]` |
| `a` | `float` | yes | metres | **Y half-axis** → ASB `width` |
| `b` | `float` | yes | metres | **Z half-axis** → ASB `height` |
| `n` | `float` | yes | — | exponent; `2` = ellipse, larger → rectangular |

(`app/schemas/aeroplaneschema.py:711`.) Shape law:
`|y/a|^n + |z/b|^n = 1`. 🟢

## Cross-section routes 🟢

Base path: `/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/cross_sections`

| Method | Path suffix | Operation | Status |
|---|---|---|---|
| GET | `` | list cross-sections in `sort_index` order (`fuselage_service.py:193`) | 200 · 404 · 500 |
| DELETE | `` | delete all cross-sections, keeping the fuselage row (`:219`) | 200 · 404 · 500 |
| GET | `/{index}` | read one (`:244`) | 200 · 404 · 500 |
| POST | `/{index}` | create (`:276`) | 201 · 404 · 422 · 500 |
| PUT | `/{index}` | update (`:327`) | 200 · 404 · 422 · 500 |
| DELETE | `/{index}` | delete (`:364`) | 200 · 404 · 500 |

An out-of-range index yields **404**. 🟡 INFERRED from the service's
`NotFoundError` usage pattern; the exact bound check was not read.

## STEP slicing route — `app/api/v2/endpoints/fuselage_slice.py` 🟢

### `POST /slice`

| | |
|---|---|
| Handler | `fuselage_slice.py:18` |
| Request | multipart upload; the file must have a `.step` or `.stp` extension |
| Parameters | `number_of_slices: int = 50` (`Form(ge=2, le=500)`), `points_per_slice: int = 30` (`10 ≤ … ≤ 200`), `slice_axis: str = "auto"`, `fuselage_name: str = "Imported Fuselage"` |
| Response | `FuselageSliceResponse` |
| Status (**current**) | 200 · **422 wrong extension** · **500 when CadQuery is unavailable** · 500 |
| Status (**target, `Q-FD-5`, not yet implemented**) | **202 Accepted** with a task id, plus a status endpoint returning `FuselageSliceResponse` on completion · 422 · 500 |
| Cost | CPU-bound, documented **5–30 s** |

Note this route is **standalone** — it is not nested under an aeroplane and does
not persist anything. It returns a `FuselageSchema` that the caller may then
`PUT` under an aeroplane. 🟢

⚠ **Decided to change (`Q-FD-5`, answered by the maintainer, 2026-08-15):**
this is the one CPU-bound operation of this duration in the system that is
still synchronous. It joins the task model — `202` plus a status endpoint —
like every other long CAD operation; the single-user product position
(ADR 0024) removes the *throughput* concern but not the missing progress,
cancellation and timeout, which the task model supplies. The timeout is part
of this change, not a follow-up. Client-visible break, affordable because
every consumer lives in this repository (ADR 0024); must land before
TypeScript client generation (`Q-CC-11`). Not yet implemented.

### `FuselageSliceResponse` — significant fields 🟢

| Field | Type | Meaning |
|---|---|---|
| (fuselage) | `FuselageSchema` | the fitted superellipse stack |
| `volume_ratio` | float | reconstructed loft volume ÷ original solid volume |
| `area_ratio` | float | reconstructed surface area ÷ original |
| `original_tessellation_url` | `null` | hard-coded `None` — STL export not wired (`fuselage_slice_service.py:113-115`) |
| `reconstructed_tessellation_url` | `null` | idem |

Any non-finite value produced by the fit is replaced by `null` before the
response is built (GH#301). 🟢

**Fidelity is graded, per `Q-FD-4` (answered 2026-08-14, endorsed by the
maintainer) — decided, not yet implemented.** `volume_ratio` / `area_ratio` ∈
`[0.95, 1.05]` is silent; `[0.85, 0.95) ∪ (1.05, 1.15]` emits a `DesignWarning`
(`P-WARN-0`) at `severity="info"`; `[0.70, 0.85) ∪ (1.15, 1.40]` emits
`severity="warning"`; outside `[0.70, 1.40]`, or `volume_ratio ≤ 0.05`, or
non-finite, the **slice is rejected** rather than returned. A per-station `n`
sitting at the `[0.5, 8.0]` optimiser bound also emits `info`, escalating to
`warning` once more than 25 % of stations hit a bound. 🟢

### Security guarantees on this route 🟢

| Guarantee | Evidence |
|---|---|
| Only `.step` / `.stp` are accepted, checked **before** any filesystem write | `fuselage_slice_service.py:28-116` |
| The filename is reduced to its **basename**; the resolved temp path is verified with `is_relative_to` (path-traversal guard, S2083) | `fuselage_slice_service.py:50-64` |
| The temp directory is `rmtree`d in a `finally` block regardless of outcome | `fuselage_slice_service.py` (slice flow) |
| The geometry kernel is lazy-imported, so a missing CadQuery yields a clean 500 rather than a start-up failure | `fuselage_slice_service.py:42-48` (ADR 0017) |

## Fitting contract (behavioural, not a wire format) 🟢

A caller reimplementing the slice pipeline must reproduce:

```
r(θ)        = ( |cos θ / a|^n + |sin θ / b|^n )^(−1/n)
perimeter   = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ          (quad, limit = 200)
area        = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)

centre      = [0, mean(z)]                            (forced onto the Z axis)
points      = mirrored (θ → −θ, same r)               (enforced symmetry)

radius_loss = mean( (r_i − r_fit(θ_i))² )
length_loss = (perimeter_fit − perimeter_actual)²
objective   = radius_loss + 0.01 · length_loss

optimiser   = scipy.optimize.minimize, method "L-BFGS-B"
x0          = [1.0, 1.0, 2.0]
bounds      = a, b ∈ (1e-3, ∞) ;  n ∈ [0.5, 8.0]
```

(`cad_designer/aerosandbox/slicing.py:585-608, 610-661`.) 🟢

## Not part of this contract

- Writing `step_path` (→ `openvsp-import`, gh-729) or `solid_step_path`
  (→ `openvsp_solid_sewing_service`, gh-731).
- Building the CAD solid that consumes `solid_step_path`, or the scheduled
  xsec-loft fallback used when `solid_status != ok` (`Q-VI-4 ③`)
  → `cad-generation`.
- The ASB fuselage drag/stability model over the xsec stack → `aero-analysis`.
- `FuselageConfiguration` itself → `cad-designer-topology` (frozen, ADR 0002);
  its `from_step_file` factory is 🟢 **confirmed dead**
  (`analysis_specific_options = {dict(...)}` raises `TypeError` on every
  execution) and its removal is recorded in `requirements.md`, not executed
  (`Q-FD-8`, `P-DEAD-0`).
- MCP tool wrappers that re-enter these handlers in-process → `mcp-server`.
