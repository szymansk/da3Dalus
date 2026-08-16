# superellipse-xsecs — Technical Design

> Use-case design, nested under module [`fuselage-design`](../design.md).
> Focuses on HOW this slice is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Module endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Service surface — `app/services/fuselage_service.py` (403 l.) 🟢

| Symbol | Signature | Returns | Line |
|---|---|---|---|
| `list_fuselage_names` | `(db, aeroplane_uuid)` | `list[str]` | l.45 |
| `create_fuselage` | `(db, aeroplane_uuid, name, payload)` | `FuselageModel` | l.63 |
| `update_fuselage` | `(db, aeroplane_uuid, name, payload)` | `FuselageModel` | l.103 |
| `get_fuselage` | `(db, aeroplane_uuid, name)` | `FuselageModel` | l.137 |
| `delete_fuselage` | `(db, aeroplane_uuid, name)` | `None` | l.160 |
| `get_fuselage_cross_sections` | `(db, aeroplane_uuid, name)` | `list[FuselageXSecSuperEllipseModel]` | l.193 |
| `delete_all_cross_sections` | `(db, aeroplane_uuid, name)` | `None` | l.219 |
| `get_cross_section` | `(db, …, index)` | xsec | l.244 |
| `create_cross_section` | `(db, …, payload)` | xsec | l.276 |
| `update_cross_section` | `(db, …, index, payload)` | xsec | l.327 |
| `delete_cross_section` | `(db, …, index)` | `None` | l.364 |

### Routes owned by this slice 🟢

Base: `/aeroplanes/{aeroplane_id}/fuselages` — full detail in
[`../contracts.md`](../contracts.md).

| Method | Path suffix | Operation | Status |
|---|---|---|---|
| GET | `` | list fuselage names | 200 · 404 · 500 |
| PUT | `/{fuselage_name}` | create | 201 · **409** · 404 · 422 · 500 |
| POST | `/{fuselage_name}` | update (destructive replace) | 200 · 404 · 422 · 500 |
| GET | `/{fuselage_name}` | read | 200 · 404 · 500 |
| DELETE | `/{fuselage_name}` | delete | 200 · 404 · 500 |
| GET | `/{fuselage_name}/step` | download Surface STEP (`fuselages.py:198`) | 200 · 404 · 500 |
| GET | `/{fuselage_name}/solid_step` | download Solid STEP (`fuselages.py:234`) | 200 · 404 · 500 |
| GET | `/{fuselage_name}/cross_sections` | list, `sort_index` order | 200 · 404 · 500 |
| DELETE | `/{fuselage_name}/cross_sections` | delete all, keep the fuselage | 200 · 404 · 500 |
| GET | `/{fuselage_name}/cross_sections/{index}` | read one | 200 · 404 · 500 |
| POST | `/{fuselage_name}/cross_sections/{index}` | create | 201 · 404 · 422 · 500 |
| PUT | `/{fuselage_name}/cross_sections/{index}` | update | 200 · 404 · 422 · 500 |
| DELETE | `/{fuselage_name}/cross_sections/{index}` | delete | 200 · 404 · 500 |

The standalone `POST /slice` belongs to
[`step-slicing/`](../step-slicing/design.md), not here. 🟢

### Data model 🟢

```
fuselages ──1:N (ordered by sort_index, cascade delete-orphan)──▶ fuselage_xsecs
```

`fuselages` (`FuselageModel`, `app/models/aeroplanemodel.py:526`):

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `name` | String | yes | — | addressed by name, not id |
| `symmetric` | Boolean | yes | **`False`** | gh-715 XZ-mirror flag |
| `step_path` | String | no | `NULL` | relative Surface STEP path |
| `solid_step_path` | String | no | `NULL` | relative Solid STEP path |
| `aeroplane_id` | Integer FK → `aeroplanes.id` `ON DELETE CASCADE` | no | — | |

`fuselage_xsecs` (`FuselageXSecSuperEllipseModel`, `:512`):

| Field | Type | Required | Default | Notes |
|---|---|---|---|---|
| `xyz` | JSON `[x,y,z]` | yes | — | section centre, **metres** |
| `a` | Float | yes | — | **Y half-axis** (semi-width), m |
| `b` | Float | yes | — | **Z half-axis** (semi-height), m |
| `n` | Float | yes | — | exponent; `2` = ellipse |
| `sort_index` | Integer | yes | `0` | ordering along the body |
| `fuselage_id` | Integer FK → `fuselages.id` `ON DELETE CASCADE` | no | — | |

