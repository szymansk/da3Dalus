# fuselage-design

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: fuselage-design,
> `_reversa_sdd/data-dictionary.md` §Module: fuselage-design.

## Overview

`fuselage-design` owns every non-lifting body — the main fuselage, but also
paired sub-fuselages such as landing-gear struts, wheel fairings and engine
cowlings. It maintains **two peer representations, not a primary and a
derived view**: the parametric superellipse cross-section stack
(`fuselage_xsecs`, the only description ASB and the layout tools can consume)
and the precise STEP artefacts (`step_path` surface, `solid_step_path` sewed
solid) that the CAD construction pipeline needs. 🟢 **A user reaches the
cross-section stack by either of two peer paths** (`Q-FD-8b`, corrected
2026-08-15): uploading a STEP and letting the slicing pipeline fit a
superellipse to each contour, **or authoring it directly** —
`create_fuselage` / `update_fuselage` accept `x_secs` with no STEP file
involved at all, and the frontend's `PropertyForm.tsx` `"fuselage"` mode edits
a cross-section by index through `useFuselage(...).updateXSec`. The STEP
slicing pipeline is one way to populate `fuselage_xsecs`, not the only one; it
is documented in full in [`step-slicing/`](step-slicing/requirements.md), and
direct authoring in [`superellipse-xsecs/`](superellipse-xsecs/requirements.md).

## Responsibilities

- CRUD for fuselages and their superellipse cross-sections, ordered by
  `sort_index`. 🟢
- Own the superellipse shape law `|y/a|^n + |z/b|^n = 1` and the axis convention
  `a → ASB width` (Y half-axis), `b → ASB height` (Z half-axis). 🟢
- Slice an uploaded STEP solid into cross-sections and fit a symmetric
  superellipse to each, reporting the reconstruction fidelity alongside the
  result. 🟢
- Hold the pointers to the two STEP artefacts and serve them for download. 🟢
- Carry the `symmetric` XZ-mirror flag whose default is the **opposite** of a
  wing's, and which downstream consumers act on by duplicating geometry with
  `y → −y`. 🟢
- Keep the component-tree group `fuselage:<name>` in sync on create, update and
  delete. 🟢

**Explicitly NOT this module's responsibility:** producing `step_path` (written
by `openvsp-import`, gh-729) or `solid_step_path` (written by
`openvsp_solid_sewing_service`, gh-731); building the CAD solid that consumes
them (→ `cad-generation`); running the aerodynamic model over the xsecs
(→ `aero-analysis`).

## Business Rules

### Shape and units

- **BR-F1 — The superellipse is defined by half-axes, not diameters.** 🟢
  In the cross-section plane (Y lateral, Z vertical):

  ```
  |y/a|^n + |z/b|^n = 1
  ```

  `a` is the **Y half-axis** (semi-width) and maps to ASB
  `FuselageXSec.width`; `b` is the **Z half-axis** (semi-height) and maps to
  `FuselageXSec.height` (gh-706, `app/schemas/aeroplaneschema.py:711-723`).
  `n = 2` is an ellipse; larger `n` approaches a rectangle.
- **BR-F2 — All fuselage lengths are metres.** 🟢 `xyz`, `a` and `b` are stored
  and served in metres; `n` is dimensionless. Unlike `wing_xsec_spares`, this
  module has **no** millimetre exception.
- **BR-F3 — The polar form is the one the code evaluates.** 🟢

  ```
  r(θ) = ( |cos θ / a|^n + |sin θ / b|^n )^(−1/n)
  ```

  (`cad_designer/aerosandbox/slicing.py:585-586`.) Derived quantities:

  ```
  perimeter(a,b,n) = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ   (scipy quad, limit=200)  (l.588-598)
  area(a,b,n)      = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)                            (l.600-602)
  polygon_area     = shoelace formula over the sliced outline                   (l.604-608)
  ```

- **BR-F4 — A fuselage needs at least two cross-sections.** 🟢
  `FuselageSchema.x_secs` carries `min_length=2` — a single station describes no
  body (`app/schemas/aeroplaneschema.py:755`).

