# cross-section-crud — Technical Design

> Use-case design, nested under the module [`wing-design`](../design.md).
> Focuses on HOW this use case is built, derived from the legacy code.
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full module REST contract: [`../contracts.md`](../contracts.md).

## Interface

### REST surface owned by this use case 🟢

Base: `/aeroplanes/{aeroplane_id}/wings` (`app/api/v2/endpoints/aeroplane/wings.py`).
`{aeroplane_id}` is the public **UUID**.

| Method | Path suffix | Operation | Status codes |
|---|---|---|---|
| GET | `` | `get_aeroplane_wings` — list wing names | 200 · 404 · 500 |
| PUT | `/{wing_name}` | `create_aeroplane_wing` (ASB geometry, stamps `design_model='asb'`) | 200/201 · 404 · 422 · 500 |
| POST | `/{wing_name}` | `update_aeroplane_wing` | 200 · 404 · 422 · 500 |
| GET | `/{wing_name}` | `get_aeroplane_wing` | 200 · 404 · 500 |
| DELETE | `/{wing_name}` | `delete_aeroplane_wing` | 200 · 404 · 500 |
| POST | `/{wing_name}/from-wingconfig` | `create_aeroplane_wing_from_wingconfig` (mm→m, `design_model='wc'`) | 201 · 404 · 422 · 500 |
| GET | `/{wing_name}/wingconfig` | `get_wing_as_wingconfig` (m→mm, `scale=1000.0`) | 200 · 404 · 500 |
| PUT | `/{wing_name}/wingconfig` | `put_wing_as_wingconfig` | 200 · 404 · 422 · 500 |
| GET | `/{wing_name}/cross_sections` | list all stations | 200 · 404 · 500 |
| DELETE | `/{wing_name}/cross_sections` | delete all stations | 200 · 404 · 500 |
| GET | `/{wing_name}/cross_sections/{i}` | read station *i* | 200 · 404 · 500 |
| POST | `/{wing_name}/cross_sections/{i}` | insert / create station *i* | 200/201 · 404 · **422 on terminal segment data** · 500 |
| PUT | `/{wing_name}/cross_sections/{i}` | update station *i* | 200 · 404 · **422 on terminal segment data** · 500 |
| DELETE | `/{wing_name}/cross_sections/{i}` | delete station *i* | 200 · 404 · 500 |
| GET | `/{wing_name}/cross_sections/{i}/spars` | list spars (metres) | 200 · 404 · 500 |
| POST | `/{wing_name}/cross_sections/{i}/spars` | create a spar (metres in, mm stored) | 201 · 404 · 422 · 500 |
| PUT | `/{wing_name}/cross_sections/{i}/spars/{spar_index}` | update a spar | 200 · 404 · 422 · 500 |
| DELETE | `/{wing_name}/cross_sections/{i}/spars/{spar_index}` | delete a spar | 200 · 404 · 500 |

### Service surface — `app/services/wing_service.py` 🟢

| Symbol | Signature | Returns | Note |
|---|---|---|---|
| `_MM_TO_M` | constant | `0.001` | l.43 |
| `_M_TO_MM` | constant | `1000.0` | l.46 |
| `_convert_spare_to_meters` | `(spare_dict) -> dict` | spar with the six dimensional fields × `0.001` | l.49-66; `spare_vector` untouched |
| `_convert_spare_to_mm` | `(spare_dict) -> dict` | spar with the six dimensional fields × `1000.0` | l.69-88 |
| `_assert_non_terminal_xsec_or_raise` | `(wing, index) -> None` | raises `ValidationError` | l.151-156 |
| `create_wing` | `(db, aeroplane_uuid, wing_name, payload)` | `WingModel` | raises `ValidationError` (→422) on a duplicate name, l.285-289; stamps `design_model='asb'`, l.341 |
| `create_wing_from_wing_configuration` | `(db, aeroplane_uuid, wing_name, config)` | `WingModel` | `scale=0.001` (mm→m), l.313; stamps `design_model='wc'`, l.292 |
| `get_wing_as_wingconfig` | `(db, aeroplane_uuid, wing_name)` | `WingConfiguration` dict | `wing_model_to_wing_config(wing, scale=1000.0)`, l.372 |
| `_sync_spares_for_xsec` | `(db, xsec, spares)` | `None` | writes solver metres back **× 1000** as mm, l.851 |
| `_recompute_spare_vectors` | `(wing)` | `None` | rebuilds a `WingConfiguration` at `scale=1.0`, l.854-873 |