Schemas: `FuselageSchema` (`aeroplaneschema.py:755`) with `x_secs`
**`min_length=2`**; `FuselageXSecSuperEllipseSchema` (l.711) with all four fields
required, all metres except `n`. 🟢

## Main Flow

### F1 — Create a fuselage (`create_fuselage`, l.63) 🟢

1. Resolve the aeroplane by UUID (404 if absent).
2. Validate `FuselageSchema` — `x_secs` `min_length=2` (BR-F4).
3. A name already present on this aeroplane raises `ConflictError` → **409**
   (l.80-84). *`create_wing` raises `ValidationError` → 422 for the same
   condition (`wing_service.py:285-289`) — see the gap register.*
4. Persist the fuselage and its cross-sections in `sort_index` order.
5. Drive the component-tree auto-sync `sync_group_for_fuselage` (gh#108), via a
   lazy import.
6. Return the model; `get_db()` commits (ADR 0009).

### F2 — Update a fuselage (`update_fuselage`, l.103) 🟢

The old `FuselageModel` is **removed from the collection and a brand-new one
appended** (l.120-122) — a destructive replace, not a field merge.

🟡 **Consequence:** `step_path` and `solid_step_path` not present in the incoming
payload are lost, because the replacement row is built purely from the payload.
A caller who wants to keep the artefacts must echo them back.

### F3 — Read a fuselage (`get_fuselage`, l.137) 🟢

Resolve by aeroplane UUID + name; `NotFoundError` → 404 on a miss. The
cross-sections come back in `sort_index` order, so a consumer may loft them
without re-sorting.

### F4 — Delete a fuselage (`delete_fuselage`, l.160) 🟢

1. Resolve and delete; the ORM cascade removes `fuselage_xsecs`.
2. `delete_synced_nodes("fuselage:<name>")` removes the component-tree group
   (l.179-181, gh#108).

### F5 — Cross-section CRUD 🟢

`get_fuselage_cross_sections` (l.193) lists in `sort_index` order;
`delete_all_cross_sections` (l.219) empties the stack but keeps the fuselage
row; `get_cross_section` (l.244), `create_cross_section` (l.276),
`update_cross_section` (l.327) and `delete_cross_section` (l.364) address a
single station **by index**.

🟡 An out-of-range index yields **404** — INFERRED from the service's
`NotFoundError` usage pattern; the exact bound check was not read.

### F6 — The superellipse parameterisation 🟢

```
Shape law (cross-section plane, Y lateral, Z vertical):
    |y/a|^n + |z/b|^n = 1

Polar form actually evaluated:
    r(θ) = ( |cos θ / a|^n + |sin θ / b|^n )^(−1/n)            (slicing.py:585-586)

Derived:
    perimeter(a,b,n) = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ   (quad, limit=200)  (l.588-598)
    area(a,b,n)      = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)                      (l.600-602)
    polygon_area     = shoelace over a sampled outline                      (l.604-608)
```

`n = 2` is an ellipse (`area → π·a·b`); larger `n` approaches a rectangle.

### F7 — Axis convention (gh-706) 🟢

```
a  (Y half-axis, semi-width)  → ASB FuselageXSec.width
b  (Z half-axis, semi-height) → ASB FuselageXSec.height
```

(`app/schemas/aeroplaneschema.py:711-723`.) They are **half-axes, not
diameters** — no factor of two is applied anywhere in the conversion. A consumer
that doubles them inflates the body; one that swaps them rotates it 90°.

### F8 — Symmetry (gh-715) 🟢

`fuselages.symmetric` defaults to **`False`**, the opposite of
`wings.symmetric` (`True`). The main fuselage sits on the symmetry plane and
must not be mirrored. Paired sub-fuselages (landing-gear struts, wheel fairings,
engine cowlings) are stored **once** by OpenVSP and duplicated `y → −y` on the
fly by every downstream consumer — the ASB converter, the CAD builder and the
viewer (`aeroplanemodel.py:529-533`, `aeroplaneschema.py:762-773`).

The mirroring is therefore a **consumer contract**, not a stored second row:
this slice never materialises the mirrored geometry.

### F9 — STEP artefact pointers 🟢

| Column | Written by | Content | Served by |
|---|---|---|---|
| `step_path` | `openvsp-import`, gh-729 | per-geom **Surface** STEP | `GET .../fuselages/{name}/step` (`fuselages.py:198`) |
| `solid_step_path` | `openvsp_solid_sewing_service`, gh-731 | sewed/healed closed **Solid** | `GET .../fuselages/{name}/solid_step` (`fuselages.py:234`) |

Both are **relative** paths resolved against `settings.ARTIFACTS_BASE_DIR`
(default `/tmp/da3dalus_artifacts`, always `.resolve()`d by a field validator,
`app/core/config.py:24-32`). `solid_step_path` is `None` when sewing failed or
the fuselage was never VSP-imported.

This slice is a **reader** of both columns. Neither write path lives here.

## Alternative Flows

- **Duplicate name:** `ConflictError` → **409** (`fuselage_service.py:80-84`).
  🟢 **This path is correct and the wing path aligns to it** (`Q-FD-1`,
  maintainer-answered). The divergence was drift, not intent. Discriminator:
  **409** for a *create* conflicting with persisted state, **422** for
  *processing* an internally inconsistent configuration.
- **Fewer than two cross-sections:** rejected by `FuselageSchema`'s
  `min_length=2` → 422, before the service is reached. 🟢
- **Unknown aeroplane or fuselage name:** `NotFoundError` → 404 with the
  `not_found` envelope. 🟢
- **Out-of-range cross-section index:** 404. 🟡 INFERRED.
- **Update omitting `step_path`:** the pointer is silently cleared, because the
  row is replaced rather than merged. 🟡
- **Missing artefact on download:** `GET .../step` or `.../solid_step` with a
  `NULL` column → 404. 🟡 INFERRED from the column nullability and the download
  route shape.
- **`symmetric = true`:** no second row is written; every consumer is expected to
  mirror `y → −y` itself. 🟢
- **Delete with the component tree unavailable:** not observed. The wing-side
  equivalent uses a lazy import for cycle-breaking only, not a `try/except`, so a
  failure here would propagate. 🟡 INFERRED — contrast with `aeroplane-core`'s
  explicitly best-effort `_sync_aircraft_mass`.

## Dependencies

- **`aeroplane-core`** — every route resolves an aeroplane by UUID first;
  `fuselages` cascade-delete with the aeroplane. Create/update/delete call back
  into `component_tree_service` (gh#108) — a two-way dependency broken by lazy
  imports.
- **[`step-slicing/`](../step-slicing/design.md)** — the *producer* of the
  cross-section stack this slice persists. It returns a `FuselageSchema` that the
  caller then `PUT`s here; there is no direct call between them.
- **`openvsp-import`** — the sole writer of `step_path` (gh-729) and, through
  `openvsp_solid_sewing_service`, of `solid_step_path` (gh-731).
- **`cad-generation`** — consumer of `solid_step_path`.
- **`aero-analysis`** — consumer of the xsec stack as the ASB fuselage model.
- **`app/core/config.py`** — `ARTIFACTS_BASE_DIR` resolution for the download
  routes.
- **`cad_designer/aerosandbox/slicing.py`** — the home of the superellipse
  closed forms this slice parameterises (read-only reference, ADR 0002).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The superellipse is parameterised by **half-axes** mapped to ASB `width`/`height` | gh-706; `aeroplaneschema.py:711-723` | 🟢 |
| Everything is metres — no millimetre exception, and therefore no conversion helper | `data-dictionary.md` §Module: fuselage-design | 🟢 |
| `symmetric` defaults to `False`, opposite to wings, and mirroring is a consumer contract rather than a stored row | gh-715; `aeroplanemodel.py:529-533` | 🟢 |
| A fuselage is addressed by **name** under an aeroplane UUID, a cross-section by **index** | `fuselage_service.py:63, 244` | 🟢 |
| Cross-sections are ordered by `sort_index` and cascade-delete | `aeroplanemodel.py:512` | 🟢 |
| `update_fuselage` preserves import artefacts the client omits | `fuselage_service.py:120-122` | 🟢 (`Q-FD-7`) — the destructive replace is a confirmed defect and is fixed |
| Duplicate name → 409 on both paths | `fuselage_service.py:80-84`; `wing_service.py:285-289` aligns | 🟢 (`Q-FD-1`) |
| The STEP columns are **pointers only** — this slice reads them, never writes them | `code-analysis.md` §STEP vs superellipse | 🟢 |
| Artefact paths are stored relative and resolved against a `.resolve()`d base directory | `app/core/config.py:24-32` | 🟢 |
| The component-tree import is lazy, to break the service cycle | `fuselage_service.delete_fuselage:179-181` | 🟢 |

## Internal State

The slice is stateless between requests. Persistent state:

- `fuselages` — name, the `symmetric` flag and the two artefact pointers.
- `fuselage_xsecs` — the superellipse stack `(xyz, a, b, n, sort_index)` in
  metres.

Referenced but **not owned**: files under `ARTIFACTS_BASE_DIR`, written by
`openvsp-import` and the sewing service.

Never persisted: the mirrored copy implied by `symmetric = true`, and any
derived perimeter / area — both are computed by consumers on demand.

## Observability

- 4xx/5xx flow through the shared error envelope; `logger.exception` is emitted
  by the endpoint layer on 5xx. 🟢
- No slice-specific logging, metrics, traces or events were found. 🟢
- 🟢 **The silent data loss is removed at source** (`Q-FD-7`,
  maintainer-answered): `update_fuselage` **preserves** `step_path` /
  `solid_step_path` when the client omits them, instead of replacing the row and
  orphaning the files. No signal is needed for a loss that no longer occurs.
  This is the same defect class as issue **#1094** (`ComponentEditDialog`
  hard-codes `model_ref: null`, erasing the uploaded model on every edit) — an
  update that discards a field the client simply did not send.

## Risks and Gaps

- 🟢 **The `a`/`b` mapping is made correct by construction, not by assertion**
  (`Q-FD-3`, expert consensus endorsed by the maintainer). A bare runtime assert
  is the **wrong instrument**, because it can only compare `a`/`b` against
  something and the only meaningful something is the source geometry. Three
  measures instead, in priority order:
  1. **One conversion seam** — `superellipse_to_asb_xsec(a, b, n)` replaces the
     two independent `2.0 * a` conversions
     (`cad_designer/aerosandbox/slicing.py:1291-1300`,
     `app/converters/openvsp_fuselage_handler.py:215`), so the convention holds
     by construction.
  2. **At import time only**, per xsec: `2a ≤ 1.02·Y_extent(step)` and
     `2b ≤ 1.02·Z_extent(step)` catch the factor-2 error; `max_x(2a)/max_x(2b)`
     within 20 % of `Y_extent/Z_extent` catches the **swap** on any non-circular
     fuselage.
  3. Where there is no source, an aspect-ratio band `2a/2b ∈ [0.3, 3.0]` —
     outside it `severity="warning"`, **never an exception**: a 0.5 kg foamie
     with a genuinely 4:1 flat fuselage exists, and refusing to store it would
     be worse than the bug.

  **Why a swap is the failure mode that matters:** it rotates the body 90° while
  leaving volume and wetted area near-unchanged — *exactly* unchanged for a body
  of revolution — so `volume_ratio` / `area_ratio` (`Q-FD-4`) **cannot see it**,
  yet AeroBuildup reads width and height separately, so a swap produces
  confidently wrong side force and `C_nβ`.
- 🟢 **`update_fuselage` preserves import artefacts the client omits**
  (`Q-FD-7`), so `step_path` / `solid_step_path` are no longer silently dropped.
- 🟢 **Duplicate-name divergence resolved: 409 on both paths** (`Q-FD-1`).
- 🟡 **The CAD side cannot consume this slice's output *yet* — and the fix is
  scheduled.** `FuselageConfiguration` carries a literal
  `#TODO generate fuselage from XSecs` (`FuselageConfiguration.py:11`), so the
  parametric representation feeds ASB and the viewer but not the CAD
  construction pipeline. **`Q-VI-4 ③` schedules exactly that loft:** when
  `solid_status != ok`, the Creators loft an approximate solid from these stored
  superellipses — a body well-formed by construction, being a loft of simple
  closed curves.

  ⚠ **Do not read this as "the x-secs are secondary."** `Q-FD-8b` established, by
  code measurement, that **parametric fuselage authoring is already implemented**
  in both frontend and backend (`fuselage_service.py:63,103` accept a full
  `FuselageSchema` including `x_secs`; `PropertyForm.tsx:24,529-532,575` edits an
  x-sec by index via `useFuselage(...).updateXSec`). The cross-sections are a
  **first-class authoring surface**, and the dual representation is two **peer**
  paths into the model. What is missing is only the CAD generation *from* them,
  which needs
  `solid_step_path` instead.
- 🟡 **Out-of-range index behaviour is inferred, not read.** The 404 mapping
  follows the service's `NotFoundError` pattern but the bound check itself was
  not inspected.
- 🟡 **No documented bound on the number of cross-sections.** `min_length=2` is
  enforced; no maximum was found, so a pathological payload is limited only by
  request size.
- 🟡 **A tree-sync failure on delete appears to propagate**, unlike the
  explicitly best-effort mass sync in `aeroplane-core`. Whether a failing sync
  should block a fuselage delete is unstated.