### Symmetry

- **BR-F5 — `fuselages.symmetric` defaults to `False`** — the opposite of
  `wings.symmetric` (`True`). 🟢 The main fuselage sits *on* the symmetry plane
  and must not be mirrored. The flag exists for **paired sub-fuselages**
  (landing-gear struts, wheel fairings, engine cowlings) that OpenVSP stores
  once and that every downstream consumer (ASB converter, CAD builder, viewer)
  duplicates on the fly with `y → −y` (gh-715, `aeroplanemodel.py:529-533`,
  `aeroplaneschema.py:762-773`).

### Fitting

- **BR-F6 — The fit is symmetric by construction.** 🟢
  `fit_symmetric_superellipse` (`slicing.py:610-661`) forces the centre onto the
  Z axis (`center = [0, mean(z)]`), converts the shifted points to `(θ, r)` and
  **mirrors** them (`θ → −θ`, same `r`) before optimising. An asymmetric
  `fit_superellipse` exists at l.663 but is not the fuselage path.
- **BR-F7 — The objective blends radius error with perimeter error.** 🟢

  ```
  radius_loss = mean( (r_i − r_fit(θ_i))² )
  length_loss = (perimeter_fit − perimeter_actual)²
  objective   = radius_loss + 0.01 · length_loss
  ```

  Optimised with `scipy.optimize.minimize`, method **`L-BFGS-B`**,
  `x0 = [1.0, 1.0, initial_n = 2.0]`, bounds `a, b ∈ (1e-3, ∞)` and
  **`n ∈ [0.5, 8.0]`**. The `0.01` perimeter weight and the `n` bounds are the
  two magic numbers of the fuselage pipeline.

### Slicing

- **BR-F8 — Only `.step` / `.stp` uploads are accepted.** 🟢 The extension is
  validated before anything is written to disk
  (`app/services/fuselage_slice_service.py:28-116`).
- **BR-F9 — Path traversal is explicitly guarded (S2083).** 🟢 The uploaded
  filename is reduced to its **basename** and the resolved temp path is checked
  with `is_relative_to` before writing (l.50-64). The temp directory is always
  removed in a `finally` block.