### Converter surface — `app/converters/` 🟢

| Symbol | Purpose | Line |
|---|---|---|
| `model_schema_converters._build_segment_details` | builds segment details; **overwrites** the x-sec control surface with the TED-derived one (BR-W1) | l.960-995 |
| `model_schema_converters._merge_ted_with_control_surface` | merges a TED into the ASB `control_surface` projection | — |
| `model_schema_converters._station_dihedral` | resolves each station's dihedral from the segment airfoils (BR-7) | l.998-1015 |
| `model_schema_converters._scale_asb_wing_geometry_schema` | multiplies `xyz_le` and `chord` by `scale` | l.452-470 |
| `model_schema_converters.wing_model_to_wing_config` | model → `cad_designer` topology | — |
| `spare_origin_preservation.should_preserve_normal_spare` | the gh-1053 exemption predicate | l.43-59 |
| `spare_origin_preservation.scale_db_origin_to_config` | `factor = 0.001 × scale` | l.62-78 |

### Data model 🟢

`wings` (`WingModel`, `app/models/aeroplanemodel.py:279`) — `name`,
`symmetric` (default **`True`**), `design_model` (`'wc'` | `'asb'` | `NULL`),
`aeroplane_id` FK `ON DELETE CASCADE`. `x_secs` is ordered by
`WingXSecModel.sort_index`, cascade delete-orphan. The read-only `units`
property always reports `{geometry_length: "m", detail_length: "m", angle: "deg"}`
(l.297-303) — see 🔴 in *Risks and Gaps*.

`wing_xsecs` (`WingXSecModel`, l.214) — `xyz_le` (JSON `[x,y,z]`, **metres**),
`chord` (m), `twist` (deg), `dihedral` (deg, **nullable**, gh-951), `airfoil`
(`.dat` path or URL), `wing_id` FK, `sort_index` (default `0`). Read-through
properties delegating to `detail`: `x_sec_type`, `tip_type`,
`number_interpolation_points`, `spare_list`, `trailing_edge_device`,
`turbulator`, plus a computed `control_surface` projection (l.241-276).

`wing_xsec_details` (`WingXSecDetailModel`, l.99) — 1:1 side table
(`wing_xsec_id` **unique**) holding `x_sec_type` (`root`|`segment`|`tip`),
`tip_type` (`flat`|`round`), `number_interpolation_points`. Children: `spares`
(1:N, ordered by `sort_index`), `trailing_edge_device` (1:1), `turbulator`
(1:1) — all cascade delete-orphan.

`wing_xsec_spares` (`WingXSecSpareModel`, l.129) — ⚠ **all dimensional fields
are millimetres** (gh-402): `spare_support_dimension_width`,
`spare_support_dimension_height`, `spare_length`, `spare_start`, `spare_origin`.
`spare_position_factor` is a dimensionless 0–1 chord fraction; `spare_vector` is
a dimensionless unit direction. `spare_mode` ∈
`normal | follow | standard | standard_backward | orthogonal_backward`.

## Main Flow

### F1 — Create a wing from ASB geometry (`PUT /{wing_name}`) 🟢

1. Resolve the aeroplane by UUID (404 if absent).
2. Validate the payload against `AsbWingSchema`. The validator
   `validate_last_xsec_has_no_segment_details` (`aeroplaneschema.py:666-680`)
   rejects any segment field on the last x-section (→ 422), and `min_length=2`
   rejects a single-station wing.
3. Reject a duplicate wing name with `ValidationError` → **422**
   (`wing_service.py:285-289`).
