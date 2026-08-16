# cross-section-crud

> Use-case specification, nested under the module [`wing-design`](../requirements.md).
> Focuses on WHAT this use case does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: wing-design
> (station/segment model, unit conversion, dihedral persistence),
> `_reversa_sdd/data-dictionary.md` §Module: wing-design.

## Overview

`cross-section-crud` is the **structural skeleton** of a lifting surface: a wing
is a list of stations (ribs), N stations describe N−1 segments, and every piece
of segment-scoped data hangs off the *inboard* station. This use case owns wing
and station CRUD, the terminal-station rule, the explicit terminal dihedral, the
`design_model` discriminator, and the **millimetre ↔ metre conversion boundary**
— the single most defect-prone seam in the codebase. 🟢

## Responsibilities

- CRUD for wings under an aeroplane, keyed by `wing_name`. 🟢
- CRUD for stations (`wing_xsecs`) addressed by **index**, ordered by
  `sort_index`. 🟢
- Own the 1:1 `wing_xsec_details` side table that carries all segment-scoped
  data (`x_sec_type`, `tip_type`, `number_interpolation_points`, `spare_list`,
  `trailing_edge_device`, `turbulator`). 🟢
- Reject every write of segment-scoped data to the terminal station, in three
  independent layers. 🟢
- Persist the terminal rib's dihedral explicitly, because it is unrecoverable
  from station positions. 🟢
- Stamp and preserve `design_model` (`'wc'` | `'asb'`) so downstream consumers
  know whether the wing is CAD-capable. 🟢
- Convert spar dimensions **m → mm** on write and **mm → m** on read, and
  nowhere else. 🟢
- Round-trip a wing through the `cad_designer` `WingConfiguration` (mm world),
  preserving explicitly solved `normal` spars. 🟢

**Explicitly NOT this use case's responsibility:** spar *sizing* and the layout
solver (→ [`../spar-sizing/`](../spar-sizing/requirements.md)), the role→axis
control decomposition (→ [`../control-surface-mixing/`](../control-surface-mixing/requirements.md)),
the turbulator optimiser (→ [`../turbulator-optimizer/`](../turbulator-optimizer/requirements.md)),
building the CAD solid (→ `cad-generation`), and the frozen topology classes
themselves (→ `cad-designer-topology`, read-only per ADR 0002).

## Business Rules

> IDs are inherited verbatim from [`../requirements.md`](../requirements.md) so
> module ↔ use-case traceability holds.

### Topology

- **BR-4 — N stations describe N−1 segments.** 🟢 *(module-level BR-4.)* A wing
  is a list of stations ordered by `sort_index`. All segment-scoped data —
  `spare_list`, `trailing_edge_device`, `turbulator`, `x_sec_type`, `tip_type`,
  `number_interpolation_points` — hangs off the **inboard** station of its
  segment, in the 1:1 `wing_xsec_details` side table
  (`app/models/aeroplanemodel.py:99`, read-through properties at `:241-276`).
- **BR-5 — The terminal station carries geometry only.** 🟢 *(module-level BR-5;
  this use case is its owner.)* Enforced in three independent layers:
  1. **schema** — `AsbWingSchema.validate_last_xsec_has_no_segment_details`
     (`app/schemas/aeroplaneschema.py:666-680`) raises when any segment field is
     present on the last x-section;
  2. **model** — `WingModel.from_dict` blanks all six segment fields when
     `index == len(xsec_dicts) - 1` (`app/models/aeroplanemodel.py:489-490`);
  3. **service** — `_assert_non_terminal_xsec_or_raise`
     (`app/services/wing_service.py:151-156`) raises `ValidationError` for any
     write targeting the terminal index.
  The triple enforcement is deliberate defence-in-depth: this is the rule that
  most often breaks round-trips.
- **BR-W2 — Minimum two stations.** 🟢 `AsbWingSchema.x_secs` carries
  `min_length=2` (`aeroplaneschema.py:645`) — a wing with fewer stations has no
  segment at all.