- **BR-F10 — Non-finite fit results are sanitised to `null` (GH#301).** 🟢
  `NaN` / `Inf` in the response are replaced by `None` rather than emitted as
  invalid JSON.
- **BR-F11 — The response carries its own quality metric.** 🟢 `volume_ratio`
  and `area_ratio` compare the reconstructed superellipse loft against the
  original solid, so the caller can judge whether the simplification is
  acceptable. `original_tessellation_url` and `reconstructed_tessellation_url`
  are hard-coded `None` — STL export is not wired yet (l.113-115).
- **BR-F12 — The geometry kernel is optional.** 🟢
  `cad_designer.aerosandbox.slicing.slice_step_to_fuselage` is **lazy-imported**;
  when CadQuery is unavailable (e.g. `linux/aarch64`) the service raises
  `InternalError` instead of failing at module import (l.42-48, ADR 0017).
- **BR-F13 — Slicing is CPU-bound and slow.** 🟢 Documented as **5–30 s** of
  work for a typical fuselage.
- **BR-F14 — The outer contour is the one enclosing the longitudinal axis.** 🟢
  A slice plane can cut several disjoint loops (internal structure, wheel wells);
  `select_outer_contour` picks the cluster that encloses the axis
  (`slicing.py:207-267`).
- **BR-F15 — Stations are chosen adaptively.** 🟢 `adaptive_x_stations`
  (l.375) places more slices where a `_curvature_density` metric (l.347) is
  high, rather than uniformly. Point weighting along each contour is by arc
  length (l.116-152).
- **BR-F16 — Solids and shells are cut differently.** 🟢 A solid is cut with
  `Workplane.split(keepTop=True)`; a shell falls back to `BRepAlgoAPI_Section`
  (gh-727, l.476-489).

### Lifecycle

- **BR-F17 — A duplicate fuselage name is a `ConflictError` → 409.** 🟢
  (`fuselage_service.py:80-84`.) **This is the correct, confirmed contract**
  (`Q-FD-1`, answered by the maintainer 2026-08-15): a *create* whose name
  collides with an existing sibling is a conflict with persisted state, not an
  unreadable payload — the payload would succeed against a different
  aeroplane, and only the current database contents reject it. That is what
  409 means. `create_wing`'s `ValidationError → 422` for the identical
  situation (`wing_service.py:285-289`) was the outlier and is being aligned
  to `ConflictError → 409` (see `wing-design/contracts.md`), not the reverse.
  Both error messages must name the colliding item.
- **BR-F18 — `update_fuselage` is a destructive replace, not a merge.** 🟢
  The old `FuselageModel` is removed from the collection and a brand-new one
  appended (`fuselage_service.py:120-122`). 🟡 INFERRED consequence: any
  `step_path` / `solid_step_path` absent from the incoming payload is **lost**.
- **BR-F19 — Create, update and delete all drive the component-tree
  auto-sync.** 🟢 `sync_group_for_fuselage` on write,
  `delete_synced_nodes("fuselage:<name>")` on delete
  (`fuselage_service.delete_fuselage:179-181`, gh#108).
- **BR-F20 — STEP paths are relative and resolved against
  `ARTIFACTS_BASE_DIR`.** 🟢 Default `/tmp/da3dalus_artifacts`, always
  `.resolve()`d by a field validator (`app/core/config.py:24-32`).
  `solid_step_path` is `None` when sewing failed or the fuselage was not
  VSP-imported.
- **BR-F21 — The two representations have disjoint consumers.** 🟢

  | Artefact | Produced by | Consumed by |
  |---|---|---|
  | `fuselage_xsecs` (a, b, n) | superellipse fit of a sliced STEP, or hand-authored | ASB drag/stability model, viewer outline, layout |
  | `fuselages.step_path` | per-geom **Surface** STEP written at OpenVSP-import time (gh-729) | download; input to sewing |
  | `fuselages.solid_step_path` | `openvsp_solid_sewing_service` sewing/healing `step_path` into a closed **Solid** (gh-731) | the CAD construction pipeline — battery-bay cuts, servo-mount unions, carbon-tube bores |

- 🟢 **BR-F22 — The CAD-side `FuselageConfiguration` has no xsec constructor;
  the CAD solid must instead be lofted from the stored cross-sections.** It
  carries a literal `#TODO generate fuselage from XSecs` and its only factory,
  `from_step_file(step_file, scale=1.0, number_of_slices=100, name=None)`, is
  dead (below). **This is not the reason both representations exist** — that
  reading is corrected by `Q-FD-8b`: the xsecs are a first-class authoring
  surface in their own right, independent of `FuselageConfiguration`, not "the
  only parametric description because nothing else can build one." What
  `#TODO generate fuselage from XSecs` actually names is a missing CAD-side
  capability, and it is now **scheduled work, not an open question**: per
  `Q-VI-4 ③`, when the sewed solid's `solid_status != ok` (defective or
  absent), the Creator classes must **loft an approximate solid from the
  stored `fuselage_xsecs` superellipses** — a body well-formed by
  construction, being a loft of simple closed curves — and flag the
  substitution with a `notice`-severity `DesignWarning` (`P-WARN-0`), because
  a subsequent cut (battery bay, servo mount, carbon-tube bore) is then made
  against an approximated body rather than the exact imported geometry. That
  loft is the answer to `#TODO generate fuselage from XSecs`; it is not yet
  implemented.
- 🟢 **`from_step_file` is dead code, confirmed.** It assigns
  `analysis_specific_options = {dict(panel_resolution=24,
  panel_spacing="cosine")}` — a **set containing a dict**
  (`FuselageConfiguration.py:123-125`). A `dict` is unhashable, so the line
  raises `TypeError` on every execution; the path has therefore **never run**.
  Per `P-DEAD-0` rule 3 (anything with no retention argument is deleted by
  default) this is removed from the re-implementation. Because
  `FuselageConfiguration.py` sits inside the ADR 0002 freeze, the removal is
  **recorded here rather than executed** (`Q-FD-8`) — this module owns exactly
  one working STEP ingestion route, the one in
  [`step-slicing/`](step-slicing/requirements.md), not two.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List a fuselage's names under an aeroplane | Must | `GET /aeroplanes/{id}/fuselages` → 200; unknown aeroplane → 404 |
| RF-02 | Create a fuselage with at least two superellipse cross-sections | Must | `PUT .../fuselages/{name}` → 201; a payload with one xsec → 422 |
| RF-03 | Reject a duplicate fuselage name with **409** | Must | A second `PUT` with the same name → 409 `conflict` |
| RF-04 | Read a fuselage with its cross-sections in `sort_index` order | Must | `GET .../fuselages/{name}` → 200 `FuselageSchema`; unknown name → 404 |
| RF-05 | Update a fuselage | Must | `POST .../fuselages/{name}` → 200; the stored xsec stack matches the payload exactly |
| RF-06 | Delete a fuselage, cascading its cross-sections and removing the component-tree group | Must | `DELETE .../fuselages/{name}` → 200; the `fuselage:<name>` group node is gone |
| RF-07 | Cross-section CRUD by index | Must | `GET/POST/PUT/DELETE .../cross_sections/{index}`; out-of-range → 404 |
| RF-08 | Delete all cross-sections of a fuselage | Should | `DELETE .../cross_sections` → 200; the fuselage row survives |
| RF-09 | Serve the Surface STEP artefact for download | Should | `GET .../fuselages/{name}/step` → 200 with the file; no `step_path` → 404 |
| RF-10 | Serve the sewed Solid STEP artefact for download | Should | `GET .../fuselages/{name}/solid_step` → 200; `solid_step_path` null → 404 |
| RF-11 | Slice an uploaded STEP into superellipse cross-sections | Must | `POST /slice` with a `.step` file → 200 `FuselageSliceResponse` containing a `FuselageSchema` |
| RF-12 | Reject a non-STEP upload before touching the filesystem | Must | A `.stl` upload → 422; no temp file is created |
| RF-13 | Report reconstruction fidelity with every slice result | Must | The response carries `volume_ratio` and `area_ratio` |
| RF-14 | Sanitise non-finite fit values to `null` | Must | A degenerate slice yields `null`, never `NaN`, in the JSON body |
| RF-15 | Always remove the temp directory, including on failure | Must | After a slice that raises, no temp directory remains |
| RF-16 | Fail cleanly when the geometry kernel is absent | Must | Without CadQuery, `POST /slice` → 500 `internal_error`; the API still starts |
| RF-17 | Fit a symmetric superellipse per slice with the documented objective and bounds | Must | Given a known ellipse outline, the fit returns `n ≈ 2` and `(a, b)` within tolerance |
| RF-18 | Choose slice stations adaptively by curvature | Should | A body with a sharp shoulder receives more stations there than in the parallel mid-body |
| RF-19 | Select the contour enclosing the longitudinal axis when a plane cuts several loops | Should | A slice through a wheel well returns the outer skin, not the well |
| RF-20 | Handle both solid and shell STEP input | Should | A shell input falls back to `BRepAlgoAPI_Section` and still produces contours |
| RF-21 | Carry the `symmetric` XZ-mirror flag with default `False` | Must | A fuselage created without `symmetric` reads back `false` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Security | Uploaded filenames are reduced to their basename and the resolved temp path is verified with `is_relative_to` before any write (path-traversal guard, S2083) | `app/services/fuselage_slice_service.py:50-64` | 🟢 |
| Security | Only `.step` / `.stp` extensions are accepted | `fuselage_slice_service.py:28-116` | 🟢 |
| Reliability | The temp directory is removed in a `finally` block regardless of outcome | `fuselage_slice_service.py` (slice flow) | 🟢 |
| Correctness | Non-finite fit outputs are converted to `None` so the response is always valid JSON | `fuselage_slice_service.py` (GH#301) | 🟢 |
| Correctness | The response carries its own fidelity metrics rather than asserting the fit is good | `fuselage_slice_service.py:113-115` | 🟢 |
| Performance | Slicing is documented CPU-bound work of **5–30 s**; the caller must expect a long request | `fuselage_slice_service.py` docstring | 🟢 |
| Performance | Slice stations are placed adaptively by curvature density rather than uniformly | `cad_designer/aerosandbox/slicing.py:347, 375` | 🟢 |
| Portability | The geometry kernel is lazy-imported; its absence yields `InternalError` at call time, not an import-time crash | `fuselage_slice_service.py:42-48` (ADR 0017) | 🟢 |
| Reliability | The transaction boundary is the request; the module never commits | `app/db/session.py:55-64` (ADR 0009) | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Fuselage lifecycle

  Scenario: Creating a fuselage with a superellipse stack
    Given an aeroplane with no fuselage
    When I PUT /aeroplanes/{id}/fuselages/Body with three cross-sections
    Then the response status is 201
    And the stored cross-sections are ordered by sort_index
    And a component-tree group node with synced_from "fuselage:Body" exists

  Scenario: A single cross-section is rejected
    Given an aeroplane with no fuselage
    When I PUT /aeroplanes/{id}/fuselages/Body with one cross-section
    Then the response status is 422
    And the error code is "validation_error"

  Scenario: A duplicate fuselage name conflicts
    Given an aeroplane with a fuselage named "Body"
    When I PUT /aeroplanes/{id}/fuselages/Body again
    Then the response status is 409
    And the error code is "conflict"
    # Note: the equivalent wing case answers 422 — see the open gap

  Scenario: Deleting a fuselage removes its cross-sections and its tree group
    Given a fuselage "Body" with three cross-sections
    When I DELETE /aeroplanes/{id}/fuselages/Body
    Then the response status is 200
    And no fuselage_xsecs rows remain for it
    And the "fuselage:Body" component-tree node is gone

Feature: Symmetry flag

  Scenario: A fuselage is not mirrored by default
    Given a fuselage created without an explicit symmetric flag
    When I read it back
    Then symmetric is false
    # The main fuselage sits on the symmetry plane

  Scenario: A paired sub-fuselage is mirrored by consumers
    Given a fuselage with symmetric true representing a gear strut
    When a downstream consumer builds geometry from it
    Then a mirrored copy at y -> -y is produced

Feature: STEP slicing

  Scenario: A STEP solid becomes a superellipse stack
    Given a valid .step file describing a single closed fuselage solid
    When I POST /slice with number_of_slices 50 and points_per_slice 30
    Then the response status is 200
    And the payload contains a FuselageSchema with at least two cross-sections
    And volume_ratio and area_ratio are reported
    And no temp directory remains on disk

  Scenario: A non-STEP upload is rejected before any write
    Given a file named model.stl
    When I POST /slice with it
    Then the response status is 422
    And no temp file was created

  Scenario: A traversal filename cannot escape the temp directory
    Given a file named "../../etc/passwd.step"
    When I POST /slice with it
    Then the write target is the basename inside the temp directory
    And the request does not touch any path outside it

  Scenario: A degenerate slice yields null, not NaN
    Given a slice whose fit does not converge to finite values
    When the response is built
    Then the affected fields are null
    And the body is valid JSON

  Scenario: Slicing without a geometry kernel fails cleanly
    Given CadQuery is not installed
    When I POST /slice with a valid .step file
    Then the response status is 500
    And the error code is "internal_error"
    And the application is still serving other routes

Feature: Superellipse fitting

  Scenario: A circular outline fits an ellipse exponent
    Given a contour sampled from a circle of radius 0.1 m
    When fit_symmetric_superellipse runs
    Then n is approximately 2.0
    And a and b are both approximately 0.1

  Scenario: The exponent stays inside its bounds
    Given a contour that is very close to a rectangle
    When the fit runs
    Then n is at most 8.0
    And n is at least 0.5
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Fuselage + cross-section CRUD (RF-01…RF-08) | Must | The critical path — `aero-analysis`, `cad-generation`, `mass-and-balance` and the viewer all read the xsec stack |
| At least two cross-sections (BR-F4) | Must | A single station describes no body; every downstream loft assumes ≥ 2 |
| The superellipse definition and its axis convention (BR-F1) | Must | A swapped `a`/`b` silently rotates the whole body 90°; the mapping to ASB `width`/`height` has no runtime check |
| `symmetric` default `False` (BR-F5/RF-21) | Must | The opposite of the wing default; getting it wrong duplicates the main fuselage onto itself |
| STEP slicing pipeline (RF-11…RF-17) | Must | The only automated route from imported geometry to a parametric fuselage |
| Upload validation and the traversal guard (RF-12, BR-F9) | Must | The only route in the module that accepts a file from the client |
| Fidelity metrics on the slice response (RF-13) | Must | The response is a *simplification*; without `volume_ratio` / `area_ratio` the caller cannot judge it (ADR 0012 in spirit) |
| Temp-directory cleanup (RF-15) | Must | Slicing runs 5–30 s and can fail mid-way; leaked directories accumulate |
| Graceful failure without CadQuery (RF-16) | Must | The service must start on `linux/aarch64` (ADR 0017) |
| STEP artefact download routes (RF-09/RF-10) | Should | Convenience over data written by `openvsp-import`; the aircraft is analysable without them |
| Adaptive station placement (RF-18) | Should | Improves fidelity per slice; a uniform stack still produces a usable body |
| Outer-contour selection (RF-19) | Should | Only matters for bodies with internal loops |
| Shell fallback via `BRepAlgoAPI_Section` (RF-20) | Should | Solids are the normal input; shells are the gh-727 edge case |
| Merging rather than replacing on update (BR-F18) | Could | Would preserve `step_path` on a partial update — today's replace loses it |
| `FuselageConfiguration.from_step_file` | Won't | Confirmed dead (`Q-FD-8`) — the `TypeError`-raising line has never executed; not carried forward. The gap it stood in for is closed by BR-F22's scheduled xsec loft (`Q-VI-4 ③`), not by fixing this factory |
| Tessellation URLs on the slice response | Won't | Hard-coded `None`; STL export is not wired |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/fuselage_service.py` (403 l.) | `list_fuselage_names` (l.45), `create_fuselage` (l.63), `update_fuselage` (l.103), `get_fuselage` (l.137), `delete_fuselage` (l.160), `get_fuselage_cross_sections` (l.193), `delete_all_cross_sections` (l.219), `get_cross_section` (l.244), `create_cross_section` (l.276), `update_cross_section` (l.327), `delete_cross_section` (l.364) | 🟢 |
| `app/services/fuselage_slice_service.py` | `slice_step_file` (l.28-116) | 🟢 |
| `cad_designer/aerosandbox/slicing.py` (1339 l.) | `slice_step_to_fuselage`, `fit_symmetric_superellipse` (l.610-661), `fit_superellipse` (l.663), superellipse `r/perimeter/area` (l.585-608), `select_outer_contour` (l.207-267), `adaptive_x_stations` (l.375), `_curvature_density` (l.347), arc-length weighting (l.116-152), solid/shell cut (l.476-489) | 🟢 |
| `cad_designer/.../fuselage/FuselageConfiguration.py` | `from_step_file` (l.114-140) | 🟢 read-only (ADR 0002); confirmed dead, removal recorded not executed (`Q-FD-8`, `P-DEAD-0`) |
| `app/api/v2/endpoints/aeroplane/fuselages.py` | fuselage + xsec routes; `/step` (l.198), `/solid_step` (l.234) | 🟢 |
| `app/api/v2/endpoints/fuselage_slice.py` | `POST /slice` (l.18) | 🟢 |
| `app/models/aeroplanemodel.py` | `FuselageModel` (l.526), `FuselageXSecSuperEllipseModel` (l.512), `symmetric` rationale (l.529-533) | 🟢 |
| `app/schemas/aeroplaneschema.py` | `FuselageSchema` (l.755), `FuselageXSecSuperEllipseSchema` (l.711), axis convention (l.711-723), symmetry note (l.762-773) | 🟢 |
| `app/core/config.py` | `ARTIFACTS_BASE_DIR` validator (l.24-32) | 🟢 |
