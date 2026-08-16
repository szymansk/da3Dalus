# superellipse-xsecs

> Use-case specification, nested under module [`fuselage-design`](../requirements.md).
> Focuses on WHAT this slice does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: fuselage-design,
> `_reversa_sdd/data-dictionary.md` §Module: fuselage-design.

## Overview

`superellipse-xsecs` owns the **parametric** half of the fuselage story: the
`fuselages` row, its ordered stack of superellipse cross-sections, and the CRUD
surface over both. It is the only description of a fuselage that ASB, the layout
tools and the viewer can consume — the STEP artefacts are precise but opaque, and
this slice merely *carries their pointers*. 🟢

**This slice is a first-class authoring surface, not a derived or fallback
view of an imported STEP body** (`Q-FD-8b`, corrected 2026-08-15, verified in
code): `create_fuselage` / `update_fuselage` (`fuselage_service.py:63, 103`)
accept a full `FuselageSchema` — including `x_secs` — and rebuild the model
via `FuselageModel.from_dict`, and `PropertyForm.tsx` (`:24, 529-532, 575`)
carries a `"fuselage"` mode that selects and edits a cross-section by index
through `useFuselage(...).updateXSec`. A user can design a fuselage entirely
from cross-section data, with no STEP file involved, and get a persisted,
analysable model. [`step-slicing/`](../step-slicing/requirements.md) is one
way to populate the stack; direct authoring through this slice's CRUD is the
other, equally primary, path. 🟢

## Responsibilities

- Own the superellipse shape law and its half-axis parameterisation. 🟢
- CRUD for fuselages, addressed by **name** under an aeroplane UUID. 🟢
- CRUD for superellipse cross-sections, addressed by **index**, ordered by
  `sort_index`. 🟢
- Carry the `symmetric` XZ-mirror flag and publish its `y → −y` consumer
  contract. 🟢
- Hold `step_path` / `solid_step_path` **as data** and serve them for download,
  resolving both against `ARTIFACTS_BASE_DIR`. 🟢
- Keep the component-tree group `fuselage:<name>` in sync on create, update and
  delete. 🟢

**Explicitly NOT this slice's responsibility:** producing the cross-sections from
a STEP solid (→ [`step-slicing/`](../step-slicing/requirements.md)); *writing*
`step_path` (→ `openvsp-import`, gh-729) or `solid_step_path`
(→ `openvsp_solid_sewing_service`, gh-731); building the CAD solid that consumes
them (→ `cad-generation`); the ASB fuselage drag model over the stack
(→ `aero-analysis`).

## Business Rules

| Rule | Derived from | Statement |
|---|---|---|
| **BR-F1** | module BR-F1 | The superellipse is defined by **half-axes, not diameters** 🟢 |
| **BR-F2** | module BR-F2 | All fuselage lengths are **metres** — no millimetre exception 🟢 |
| **BR-F3** | module BR-F3 | The polar form is what the code evaluates 🟢 |
| **BR-F4** | module BR-F4 | A fuselage needs at least two cross-sections 🟢 |
| **BR-F5** | module BR-F5 | `symmetric` defaults to `False`, the opposite of a wing 🟢 |
| **BR-F17** | module BR-F17 | A duplicate fuselage name is a `ConflictError` → **409** 🟢 |
| **BR-F18** | module BR-F18 | `update_fuselage` is a destructive replace, not a merge 🟢 |
| **BR-F19** | module BR-F19 | Create, update and delete all drive the component-tree auto-sync 🟢 |
| **BR-F20** | module BR-F20 | STEP paths are relative and resolved against `ARTIFACTS_BASE_DIR` 🟢 |
| **BR-F21** | module BR-F21 | The two representations have disjoint consumers 🟢 |

### BR-F1 — Half-axes, not diameters 🟢

In the cross-section plane (Y lateral, Z vertical):

```
|y/a|^n + |z/b|^n = 1
```