- **BR-6 — A segment's root chord is not independently settable.** 🟢 Chord
  continuity means a segment's root chord *is* the previous segment's tip chord;
  tapering is expressed by setting the tip chord. The schema cannot express this
  constraint, so the copilot's `get_wing_geometry` carries it as free-text
  `note`. 🟢 **The invariant is enforced in the Pydantic schema layer**
  (`Q-WD-5`, expert consensus endorsed by the maintainer): a supplied root chord
  that contradicts the previous segment's tip chord is **rejected with a 422
  naming the governing tip chord**, or accepted with a `DesignWarning` — but
  never silently discarded. The distinction that decides this: *within* a
  segment root and tip chords differ freely (that is taper); *between* segments
  the invariant holds **because construction goes through `add_segment`**, which
  copies the previous tip. `from_json_dict` bypasses that constructor, which is
  why a JSON-described wing needs the schema-level check.
- **BR-W1 — ASB index offset.** 🟢 AeroSandbox emits N+1 x-secs for N segments,
  and `x_sec[i]`'s control surface belongs to segment *i−1*.
  `_build_segment_details` therefore **overwrites** the x-sec-derived control
  surface with the segment's own TED-derived one; without the overwrite,
  `_merge_ted_with_control_surface` resurrects a phantom TED on round-trip
  (`app/converters/model_schema_converters.py:960-995`).
- **BR-7 — Terminal dihedral must be persisted explicitly (gh-951).** 🟢 The last
  rib's local-x rotation moves no outboard station, leaves no trace in `xyz_le`,
  and cannot be reconstructed from positions. It is stored in
  `wing_xsecs.dihedral` (`app/models/aeroplanemodel.py:219-225`); `NULL` on
  legacy rows means "derive from geometry". Write path is `_station_dihedral`
  (`app/converters/model_schema_converters.py:998-1015`):

  ```
  station i airfoil = segments[i].root_airfoil        for i < N
  station N airfoil = segments[-1].tip_airfoil        (terminal rib)
  dihedral          = airfoil.dihedral_as_rotation_in_degrees
  ```

- **BR-8 — A wing knows how it was authored.** 🟢 `wings.design_model` is `'wc'`
  when the wing was created from a `WingConfiguration` (CAD-capable) and `'asb'`
  when created from bare ASB geometry; `NULL` for legacy rows
  (`app/services/wing_service.py:292`, `:341`;
  `app/schemas/aeroplaneschema.py:652-655`).

### Units — the conversion boundary

- **BR-1 — The unit duality (ADR 0001).** 🟢 The DB and AeroSandbox speak
  **metres**; `WingConfig` and every `cad_designer` topology class speaks
  **millimetres**. Conversion happens **only** in `app/converters/` and the
  `_convert_spare_to_*` helpers of `wing_service`
  (`_MM_TO_M = 0.001` at `wing_service.py:43`, `_M_TO_MM = 1000.0` at `:46`).
  There is no type-level unit anywhere — the discipline is by convention.
- **BR-2 — The `wing_xsec_spares` exception (gh-402).** 🟢 All six dimensional
  spar columns — `spare_support_dimension_width`, `spare_support_dimension_height`,
  `spare_length`, `spare_start`, `spare_origin` (and `spare_position_factor`,
  which is a dimensionless 0–1 chord fraction) — are stored in **millimetres
  inside the metre database**. `spare_vector` is a **dimensionless unit
  direction vector**. The API contract is unchanged: every spar endpoint still
  delivers metres, via `_convert_spare_to_meters` (`wing_service.py:49-66`) on
  read and `_convert_spare_to_mm` (`:69-88`) on write.
- **BR-3 — Wing-local frame.** 🟢 `cad_designer` geometry uses a wing-local
  frame: origin at the root leading edge, z up.
