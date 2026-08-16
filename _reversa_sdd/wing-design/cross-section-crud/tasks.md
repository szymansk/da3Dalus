# cross-section-crud — Implementation Tasks

> Executable sequence to re-implement this use case from the legacy behaviour.
> Every task cites the legacy file it was extracted from, a definition of done,
> and a confidence marker.
> Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] Persistence layer (SQLAlchemy 2.x) with the request-scoped `get_db()`
      session that **owns the transaction** (`app/db/session.py:55-64`,
      ADR 0009).
- [ ] `app/core/exceptions.py` hierarchy (`NotFoundError`, `ValidationError`,
      `ConflictError`, `InternalError`) and the global error-envelope handler.
- [ ] `aeroplanes` table and the aeroplane-by-UUID lookup (module
      `aeroplane-core`) — every route resolves an aeroplane first.
- [ ] `cad_designer` topology package available for the `WingConfiguration`
      round-trip (**read-only**, ADR 0002); the geometry kernel (`cadquery`) is
      **optional** and must be probed at import (ADR 0017).
- [ ] Airfoil `.dat` files reachable via `AIRFOILS_DIR` (module
      `airfoil-catalog`) — a missing file degrades the spar-vector recompute.
- [ ] `component_tree_service` group auto-sync hooks (module `aeroplane-core`,
      gh#108).

## Tasks

- [ ] **T-01 — `wings` table and `WingModel`.**
  Columns: `name`, `symmetric` (Boolean, default **`True`**), `design_model`
  (String, nullable — `'wc'` | `'asb'` | `NULL`), `aeroplane_id` FK →
  `aeroplanes.id` `ON DELETE CASCADE`. `x_secs` ordered by
  `WingXSecModel.sort_index` with `cascade="all, delete-orphan"`. Expose the
  read-only `units` property returning
  `{geometry_length: "m", detail_length: "m", angle: "deg"}`.
  - Legacy origin: `app/models/aeroplanemodel.py:279`, `:297-303`
  - Definition of done: deleting a wing removes every station, detail, spar,
    TED, servo and turbulator row in one flush.
  - Confidence: 🟢

- [ ] **T-02 — `wing_xsecs` table and `WingXSecModel`.**
  Columns: `xyz_le` (JSON `[x,y,z]`, **metres**), `chord` (Float, m), `twist`
  (Float, deg), `dihedral` (Float, **nullable**, deg — gh-951), `airfoil`
  (String, `.dat` path or URL), `wing_id` FK `ON DELETE CASCADE`, `sort_index`
  (Integer, default `0`). Add the read-through properties delegating to
  `detail`: `x_sec_type`, `tip_type`, `number_interpolation_points`,
  `spare_list`, `trailing_edge_device`, `turbulator`, plus the computed
  `control_surface` projection.
  - Legacy origin: `app/models/aeroplanemodel.py:214`, `:219-225`, `:241-276`
  - Definition of done: a station read returns segment data transparently from
    the 1:1 detail row without the caller knowing the side table exists.
  - Confidence: 🟢

- [ ] **T-03 — `wing_xsec_details` 1:1 side table.**
  `wing_xsec_id` FK `ON DELETE CASCADE` and **unique** (this is what enforces
  1:1), `x_sec_type` (`root`|`segment`|`tip`, nullable), `tip_type`
  (`flat`|`round`, nullable, only meaningful when `x_sec_type == 'tip'`),
  `number_interpolation_points` (Integer, nullable — loft sampling override,
  ≈201 typical for print quality). Children `spares` (1:N ordered by
  `sort_index`), `trailing_edge_device` (1:1), `turbulator` (1:1), all
  `delete-orphan`.
  - Legacy origin: `app/models/aeroplanemodel.py:99`
  - Definition of done: attempting to insert a second detail row for the same
    `wing_xsec_id` raises an `IntegrityError` at the database level.
  - Confidence: 🟢

- [ ] **T-04 — `wing_xsec_spares` table, in millimetres.**
  `wing_xsec_detail_id` FK `ON DELETE CASCADE`, `sort_index` (default `0`),
  `spare_support_dimension_width` (**mm**, required),
  `spare_support_dimension_height` (**mm**, required), `spare_position_factor`
  (dimensionless 0–1, nullable), `spare_length` (**mm**, nullable),
  `spare_start` (**mm**, nullable), `spare_mode`
  (`normal`|`follow`|`standard`|`standard_backward`|`orthogonal_backward`,
  nullable), `spare_vector` (JSON `[x,y,z]`, **dimensionless**, nullable),
  `spare_origin` (JSON `[x,y,z]`, **mm**, nullable).
  - Legacy origin: `app/models/aeroplanemodel.py:129`; gh-402
  - Definition of done: a comment or column-level docstring records the mm
    exception, and a test asserts a stored value is 1000× the wire value.
  - Confidence: 🟢

- [ ] **T-05 — Unit-conversion helpers.**
  `_MM_TO_M = 0.001`, `_M_TO_MM = 1000.0`; `_convert_spare_to_meters` and
  `_convert_spare_to_mm` scale exactly
  `spare_support_dimension_width`, `spare_support_dimension_height`,
  `spare_length`, `spare_start` and each component of `spare_origin` —
  and **must not touch** `spare_vector` or `spare_position_factor`.
  - Legacy origin: `app/services/wing_service.py:43`, `:46`, `:49-66`, `:69-88`
  - Definition of done: a property test round-trips `m → mm → m` to within
    floating-point tolerance, and asserts `spare_vector` is bit-identical.
  - Confidence: 🟢

- [ ] **T-06 — Terminal-station rule, layer 1 (schema).**
  `AsbWingSchema.x_secs` with `min_length=2`, plus
  `validate_last_xsec_has_no_segment_details` raising when **any** of the six
  segment fields (`x_sec_type`, `tip_type`, `number_interpolation_points`,
  `spare_list`, `trailing_edge_device`, `turbulator`) is present on the last
  x-section.
  - Legacy origin: `app/schemas/aeroplaneschema.py:645`, `:666-680`
  - Definition of done: one test per segment field asserting a 422; a wing with
    one station is also rejected.
  - Confidence: 🟢

- [ ] **T-07 — Terminal-station rule, layer 2 (model).**
  `WingModel.from_dict` blanks all six segment fields when
  `index == len(xsec_dicts) - 1`.
  - Legacy origin: `app/models/aeroplanemodel.py:489-490`
  - Definition of done: constructing a wing from a dict that carries terminal
    segment data yields a terminal station with all six fields empty, without
    raising.
  - Confidence: 🟢

- [ ] **T-08 — Terminal-station rule, layer 3 (service).**
  `_assert_non_terminal_xsec_or_raise(wing, index)` raising `ValidationError`
  (→ 422) for any write of segment-scoped data targeting the terminal index.
  - Legacy origin: `app/services/wing_service.py:151-156`
  - Definition of done: `PUT .../cross_sections/{last}` with a `spare_list`
    returns 422 `validation_error`; the same payload at index 0 returns 200.
  - Confidence: 🟢

- [ ] **T-09 — Wing CRUD.**
  `create_wing` (duplicate name → `ValidationError` → **422**), `update_wing`,
  `get_wing`, `delete_wing`, `list_wing_names`. `create_wing` stamps
  `design_model = 'asb'`.
  - Legacy origin: `app/services/wing_service.py:285-289`, `:341`
  - Definition of done: a duplicate name returns **409**, matching
    `create_fuselage` (`Q-FD-1`); a deleted wing leaves no child rows.
  - Confidence: 🟢

- [ ] **T-10 — Station CRUD by index.**
  Address stations by position in `sort_index` order; an out-of-range index
  raises `NotFoundError` → 404. Support the bulk `GET`/`DELETE` over
  `cross_sections` as well.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py` (`cross_sections`
    routes); `app/services/wing_service.py` station CRUD
  - Definition of done: stations inserted out of order are still addressed by
    `sort_index` position; index 7 on a 3-station wing → 404.
  - Confidence: 🟢

- [ ] **T-11 — Spar CRUD with the unit boundary.**
  `GET`/`POST` on `/cross_sections/{i}/spars` and `PUT`/`DELETE` on
  `/spars/{spar_index}`, applying T-05 in both directions.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py` spar routes;
    `wing_service.py:49-88`
  - Definition of done: POST `spare_length = 0.25` stores `250.0`; the
    subsequent GET returns `0.25`.
  - Confidence: 🟢

- [ ] **T-12 — `create_wing_from_wing_configuration` (mm → m).**
  Convert the incoming millimetre `WingConfiguration` with `scale = 0.001` and
  stamp `design_model = 'wc'`. Spar dimensional fields are stored **verbatim in
  mm** and are therefore not rescaled by this factor.
  - Legacy origin: `app/services/wing_service.py:313`, `:292`
  - Definition of done: a payload chord of `250.0` is stored as `0.25`, while a
    spar `spare_length` of `250.0` is stored as `250.0`.
  - Confidence: 🟢

- [ ] **T-13 — `get_wing_as_wingconfig` (m → mm).**
  `wing_model_to_wing_config(wing, scale=1000.0)`;
  `_scale_asb_wing_geometry_schema` multiplies `xyz_le` and `chord` by `scale`.
  - Legacy origin: `app/services/wing_service.py:372`;
    `app/converters/model_schema_converters.py:452-470`
  - Definition of done: the output of `GET .../wingconfig` re-imports
    byte-identically through `POST .../from-wingconfig`.
  - Confidence: 🟢

- [ ] **T-14 — `scale_db_origin_to_config`.**
  `factor = 0.001 × scale`, so `scale=1.0` yields metres (the recompute path)
  and `scale=1000.0` yields verbatim millimetres (the read path).
  - Legacy origin: `app/converters/spare_origin_preservation.py:62-78`
  - Definition of done: a table-driven test covers both scales against a known
    mm origin.
  - Confidence: 🟢

- [ ] **T-15 — `should_preserve_normal_spare` (gh-1053).**
  Exempt a spar from the clear-and-recompute path **only** when
  `spare_mode == "normal"` **and** `spare_origin` is a fully explicit
  3-component vector **and** `spare_vector` is present. All other modes
  (`standard`, `follow`, `standard_backward`, `orthogonal_backward`) still
  recompute.
  - Legacy origin: `app/converters/spare_origin_preservation.py:43-59`
  - Definition of done: a solver-produced front/rear couple keeps its distinct
    origins across a model→config→model round-trip; a `standard`-mode spar is
    recomputed. A regression test pins that dropping any one of the three
    conditions re-enables the recompute.
  - Confidence: 🟢

- [ ] **T-16 — `_recompute_spare_vectors` with graceful degradation.**
  Rebuild a `WingConfiguration` at **`scale = 1.0`** (metres), read back each
  segment's computed `spare_vector` / `spare_origin`, write the origin back
  **× 1000** as mm via `_sync_spares_for_xsec`. Catch `ImportError` and
  `FileNotFoundError`, log a warning, and continue.
  - Legacy origin: `app/services/wing_service.py:851`, `:854-873`
  - Definition of done: with `cadquery` patched to raise `ImportError`, the spar
    write still returns 200, a warning is logged, and the stored vectors are
    unchanged.
  - Confidence: 🟢

- [ ] **T-17 — `_station_dihedral` (gh-951).**
  Assign `station i airfoil = segments[i].root_airfoil` for `i < N` and
  `station N airfoil = segments[-1].tip_airfoil`, then persist
  `airfoil.dihedral_as_rotation_in_degrees` into `wing_xsecs.dihedral`.
  Treat `NULL` on read as "derive from geometry".
  - Legacy origin: `app/converters/model_schema_converters.py:998-1015`;
    `app/models/aeroplanemodel.py:219-225`
  - Definition of done: a terminal dihedral of 5.0° survives a full round-trip;
    a guard test asserts the value is **not** recoverable from `xyz_le` alone.
  - Confidence: 🟢

- [ ] **T-18 — `_build_segment_details` and the ASB index offset (BR-W1).**
  When converting N+1 ASB x-secs into N segments, **overwrite** the
  x-sec-derived control surface with the segment's own TED-derived one.
  - Legacy origin: `app/converters/model_schema_converters.py:960-995`
  - Definition of done: a wing whose segment 0 has no TED still has no TED after
    an ASB round-trip (guard against the phantom-TED regression that
    `_merge_ted_with_control_surface` otherwise causes).
  - Confidence: 🟢

- [ ] **T-19 — Component-tree group auto-sync.**
  On create/update call `sync_group_for_wing`; on delete call
  `delete_synced_nodes("wing:<name>")`. Reach `component_tree_service` through
  a **lazy import inside the function** to break the service cycle.
  - Legacy origin: `wing_service.create_wing:298-300` (gh#108)
  - Definition of done: creating a wing yields a component-tree group node with
    `synced_from = "wing:<name>"`; deleting the wing removes it.
  - Confidence: 🟢

- [ ] **T-20 — REST layer and the domain→HTTP mapping.**
  The 18 routes listed in [`design.md`](design.md) §Interface, with
  `NotFoundError → 404`, `ValidationError → 422`, `ConflictError → 409`,
  and a defensive `except Exception → 500` on every handler.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/wings.py`
  - Definition of done: contract tests assert every status code in the route
    table, including the 422 on a terminal-station segment write.
  - Confidence: 🟢

- [ ] **T-21 — Wire geometry mutations into `invalidation_service`.**
  Every route in this use case that changes geometry must call `mark_ops_dirty`
  so dependent operating points move to `DIRTY`.
  - Legacy origin: `app/services/invalidation_service.py:16-93` (cross-module
    note in `code-analysis.md`)
  - Definition of done: after a station or spar write, every non-`DIRTY` /
    non-`COMPUTING` operating point on the aeroplane is `DIRTY`.
  - Confidence: 🟡 — the fan-out is confirmed, but the exact set of wing routes
    that trigger it was not enumerated in the source analysis.

## Test Tasks

- [ ] **TT-01 — Happy path:** create a wing from ASB geometry, add a station,
      add a spar, read the wing back; all values round-trip (see
      [`requirements.md`](requirements.md) Acceptance Criteria).
- [ ] **TT-02 — Failure:** a segment-scoped write to the terminal station
      returns 422 `validation_error` at the schema layer *and* at the service
      layer (two separate tests — the layers must be independently verified).
- [ ] **TT-03 — Failure:** a wing payload with one x-section returns 422.
- [ ] **TT-04 — Unit boundary matrix:** for each of the six dimensional spar
      fields, assert the stored value is 1000× the wire value; assert
      `spare_vector` and `spare_position_factor` are unscaled.
- [ ] **TT-05 — `scale_db_origin_to_config`** at `scale=1.0` and `scale=1000.0`.
- [ ] **TT-06 — Preservation predicate:** a `normal` spar with a full origin and
      vector is preserved; dropping any one of the three conditions restores the
      recompute; `standard` / `follow` / `*_backward` always recompute.
- [ ] **TT-07 — Degradation guard:** patch the geometry-kernel import to raise
      `ImportError`, then `FileNotFoundError`; both leave the request at 200
      with a logged warning.
- [ ] **TT-08 — Dihedral round-trip:** a terminal dihedral of 5.0° survives; a
      companion test asserts the terminal rotation leaves `xyz_le` unchanged, so
      the test fails if the column is ever dropped in favour of derivation.
- [ ] **TT-09 — Phantom-TED guard:** an ASB round-trip on a wing whose segment 0
      has no TED must not create one.
- [ ] **TT-10 — Model-layer blanking:** `WingModel.from_dict` on a dict carrying
      terminal segment data yields empty terminal segment fields *without*
      raising.
- [ ] **TT-11 — Index addressing:** out-of-order `sort_index` values still
      resolve by position; an out-of-range index returns 404.
- [ ] **TT-12 — `design_model` stamping:** `PUT /{wing_name}` → `'asb'`;
      `POST /from-wingconfig` → `'wc'`; a legacy row keeps `NULL`.
- [ ] **TT-13 — Cascade:** deleting a wing removes stations, details, spars,
      TEDs, servos and turbulators, and removes the `wing:<name>` component-tree
      group.
- [ ] **TT-14 — Duplicate name:** returns **409**, the same as fuselage
      (`Q-FD-1`). The former 422 was drift, not a deliberate divergence.

## Data Migration Tasks

- [x] **TM-01 — `dihedral` backfill: not needed.** 🟢 **Measured 2026-08-15**
      (`Q-WD-7 ③`): 381 of 414 stations carry `dihedral IS NULL`, of which 73 are
      terminal ribs — but **none of those wings stores a non-zero dihedral
      anywhere**, so deriving the terminal value from geometry yields exactly
      what persistence would have. Nothing is unrecoverable in the current data.
      The consumer fallback is sufficient; re-run the check if data is imported
      from elsewhere.
- [ ] **TM-02 — Backfill `wings.design_model` for legacy rows.** `NULL` means
      "authoring origin unknown", which leaves CAD capability un-gated. Decide
      whether to infer `'wc'` from the presence of spar/TED data or leave the
      column tri-state. 🟡
- [ ] **TM-03 — Verify the mm invariant on `wing_xsec_spares`.** Any pre-gh-402
      rows still holding metres would be 1000× too small. Run a magnitude sanity
      check (a `spare_length` below ~1.0 is almost certainly metres) before
      enabling the new read path. 🟡

## Suggested Order

1. **T-01 → T-04** first: the four tables are the foundation. T-03's unique
   constraint is what makes the 1:1 detail relation real, and T-04 must land
   with the mm decision documented or every later task inherits ambiguity.
2. **T-05** immediately after: the conversion helpers are used by T-11, T-12,
   T-13, T-14 and T-16, and are the cheapest thing to get exhaustively tested.
3. **T-06 → T-08** next, and in that order: the three enforcement layers should
   be built and tested independently so a later refactor cannot silently drop
   one. T-07 must not raise — its contract is *blank silently*.
4. **T-09 → T-11**: CRUD on top of the model. T-11 blocks on T-05.
5. **T-12 → T-15**: the `WingConfiguration` bridge. T-15 blocks on T-14, and
   both block on the `cad_designer` topology being importable.
6. **T-16 → T-18**: the converter subtleties. T-16 blocks on T-15 (preservation
   must exist before the recompute is allowed to run), and T-17/T-18 are
   independent of each other.
7. **T-19** after `aeroplane-core`'s component-tree service exists
   (bidirectional dependency, broken by lazy imports).
8. **T-20** and **T-21** last — the REST layer is thin and only wires what is
   already tested; the invalidation fan-out needs the routes to exist.

## Pending Gaps (🔴)

- **The `units` block contradicts storage.** `WingUnitsSchema` /
  `WingModel.units` declare `detail_length: "m"` while `wing_xsec_spares` stores
  mm. Should `units` be documented as wire-format-only, or should it gain a
  per-field storage annotation?
- **`servo` is a union by convention.** Is `WingXSecTedServoModel` or the `int`
  index canonical for new records
  (`aeroplanemodel.py:183-187`)?
- **`Servo` requires fields the DB allows to be NULL.** How should a legacy row
  with a `NULL` dimension be surfaced — rejected, defaulted, or made optional in
  the schema?
- **Topology vs DB default divergence.** Which layer supplies the effective
  default for `positive/negative_deflection_deg` (25° vs `NULL`), `hinge_type`
  (`"top"` vs `NULL`) and `trailing_edge_offset_factor` (`1.0` vs `NULL`) on a
  CAD build?
- **Duplicate-name status code divergence.** Wing → 422
  (`wing_service.py:285-289`), fuselage → 409 (`fuselage_service.py:80-84`).
  Which is correct, and should they be unified?
- **BR-6 is unenforced.** A segment's root chord is not independently settable,
  but nothing in the schema expresses it — a client write silently rewrites the
  previous segment's tip chord. Should the schema reject it, or is the free-text
  `note` the intended level of protection?
- **Recompute degradation is silent to the caller.** Per ADR 0012 (design
  warnings, not silent fallbacks), should a skipped `_recompute_spare_vectors`
  surface as a warning in the response body rather than a log line only?
- **TM-01 is undecidable for terminal ribs.** The pre-gh-951 terminal dihedral is
  genuinely unrecoverable — is a manual re-entry pass expected, or is `NULL`
  acceptable indefinitely?