4. `WingModel.from_dict` builds the stations. For
   `index == len(xsec_dicts) - 1` it **blanks all six segment fields**
   (`aeroplanemodel.py:489-490`) — the model-layer half of BR-5.
5. Stamp `design_model = 'asb'` (`wing_service.py:341`).
6. Create the matching component-tree group (`sync_group_for_wing`, gh#108).
7. Return; `get_db()` commits.

### F2 — Create a wing from a `WingConfiguration` (`POST /from-wingconfig`) 🟢

1. Resolve the aeroplane.
2. Convert the millimetre payload with `scale = 0.001`
   (`wing_service.create_wing_from_wing_configuration:313`): every `xyz_le`
   component and `chord` is divided by 1000; spar dimensional fields are stored
   **verbatim in mm** (BR-2), so they are *not* rescaled by this factor.
3. `_station_dihedral` (`model_schema_converters.py:998-1015`) assigns each
   station's airfoil and reads its dihedral:

   ```
   station i airfoil = segments[i].root_airfoil        for i < N
   station N airfoil = segments[-1].tip_airfoil        (terminal rib)
   dihedral          = airfoil.dihedral_as_rotation_in_degrees
   ```

4. Stamp `design_model = 'wc'` (`wing_service.py:292`) — the wing is now
   CAD-capable.
5. Return **201**.

### F3 — Read a wing back as a `WingConfiguration` (`GET /wingconfig`) 🟢

1. Resolve the wing.
2. `wing_model_to_wing_config(wing, scale=1000.0)`
   (`wing_service.get_wing_as_wingconfig:372`) — the mm world.
3. `_scale_asb_wing_geometry_schema` multiplies `xyz_le` and `chord` by `scale`
   (`model_schema_converters.py:452-470`).
4. Spar origins go through `scale_db_origin_to_config`
   (`spare_origin_preservation.py:62-78`):

   ```
   factor = 0.001 × scale
     scale = 1.0     → factor 0.001  → metres      (used by the recompute path)
     scale = 1000.0  → factor 1.0    → verbatim mm (used by the read path)
   ```

5. `_resolve_spare_vectors_and_origins` clears and recomputes every spar's
   origin/vector **unless** `should_preserve_normal_spare` exempts it
   (`spare_origin_preservation.py:43-59`):

   ```
   preserve  ⇔  spare_mode == "normal"
             ∧  spare_origin is a fully explicit 3-component vector
             ∧  spare_vector is present
   ```

6. Return the mm-world configuration.

### F4 — Station write with the terminal guard 🟢

1. Resolve the wing and the station index against `sort_index` ordering
   (404 when out of range).
2. `_assert_non_terminal_xsec_or_raise(wing, index)`
   (`wing_service.py:151-156`) raises `ValidationError` → **422** when the write
   carries segment-scoped data and `index` is the terminal station.
3. Apply the patch to `wing_xsecs` and, for segment fields, to the 1:1
   `wing_xsec_details` row (creating it on demand).
4. Return.

### F5 — Spar write and the unit boundary 🟢

1. Payload arrives in **metres**.
2. `_convert_spare_to_mm` (`wing_service.py:69-88`) multiplies
   `spare_support_dimension_width`, `spare_support_dimension_height`,
   `spare_length`, `spare_start` and every component of `spare_origin` by
   `_M_TO_MM = 1000.0`. `spare_vector` and `spare_position_factor` are left
   untouched.
3. Persist to `wing_xsec_spares` (mm).
4. Optionally `_recompute_spare_vectors` (F6).
5. On read, `_convert_spare_to_meters` (`:49-66`) applies
   `_MM_TO_M = 0.001` to the same six fields.

### F6 — Spar-vector recompute (`_recompute_spare_vectors`, l.854-873) 🟢

1. Rebuild a `WingConfiguration` from the wing at **`scale = 1.0`** — i.e. in
   metres, not the usual mm world.
2. Read back each segment's computed `spare_vector` and `spare_origin`.
3. Write the origin back **× 1000** as mm (`_sync_spares_for_xsec:851`).
4. On `ImportError` (aarch64 without CadQuery) or `FileNotFoundError` (missing
   airfoil `.dat`), log a warning and return — the stored values are left
   unchanged.

### F7 — ASB round-trip and the index offset (BR-W1) 🟢

AeroSandbox emits **N+1** x-secs for **N** segments, and `x_sec[i]`'s control
surface belongs to segment *i−1*. `_build_segment_details`
(`model_schema_converters.py:960-995`) therefore **overwrites** the x-sec-derived
control surface with the segment's own TED-derived one. Without the overwrite,
`_merge_ted_with_control_surface` resurrects a phantom TED on the next
round-trip.

## Alternative Flows

- **Unknown aeroplane / wing / station index:** `NotFoundError` → **404** with
  the `not_found` envelope.
- **Duplicate wing name:** aligns to `ConflictError` → **409**, matching
  `create_fuselage` (`Q-FD-1`, maintainer-answered). 🟢 Today
  `wing_service.py:285-289` raises `ValidationError` → 422; the change is
  client-visible and must land before TypeScript client generation
  (`Q-CC-11`).
- **Segment data on the terminal station:** rejected at whichever layer sees it
  first — schema (422), then model (silently blanked), then service (422).
- **Single-station wing:** `min_length=2` on `AsbWingSchema.x_secs` → **422**.
- **CadQuery unavailable during a spar recompute:** warning logged, request
  succeeds, spar vectors keep their previous values. 🟡 The caller receives no
  signal that the recompute was skipped.
- **Missing airfoil `.dat` during a recompute:** same degradation path
  (`FileNotFoundError`).
- **Legacy `dihedral = NULL`:** consumers fall back to the geometry-derived
  dihedral.
- **Legacy `design_model = NULL`:** the wing's authoring origin is unknown;
  CAD capability must be probed rather than assumed. 🟡

## Dependencies

- **`app/db/session.py` (`get_db`)** — owns the transaction; this use case never
  commits (ADR 0009).
- **`app/converters/model_schema_converters.py`** — the conversion hub shared
  with `fuselage-design`, `cad-generation`, `aero-analysis`, `avl-integration`
  and `openvsp-import`.
- **`app/converters/spare_origin_preservation.py`** — the mm↔config scale rule
  and the gh-1053 preservation predicate.
- **`cad_designer` topology (`WingConfiguration`, `WingSegment`, `Spare`,
  `Airfoil`)** — the millimetre world; **read-only** (ADR 0002).
- **`aeroplane-core` (`component_tree_service`)** — the wing group auto-sync
  (gh#108), reached by a lazy import to break the service cycle.
- **`airfoil-catalog`** — station `airfoil` values resolve to `.dat` files under
  `AIRFOILS_DIR`; a missing file degrades the recompute (F6).
- **`app/core/exceptions.py`** — the `ServiceException` hierarchy.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Segment data hangs off the inboard station in a 1:1 side table rather than on the station itself | `aeroplanemodel.py:99` + read-through properties `:241-276` | 🟢 |
| The terminal-station rule is enforced three times rather than once | `aeroplaneschema.py:666-680`, `aeroplanemodel.py:489-490`, `wing_service.py:151-156` | 🟢 |
| The model layer *blanks* terminal segment fields silently while the schema and service layers *raise* | `aeroplanemodel.py:489-490` vs the other two | 🟢 (the asymmetry itself is 🟡 deliberate) |
| Spar dimensions are stored in mm inside an otherwise-metre database, with conversion pushed to the service boundary | gh-402; `wing_service.py:43-88` | 🟢 |
| `spare_vector` is dimensionless and therefore never scaled at any boundary | `wing_service.py:49-88`; data-dictionary §`wing_xsec_spares` | 🟢 |
| Spar origins are cleared and recomputed by default, with an explicit opt-out for solver output | `spare_origin_preservation.py:43-59` (gh-1053 over gh-352/gh-362) | 🟢 |
| The terminal dihedral is persisted rather than derived | `aeroplanemodel.py:219-225` (gh-951) | 🟢 |
| Authoring origin is recorded on the row (`design_model`) rather than inferred from content | `wing_service.py:292, :341` | 🟢 |
| The geometry-kernel dependency is optional: its absence degrades a refinement, never the CRUD | `wing_service.py:854-873` (ADR 0017) | 🟢 |
| A duplicate name is a **conflict** (409) on both the wing and fuselage paths | `wing_service.py:285-289` aligns to `fuselage_service.py:80-84` | 🟢 (`Q-FD-1`) |

## Internal State

Stateless between requests. Persistent state:

- `wings` — identity, `symmetric`, `design_model`.
- `wing_xsecs` — the station geometry (`xyz_le`, `chord`, `twist`, `dihedral`,
  `airfoil`) and `sort_index` ordering.
- `wing_xsec_details` — the 1:1 segment side table.
- `wing_xsec_spares` — spar geometry, **in millimetres**.

Nothing is cached; `units` is a computed read-only property, and the ASB
`control_surface` projection on a station is computed from the TED
(`aeroplanemodel.py:241-276`), never stored twice.

## Observability

- `logger.warning` when `_recompute_spare_vectors` degrades on `ImportError` /
  `FileNotFoundError` (`wing_service.py:872`). 🟢
- `logger.exception` on 5xx via the global handlers; 4xx logged at INFO. 🟢
- No metrics, traces or structured events emitted by this use case. 🟢
- Geometry mutations must be fanned out through `invalidation_service`
  (`mark_ops_dirty`) so dependent operating points become `DIRTY`; any new
  geometry-mutating path has to be wired through it. 🟡 INFERRED as a
  requirement on new code from the cross-module note in `code-analysis.md`.

## Risks and Gaps

- 🔴 **The self-describing `units` block lies about storage.** `WingUnitsSchema`
  (`aeroplaneschema.py:510`) and `WingModel.units` (`aeroplanemodel.py:297-303`)
  declare `detail_length: "m"`, and `SpareDetailSchema` descriptions say "in
  meters", while `wing_xsec_spares` stores **mm**. A consumer reading `units`
  alone is misled about the storage unit. Is `units` meant to describe the wire
  format only?
- 🔴 **`servo` is a union by convention.**
  `WingXSecTrailingEdgeDeviceModel.servo` returns a `WingXSecTedServoModel` *or*
  an `int` index (`aeroplanemodel.py:183-187`). Which is canonical for new
  records is undocumented.
- 🔴 **`Servo` schema requires what the DB allows to be NULL.** All `Servo`
  fields are required `NonNegativeFloat` (`app/schemas/Servo.py:6-13`); all
  `wing_xsec_ted_servos` columns are nullable. A legacy row with a `NULL`
  dimension cannot be validated into the schema.
- 🔴 **Topology defaults diverge from DB defaults.**
  `positive/negative_deflection_deg` default to 25° in the topology layer but
  `NULL` in the DB; `hinge_type` `"top"` vs `NULL`;
  `trailing_edge_offset_factor` `1.0` vs `NULL`. Which layer supplies the
  effective default on a CAD build is not documented.
- 🟢 **Duplicate-name divergence resolved: 409 on both paths** (`Q-FD-1`).
- 🟢 **BR-6 gains a schema expression** (`Q-WD-5`): a root chord contradicting
  the previous segment's tip chord is rejected with a 422 naming that governing
  tip chord, or accepted with a `DesignWarning` — never silently discarded. The
  invariant is a property of the construction API (`add_segment` copies the
  previous tip), which `from_json_dict` bypasses; that is precisely why the
  check belongs in the schema layer, where JSON-described wings arrive.
- 🟡 **The recompute degradation is invisible to the caller.** A 200 response on
  an aarch64 host does not distinguish "vectors recomputed" from "recompute
  skipped". Per ADR 0012 this arguably warrants a design warning in the
  response body rather than a log line only.
- 🟢 **Known frozen bug, deliberately not fixed.**
  `cad_designer/.../WingConfiguration.py` contains a dead perpendicular-spare
  branch. The topology layer is frozen (ADR 0002); recorded here so later
  analysis does not rediscover it as new.