- **BR-W3 — Spar geometry preservation (gh-1053).** 🟢
  `_resolve_spare_vectors_and_origins` normally **clears and recomputes** every
  spar's origin and vector on model→config conversion — this is the gh-352 /
  gh-362 unit-leak guard. `should_preserve_normal_spare`
  (`app/converters/spare_origin_preservation.py:43-59`) exempts a spar that is
  `spare_mode == "normal"` **and** carries a fully explicit 3-component
  `spare_origin` **and** a `spare_vector`. Everything else — `standard`,
  `follow`, `standard_backward`, `orthogonal_backward` — still goes through the
  recompute path. Without the exemption, a solver-produced front/rear spar
  couple collapses onto the default quarter-chord station.
- **BR-W4 — Recompute degrades silently on a missing platform dependency.** 🟢
  `_recompute_spare_vectors` (`app/services/wing_service.py:854-873`) rebuilds a
  `WingConfiguration` at `scale=1.0` (metres), reads back each segment's computed
  `spare_vector` / `spare_origin`, and writes the origin back **× 1000** as mm
  (`_sync_spares_for_xsec`, `:851`). On `ImportError` (aarch64 without CadQuery)
  or `FileNotFoundError` (missing airfoil `.dat`) it logs a warning and
  continues. 🟡 Consequence: on a degraded platform the stored vectors stay at
  their previous values with no signal to the caller.

### Conversion scale table 🟢

| Boundary | Direction | Factor | Code |
|---|---|---|---|
| API response ← DB | mm → m (spar `width`/`height`/`length`/`start`/`origin`; `spare_vector` untouched) | `0.001` | `wing_service._convert_spare_to_meters:49-66` |
| API request → DB | m → mm, same fields | `1000.0` | `wing_service._convert_spare_to_mm:69-88` |
| DB → `WingConfiguration` | `factor = 0.001 × scale` (`scale=1.0` → metres, `scale=1000.0` → verbatim mm) | derived | `spare_origin_preservation.scale_db_origin_to_config:62-78` |
| Wing geometry → config | `xyz_le` and `chord` multiplied by `scale` | `scale` | `model_schema_converters._scale_asb_wing_geometry_schema:452-470` |
| Config → DB (after a spar solve) | metres × 1000 | `1000` | `wing_service._sync_spares_for_xsec:851` |
| Read wing as `WingConfig` | `wing_model_to_wing_config(wing, scale=1000.0)` — mm world | `1000.0` | `wing_service.get_wing_as_wingconfig:372` |
| Create wing from `WingConfig` | mm → m | `0.001` | `wing_service.create_wing_from_wing_configuration:313` |

### Known contradictions

- 🟡 **`units` describes the wire format only, and that is correct**
  (`Q-WD-2`). `WingUnitsSchema` (`aeroplaneschema.py:510`) and `WingModel.units`
  (`aeroplanemodel.py:297-303`) declare `detail_length: "m"` while the DB stores
  **mm** (gh-402) — but the API delivers metres, so the wire contract is
  consistent. **No per-field storage-unit override is added:** ADR 0019 rule 4
  forbids a field that exists only because of an internal representation. The
  `SpareDetailSchema` descriptions are clarified to say they describe the wire
  format, before TypeScript client generation bakes them in (`Q-CC-11`).
  Derived from the ADR rather than decided directly, so INFERRED.
- 🟢 **`servo_data` is canonical for new records; `servo_index` is deprecated**
  (`Q-WD-3 ①`). The `Servo | int` union stays *readable* so existing rows
  resolve, but nothing new writes the bare index — a union by convention is a
  contract a client cannot type against.
- 🟢 **A `NULL` servo dimension is rejected on read, not defaulted**
  (`Q-WD-3 ②`). Every `Servo` field is a required `NonNegativeFloat`
  (`app/schemas/Servo.py:6-13`) while every `wing_xsec_ted_servos` column is
  nullable; failing loudly is correct, because substituting a plausible number
  for a missing servo dimension would put an invented value into a CAD build
  (ADR 0020). The error names the row and the field.