`a` is the **Y half-axis** (semi-width) and maps to ASB
`FuselageXSec.width`; `b` is the **Z half-axis** (semi-height) and maps to
`FuselageXSec.height` (gh-706, `app/schemas/aeroplaneschema.py:711-723`).
`n = 2` is an ellipse; larger `n` approaches a rectangle.

A consumer that treats `a` / `b` as full widths **halves the body**; a consumer
that swaps them **rotates it 90°**. Neither error raises — see the gap register.

### BR-F2 — Metres throughout 🟢

`xyz`, `a` and `b` are stored and served in **metres**; `n` is dimensionless.
Unlike `wing_xsec_spares` (gh-402), this slice has **no** millimetre exception,
so no conversion helper exists and none should be added.

### BR-F3 — The polar form 🟢

```
r(θ) = ( |cos θ / a|^n + |sin θ / b|^n )^(−1/n)
```

(`cad_designer/aerosandbox/slicing.py:585-586`.) Derived quantities, used by
[`step-slicing/`](../step-slicing/requirements.md) for the fit objective and
available here for area/perimeter reporting:

```
perimeter(a,b,n) = ∫₀^{2π} sqrt(r² + (dr/dθ)²) dθ   (scipy quad, limit=200)  (l.588-598)
area(a,b,n)      = 4·a·b·Γ(1 + 1/n)² / Γ(1 + 2/n)                            (l.600-602)
polygon_area     = shoelace formula over a sampled outline                    (l.604-608)
```

Sanity identity: at `n = 2`, `area` reduces to `π·a·b`. 🟡 INFERRED from the
closed form — `Γ(1.5)² / Γ(2) = (√π/2)² = π/4`, so `4·a·b·π/4 = π·a·b`.

### BR-F4 — Minimum two cross-sections 🟢

`FuselageSchema.x_secs` carries `min_length=2`
(`app/schemas/aeroplaneschema.py:755`) — a single station describes no body, and
every downstream loft assumes at least two.

### BR-F5 — `symmetric` defaults to `False` 🟢

The **opposite** of `wings.symmetric` (`True`). The main fuselage sits *on* the
symmetry plane and must not be mirrored. The flag exists for **paired
sub-fuselages** — landing-gear struts, wheel fairings, engine cowlings — that
OpenVSP stores **once** and that every downstream consumer (ASB converter, CAD
builder, viewer) duplicates on the fly with `y → −y`
(gh-715, `aeroplanemodel.py:529-533`, `aeroplaneschema.py:762-773`).

### BR-F17 — Duplicate name → 409 🟢

`create_fuselage` raises `ConflictError` → **409**
(`fuselage_service.py:80-84`). **This is the correct, confirmed contract**
(`Q-FD-1`, answered by the maintainer 2026-08-15): a *create* whose name
collides with an existing sibling is a conflict with persisted state, not an
unreadable payload. `create_wing`'s `ValidationError` → **422** for the same
situation (`wing_service.py:285-289`) was the outlier and is being aligned to
409, not the reverse.

### BR-F18 — Destructive replace today; decided to become a merge (`Q-FD-7`) 🟢

`update_fuselage` **currently** removes the old `FuselageModel` from the
collection and appends a brand-new one built purely from the payload
(`fuselage_service.py:120-122`), so any `step_path` / `solid_step_path`
absent from the incoming payload is lost. **Answered by the maintainer,
2026-08-15: yes, preserve import artefacts when the client omits them.** This
is the same defect class as issue #1094 (`ComponentEditDialog` hard-coding
`model_ref: null`, erasing the uploaded model on every edit) — a partial
update must not destroy what it does not mention. The re-implementation
carries `step_path` / `solid_step_path` forward from the previous row when
the payload omits them, rather than requiring the caller to echo them back.
Not yet implemented.

### BR-F19 — Component-tree auto-sync 🟢