- 🟢 **Duplicate name answers 409 on both paths** (`Q-FD-1`,
  maintainer-answered). `create_wing`'s `ValidationError` → 422
  (`wing_service.py:285-289`) aligns to `ConflictError` → 409, matching
  `create_fuselage` (`fuselage_service.py:80-84`). The discriminator: **409**
  for a *create* conflicting with persisted state, **422** for *processing* an
  internally inconsistent configuration.

## Functional Requirements

> The `RF-xx` ids refine the module-level requirements in
> [`../requirements.md`](../requirements.md).

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | List a wing's names / read a wing by name under an aeroplane | Must | `GET /aeroplanes/{id}/wings` → 200 with the name list; `GET .../wings/{wing_name}` on an unknown name → 404 |
| RF-02 | Create a wing from an ASB geometry payload (`PUT /{wing_name}`), stamping `design_model = 'asb'` | Must | Round-trip read returns the same stations; the stored `design_model` is `'asb'` |
| RF-03 | Create a wing from a `WingConfiguration` payload, stamping `design_model = 'wc'` and converting mm→m with `scale = 0.001` | Must | `POST .../from-wingconfig` → 201; a payload chord of `250.0` mm is stored as `0.25` m |
| RF-04 | Read a wing back as a `WingConfiguration` in the millimetre world (`scale = 1000.0`) | Must | `GET .../wingconfig` returns mm geometry that re-imports byte-identically through `POST .../from-wingconfig` |
| RF-05 | Update / delete a wing, keeping the component-tree group in sync | Must | `DELETE .../{wing_name}` → 200; the `wing:<name>` component-tree group is removed |
| RF-06 | Station CRUD by index, ordered by `sort_index` | Must | `GET/POST/PUT/DELETE .../cross_sections/{i}` address the i-th station by `sort_index`; an out-of-range index → 404 |
| RF-06b | Bulk station reads and deletes | Should | `GET .../cross_sections` lists all; `DELETE .../cross_sections` removes all and leaves the wing row intact |
| RF-07 | Reject any write of segment-scoped data to the terminal station | Must | `PUT .../cross_sections/{last}` carrying a `spare_list` → 422 `validation_error`; the same payload on index 0 → 200 |
| RF-08 | Spar CRUD per station, delivering **metres** on the wire while storing **millimetres** | Must | POST a spar with `spare_length = 0.25`; the DB column reads `250.0`; the subsequent GET returns `0.25` |
| RF-09 | Preserve an explicit `normal` spar's origin and vector across a model→config round-trip | Must | A solver-produced front/rear couple keeps its distinct origins after a read-back; a `standard`-mode spar has its origin recomputed |
| RF-14 | Persist the terminal rib's dihedral explicitly | Must | Set a terminal dihedral of 5.0°, read the wing back: the value survives even though it is absent from `xyz_le` |
| RF-06c | Reject a wing with fewer than two stations | Must | A create payload with one x-section → 422 (`min_length=2`) |
| RF-08b | Degrade the spar-vector recompute to a warning when the geometry kernel is unavailable | Should | With `cadquery` unimportable, the spar write still returns 200 and logs a warning |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Correctness | Unit conversion happens only at the named boundaries; no ad-hoc scaling elsewhere | `wing_service.py:43-88`, `spare_origin_preservation.py:62-78`, `model_schema_converters.py:452-470` | 🟢 |
| Correctness | The terminal-station rule is enforced in three independent layers, so no single-layer bypass can persist segment data on the last rib | `aeroplaneschema.py:666-680`, `aeroplanemodel.py:489-490`, `wing_service.py:151-156` | 🟢 |
| Correctness | The x-sec-derived control surface is overwritten by the TED-derived one, preventing a phantom TED on round-trip | `model_schema_converters.py:960-995` | 🟢 |
| Correctness | The terminal dihedral is stored rather than derived, because the derivation is information-losing | `aeroplanemodel.py:219-225`, `model_schema_converters.py:998-1015` | 🟢 |
| Portability | The spar-vector recompute degrades to a warning on `ImportError` / `FileNotFoundError`, so an aarch64 host without CadQuery still serves wing CRUD | `wing_service.py:854-873` | 🟢 |
| Reliability | Transaction boundary is the request; the service never commits (ADR 0009) | `app/db/session.py:55-64` | 🟢 |
| Integrity | Station, detail, spar, TED, servo and turbulator rows all cascade `ON DELETE CASCADE` / `delete-orphan`, so deleting a wing leaves no orphan children | `aeroplanemodel.py:99, 129, 147, 190, 214` | 🟢 |

## Acceptance Criteria

```gherkin
Feature: Station and segment model

  Scenario: Segment data lives on the inboard station
    Given a wing with 3 stations
    When I POST a spar to cross_sections index 0
    Then the spar is stored on the wing_xsec_details row of station 0
    And it describes the segment between stations 0 and 1

  Scenario: Writing segment data to the terminal station is rejected
    Given a wing with 3 stations
    When I PUT cross_sections index 2 with a spare_list
    Then the response status is 422
    And the error code is "validation_error"
    And no wing_xsec_details row is created for station 2

  Scenario: A wing with fewer than two stations is rejected
    Given a create payload carrying exactly one x-section
    When I PUT /aeroplanes/{id}/wings/{wing_name}
    Then the response status is 422
    And the message names the x_secs min_length constraint

Feature: Station CRUD by index

  Scenario: Stations are addressed by sort_index order
    Given a wing whose stations were inserted out of order
    When I GET cross_sections index 1
    Then the station returned is the one with the second-lowest sort_index

  Scenario: An out-of-range index is a not-found
    Given a wing with 3 stations
    When I GET cross_sections index 7
    Then the response status is 404
    And the error code is "not_found"

Feature: Unit conversion boundary

  Scenario: Spars are metres on the wire, millimetres in storage
    Given a wing with one station
    When I POST a spar with spare_length 0.25 and spare_support_dimension_width 0.008
    Then the stored wing_xsec_spares row has spare_length 250.0 and width 8.0
    And GET of that spar returns spare_length 0.25

  Scenario: spare_vector is never scaled
    Given a spar whose spare_vector is [0.0, 0.0, 1.0]
    When the spar is written and read back
    Then spare_vector is still [0.0, 0.0, 1.0]

  Scenario: A solved normal spar keeps its explicit origin
    Given a spar with spare_mode "normal", a 3-component spare_origin and a spare_vector
    When the wing is converted to a WingConfiguration and back
    Then the spar's origin is unchanged
    And a spar with spare_mode "standard" has its origin recomputed

  Scenario: The recompute degrades rather than failing when CadQuery is absent
    Given an environment where importing cadquery raises ImportError
    When I write a spar that would normally trigger _recompute_spare_vectors
    Then the response status is 200
    And a warning is logged
    And the stored spare_vector is left at its previous value

Feature: WingConfiguration round-trip

  Scenario: A wing created from a WingConfiguration is CAD-capable
    Given a WingConfiguration payload in millimetres
    When I POST /aeroplanes/{id}/wings/{wing_name}/from-wingconfig
    Then the response status is 201
    And the stored wings.design_model is "wc"
    And a payload chord of 250.0 is stored as 0.25

  Scenario: A wing created from bare ASB geometry is marked asb
    Given an ASB geometry payload in metres
    When I PUT /aeroplanes/{id}/wings/{wing_name}
    Then the stored wings.design_model is "asb"

  Scenario: The round-trip does not resurrect a phantom trailing-edge device
    Given a wing whose segment 0 has no trailing-edge device
    When the wing is converted to ASB geometry and back
    Then segment 0 still has no trailing-edge device

Feature: Dihedral persistence

  Scenario: The terminal rib's dihedral survives a round-trip
    Given a wing whose last station has dihedral 5.0
    When I read the wing back
    Then the last station reports dihedral 5.0
    # It is not derivable from xyz_le — the terminal rotation moves no station

  Scenario: A legacy NULL dihedral falls back to geometry
    Given a wing whose last station has dihedral NULL
    When I read the wing back
    Then the reported dihedral is derived from the station geometry
    And no error is raised
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Wing + station CRUD (RF-01…RF-06) | Must | The critical path — `aero-analysis`, `cad-generation`, `mass-and-balance` and `openvsp-import` all read wings through this surface |
| Terminal-station enforcement (RF-07) | Must | Triple-enforced in the legacy code precisely because violations break every round-trip |
| Unit conversion at the named boundaries (RF-08) | Must | Wrong by 1000× when omitted; the single most common defect class in this codebase (gh-352, gh-362, gh-402) |
| `WingConfiguration` round-trip (RF-03/RF-04) | Must | The only bridge into the CAD stack; `design_model` gates CAD capability downstream |
| Explicit terminal dihedral (RF-14) | Must | Information-losing when omitted — unrecoverable from geometry (gh-951) |
| Spar preservation for explicit `normal` spars (RF-09) | Must | Without it the spar solver's output is destroyed on the very next read (gh-1053) |
| Minimum-two-stations guard (RF-06c) | Must | A one-station wing has no segment, so every downstream segment loop is undefined |
| Bulk station list / delete-all (RF-06b) | Should | Convenience over the indexed routes; the wing is fully editable without them |
| Graceful recompute degradation (RF-08b) | Should | Platform resilience for aarch64; the primary path is unaffected on a normal host |
| Clarifying the `SpareDetailSchema` descriptions | **Should** | 🟡 decided (`Q-WD-2`): `units` describes the wire format only and gains no storage override; the descriptions are clarified before client generation |
| Normalising the `servo` union to a single canonical form | **Should** | 🟢 decided (`Q-WD-3 ①`): `servo_data` canonical for new records, `servo_index` deprecated, union readable for existing rows |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/wing_service.py` | `create_wing`, `update_wing`, `get_wing`, `delete_wing`, `list_wing_names`, station CRUD, `_assert_non_terminal_xsec_or_raise` (l.151-156), `_convert_spare_to_meters` (l.49-66), `_convert_spare_to_mm` (l.69-88), `get_wing_as_wingconfig` (l.372), `create_wing_from_wing_configuration` (l.313), `_sync_spares_for_xsec` (l.851), `_recompute_spare_vectors` (l.854-873) | 🟢 |
| `app/api/v2/endpoints/aeroplane/wings.py` | wing routes, `cross_sections` routes, `spars` routes, `wingconfig` / `from-wingconfig` routes | 🟢 |
| `app/converters/model_schema_converters.py` | `_build_segment_details` (l.960-995), `_merge_ted_with_control_surface`, `_station_dihedral` (l.998-1015), `_scale_asb_wing_geometry_schema` (l.452-470), `wing_model_to_wing_config` | 🟢 |
| `app/converters/spare_origin_preservation.py` | `should_preserve_normal_spare` (l.43-59), `scale_db_origin_to_config` (l.62-78) | 🟢 |
| `app/models/aeroplanemodel.py` | `WingModel` (l.279), `WingModel.from_dict` (l.489-490), `WingXSecModel` (l.214), `WingXSecDetailModel` (l.99), `WingXSecSpareModel` (l.129), `units` property (l.297-303) | 🟢 |
| `app/schemas/aeroplaneschema.py` | `AsbWingSchema` (l.645), `validate_last_xsec_has_no_segment_details` (l.666-680), `AsbWingReadSchema` (l.685), `AsbWingGeometryWriteSchema` (l.695), `WingXSecSchema` (l.522), `WingXSecGeometryWriteSchema` (l.592), `WingUnitsSchema` (l.510), `SpareDetailSchema` (l.268) | 🟢 |
| `cad_designer/airplane/aircraft_topology/wing/WingConfiguration.py` | `WingConfiguration` (l.70) | 🟢 read-only (ADR 0002) |