Create and update drive `sync_group_for_fuselage`; delete calls
`delete_synced_nodes("fuselage:<name>")`
(`fuselage_service.delete_fuselage:179-181`, gh#108). The import is lazy, to
break the `fuselage_service ↔ component_tree_service` cycle.

### BR-F20 — Artefact path resolution 🟢

Both paths are **relative** and resolved against `settings.ARTIFACTS_BASE_DIR`
(default `/tmp/da3dalus_artifacts`, always `.resolve()`d by a field validator,
`app/core/config.py:24-32`). `solid_step_path` is `None` when sewing failed or
the fuselage was never VSP-imported.

### BR-F21 — Disjoint consumers 🟢

| Artefact | Produced by | Consumed by |
|---|---|---|
| `fuselage_xsecs` (a, b, n) | superellipse fit of a sliced STEP, or hand-authored | ASB drag/stability model, viewer outline, layout |
| `fuselages.step_path` | per-geom **Surface** STEP written at OpenVSP-import time (gh-729) | download; input to sewing |
| `fuselages.solid_step_path` | `openvsp_solid_sewing_service` sewing/healing `step_path` into a closed **Solid** (gh-731) | the CAD construction pipeline — battery-bay cuts, servo-mount unions, carbon-tube bores |

This slice **writes neither STEP column**; it only stores and serves them.

## Functional Requirements

| ID | Refines | Requirement | Priority | Acceptance criterion |
|----|---------|-------------|----------|----------------------|
| RF-01 | module RF-01 | List a fuselage's names under an aeroplane | Must | `GET /aeroplanes/{id}/fuselages` → 200; unknown aeroplane → 404 |
| RF-02 | module RF-02 | Create a fuselage with at least two superellipse cross-sections | Must | `PUT .../fuselages/{name}` → 201; a payload with one xsec → 422 |
| RF-03 | module RF-03 | Reject a duplicate fuselage name with **409** | Must | A second `PUT` with the same name → 409 `conflict` |
| RF-04 | module RF-04 | Read a fuselage with its cross-sections in `sort_index` order | Must | `GET .../fuselages/{name}` → 200 `FuselageSchema`; unknown name → 404 |
| RF-05 | module RF-05 | Update a fuselage (destructive replace) | Must | `POST .../fuselages/{name}` → 200; the stored xsec stack matches the payload exactly |
| RF-06 | module RF-06 | Delete a fuselage, cascading its cross-sections and removing the component-tree group | Must | `DELETE .../fuselages/{name}` → 200; the `fuselage:<name>` group node is gone |
| RF-07 | module RF-07 | Cross-section CRUD by index | Must | `GET/POST/PUT/DELETE .../cross_sections/{index}`; out-of-range → 404 |
| RF-08 | module RF-08 | Delete all cross-sections of a fuselage | Should | `DELETE .../cross_sections` → 200; the fuselage row survives |
| RF-09 | module RF-09 | Serve the Surface STEP artefact for download | Should | `GET .../fuselages/{name}/step` → 200 with the file; no `step_path` → 404 |
| RF-10 | module RF-10 | Serve the sewed Solid STEP artefact for download | Should | `GET .../fuselages/{name}/solid_step` → 200; `solid_step_path` null → 404 |
| RF-21 | module RF-21 | Carry the `symmetric` XZ-mirror flag with default `False` | Must | A fuselage created without `symmetric` reads back `false` |
| RF-X1 | new (slice-local) | Map `a → ASB width` and `b → ASB height` on conversion | Must | The produced `FuselageXSec` has `width == a` and `height == b`, not `2a` / `2b` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Cross-sections are always returned in `sort_index` order, so a consumer may loft them without re-sorting | `app/services/fuselage_service.py:193`; `app/models/aeroplanemodel.py:512` | 🟢 |
| Correctness | The 1:N relation cascades, so deleting a fuselage cannot leave orphan cross-sections | `app/models/aeroplanemodel.py:512` (`ON DELETE CASCADE`, `delete-orphan`) | 🟢 |
| Correctness | A fuselage cannot be persisted with fewer than two stations | `app/schemas/aeroplaneschema.py:755` (`min_length=2`) | 🟢 |
| Reliability | The transaction boundary is the request; the slice never commits | `app/db/session.py:55-64` (ADR 0009) | 🟢 |
| Reliability | The component-tree import is lazy, so the `fuselage_service ↔ component_tree_service` cycle never breaks module import | `fuselage_service.delete_fuselage:179-181` | 🟢 |
| Security | Artefact paths are stored **relative** and resolved against a `.resolve()`d `ARTIFACTS_BASE_DIR`, bounding where a download can read | `app/core/config.py:24-32` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Fuselage CRUD

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
    # 409 is the confirmed contract (Q-FD-1); create_wing is being aligned
    # to it, so no divergence survives to note

  Scenario: Reading an unknown fuselage
    Given an aeroplane with no fuselage named "Nose"
    When I GET /aeroplanes/{id}/fuselages/Nose
    Then the response status is 404
    And the error code is "not_found"

  Scenario: Deleting a fuselage removes its cross-sections and its tree group
    Given a fuselage "Body" with three cross-sections
    When I DELETE /aeroplanes/{id}/fuselages/Body
    Then the response status is 200
    And no fuselage_xsecs rows remain for it
    And the "fuselage:Body" component-tree node is gone

Feature: Destructive update

  Scenario: An update replaces the whole cross-section stack
    Given a fuselage "Body" with three cross-sections
    When I POST /aeroplanes/{id}/fuselages/Body with two cross-sections
    Then the response status is 200
    And exactly two cross-sections are stored

  Scenario: An update without step_path preserves the stored artefact pointer
    Given a fuselage "Body" whose step_path is "vsp/body.step"
    When I POST /aeroplanes/{id}/fuselages/Body without a step_path field
    Then the stored step_path is still "vsp/body.step"
    # Target contract per Q-FD-7 (2026-08-15): a partial update must not
    # destroy what it does not mention, same principle as issue #1094.
    # The legacy code clears the field instead (destructive replace);
    # that is the defect this scenario supersedes, not the target.

Feature: Cross-section CRUD

  Scenario: Reading a cross-section by index
    Given a fuselage with three cross-sections
    When I GET /aeroplanes/{id}/fuselages/Body/cross_sections/1
    Then the response status is 200
    And the payload carries xyz, a, b and n

  Scenario: An out-of-range index is not found
    Given a fuselage with three cross-sections
    When I GET /aeroplanes/{id}/fuselages/Body/cross_sections/7
    Then the response status is 404

  Scenario: Deleting all cross-sections keeps the fuselage
    Given a fuselage "Body" with three cross-sections
    When I DELETE /aeroplanes/{id}/fuselages/Body/cross_sections
    Then the response status is 200
    And the fuselage row still exists
    And it has no cross-sections

Feature: Superellipse parameterisation

  Scenario: The half-axes map to ASB width and height
    Given a cross-section with a 0.12 and b 0.08
    When it is converted to an ASB FuselageXSec
    Then width is 0.12
    And height is 0.08
    # They are half-axes, not diameters — no factor of two is applied

  Scenario: An exponent of two is an ellipse
    Given a cross-section with n 2.0, a 0.10 and b 0.05
    When the enclosed area is evaluated
    Then it equals pi times a times b

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

Feature: STEP artefact pointers

  Scenario: Downloading a present Surface STEP
    Given a fuselage whose step_path is "vsp/body.step" under ARTIFACTS_BASE_DIR
    When I GET /aeroplanes/{id}/fuselages/Body/step
    Then the response status is 200
    And the resolved path is inside ARTIFACTS_BASE_DIR

  Scenario: A missing Solid STEP is not found
    Given a fuselage whose solid_step_path is null
    When I GET /aeroplanes/{id}/fuselages/Body/solid_step
    Then the response status is 404
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Fuselage + cross-section CRUD (RF-01…RF-08) | Must | The critical path — `aero-analysis`, `cad-generation`, `mass-and-balance` and the viewer all read the xsec stack, and nothing else can author it by hand |
| Half-axis parameterisation and the ASB mapping (BR-F1 / RF-X1) | Must | A swapped or doubled `a`/`b` silently produces a plausible but wrong body; there is no runtime check anywhere |
| At least two cross-sections (BR-F4) | Must | Every downstream loft assumes ≥ 2; a one-station fuselage has no length |
| `symmetric` default `False` (BR-F5 / RF-21) | Must | The opposite of the wing default; getting it wrong duplicates the main fuselage onto itself |
| Duplicate name → 409 (BR-F17 / RF-03) | Must | Part of the observed wire contract, even though it diverges from the wing path |
| Cascade delete + tree-group removal (RF-06 / BR-F19) | Must | Without the cascade the xsec rows orphan; without the sync the BoM keeps a phantom group |
| Artefact download routes (RF-09 / RF-10) | Should | Convenience over data written by `openvsp-import`; the aircraft is analysable without them |
| Metres-only discipline (BR-F2) | Should | Enforced by absence — there is no conversion helper to get wrong, unlike `wing-design` |
| Perimeter / area reporting from `(a, b, n)` | Could | The closed forms exist in `slicing.py` but this slice exposes no endpoint for them |
| Merging rather than replacing on update (BR-F18) | Could | Would preserve `step_path` on a partial update — today's replace loses it |
| Runtime assertion of the `a`/`b` ↔ `width`/`height` mapping | **Won't** | 🟢 decided (`Q-FD-3`): a bare assertion is the **wrong instrument** — it can only compare `a`/`b` against the source geometry. Replaced by one `superellipse_to_asb_xsec(a, b, n)` conversion seam (correct by construction) plus import-time bounding-box checks |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/fuselage_service.py` | `list_fuselage_names` (l.45), `create_fuselage` (l.63, conflict at l.80-84), `update_fuselage` (l.103, replace at l.120-122), `get_fuselage` (l.137), `delete_fuselage` (l.160, tree-sync at l.179-181) | 🟢 |
| `app/services/fuselage_service.py` | `get_fuselage_cross_sections` (l.193), `delete_all_cross_sections` (l.219), `get_cross_section` (l.244), `create_cross_section` (l.276), `update_cross_section` (l.327), `delete_cross_section` (l.364) | 🟢 |
| `app/models/aeroplanemodel.py` | `FuselageModel` (l.526), `symmetric` rationale (l.529-533), `FuselageXSecSuperEllipseModel` (l.512) | 🟢 |
| `app/schemas/aeroplaneschema.py` | `FuselageXSecSuperEllipseSchema` (l.711), axis convention (l.711-723), `FuselageSchema` (l.755), symmetry note (l.762-773) | 🟢 |
| `app/api/v2/endpoints/aeroplane/fuselages.py` | fuselage + xsec routes; `/step` (l.198), `/solid_step` (l.234) | 🟢 |
| `app/core/config.py` | `ARTIFACTS_BASE_DIR` field validator (l.24-32) | 🟢 |
| `cad_designer/aerosandbox/slicing.py` | superellipse `r` / `perimeter` / `area` / `polygon_area` (l.585-608) — the shape law this slice parameterises | 🟢 |
| `cad_designer/.../fuselage/FuselageConfiguration.py` | `#TODO generate fuselage from XSecs` (l.11) — CAD generation *from* the x-secs is scheduled by `Q-VI-4 ③` (loft when `solid_status != ok`). Note this is the **CAD** gap only: parametric authoring of the x-secs is already implemented FE + BE (`Q-FD-8b`) | 🟡 |
