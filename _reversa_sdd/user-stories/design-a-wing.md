# Designing a Wing

> **Personas:** RC/UAV designer · Hobbyist · AI-copilot user · MCP-agent client
> **Modules:** `wing-design` (+ `cross-section-crud`, `control-surface-mixing`, `turbulator-optimizer` slices; `ai-copilot` for the copilot story; `mcp-server` for the agent story)
> **Primary surface:** `/aeroplanes/{aeroplane_id}/wings/...` (REST v2, mounted at the application root — there is no `/api/v2` segment)

## Context

A wing is the central lifting-surface object in da3Dalus — main wing, tailplane, fin, canard and winglet are all rows in the same `wings` table, distinguished only by name and station geometry. Designing a wing means describing its stations (ribs) with an airfoil at each, and — for a buildable aircraft — layering on the segment-scoped structure (control surfaces, turbulators) that a real build needs. This flow covers wing creation in both the AeroSandbox-native metre world and the CAD-capable `WingConfiguration` millimetre world, station CRUD under the terminal-station rule, gh-772 control-surface mixing, turbulator setup, and the two non-human entry points into the same surface — the AI copilot and an MCP-agent client — each of which reaches a materially different, and materially smaller, subset of the underlying REST contract. Spar CRUD and the spar-plan solver are a separate flow — see `size-and-place-spars.md`.

## US-WING-01 — Create a wing from raw ASB geometry

**As an** RC/UAV designer, **I want** to define a wing directly as a list of AeroSandbox cross-sections (leading-edge point, chord, twist, airfoil), **so that** I can get a wing into the database and run VLM/AeroBuildup analysis on it without first building a CAD-capable model.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| PUT | `/aeroplanes/{aeroplane_id}/wings/{wing_name}` | create the wing from an `AsbWingSchema` payload |
| GET | `/aeroplanes/{aeroplane_id}/wings/{wing_name}` | read it back (`AsbWingReadSchema`) |
| GET | `/aeroplanes/{aeroplane_id}/wings` | list wing names on the aeroplane |

**Acceptance criteria**

- **AC-1 — A valid two-or-more-station wing is created**
  - **Given** the aeroplane exists and a payload of ≥2 `x_secs`, each with `xyz_le` (metres), `chord` (metres), `twist` (degrees) and `airfoil` (a `.dat` path or URL)
  - **When** I `PUT /aeroplanes/{aeroplane_id}/wings/{wing_name}`
  - **Then** the response is **201**, the wing is stored with `design_model = "asb"`, a `wing:<name>` component-tree group is created (gh#108), and a follow-up `GET` returns the same stations.
- **AC-2 — Segment data on the terminal station is rejected**
  - **Given** the same payload but the **last** `x_sec` carries a segment-scoped field (`spare_list`, `trailing_edge_device`, `turbulator`, `x_sec_type`, `tip_type`, or `number_interpolation_points`)
  - **When** I `PUT`
  - **Then** the response is **422** `validation_error` (`AsbWingSchema.validate_last_xsec_has_no_segment_details`) — the terminal station may carry geometry only.
- **AC-3 — A duplicate wing name is a validation error, not a conflict**
  - **Given** a wing named `main_wing` already exists on the aeroplane
  - **When** I `PUT` the same name again
  - **Then** the response is **422** `validation_error` (`wing_service.py:285-289`) — note this diverges from `create_fuselage`, which raises `ConflictError` → **409** for the identical situation; whether that divergence is intentional is unconfirmed.
- **AC-4 — A single-station wing is rejected**
  - **Given** a payload with only one `x_sec`
  - **When** I `PUT`
  - **Then** the response is **422** (`AsbWingSchema.x_secs` carries `min_length=2`).

**Confidence:** 🟢 CONFIRMED

## US-WING-02 — Bridge a wing into the CAD-capable millimetre world

**As an** RC/UAV designer, **I want** to author or re-read a wing's geometry as a `WingConfiguration` in millimetres, **so that** the same design can later be lofted into a real CAD solid by `cad-generation`.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/from-wingconfig` | create a wing from a `WingConfiguration` (mm) payload |
| GET | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/wingconfig` | read the wing back as a `WingConfiguration` (mm) |
| PUT | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/wingconfig` | overwrite the wing from a `WingConfiguration` (mm) payload |

**Acceptance criteria**

- **AC-1 — Millimetre payload converts to metre storage at the documented boundary**
  - **Given** a `WingConfiguration` payload with a 250 mm root chord
  - **When** I `POST /wings/{wing_name}/from-wingconfig`
  - **Then** the response is **201**, `design_model` is stamped `"wc"`, the stored `wing_xsecs.chord` is `0.25` m (`scale = 0.001`), and each station's `airfoil` and `dihedral` are resolved from the segment root/tip airfoils (BR-7: `station i airfoil = segments[i].root_airfoil`, terminal station = `segments[-1].tip_airfoil`).
- **AC-2 — The millimetre round trip is faithful, with an explicit spar exemption**
  - **Given** the wing created in AC-1, including one spar in `spare_mode = "normal"` with a full 3-component `spare_origin` and `spare_vector`
  - **When** I `GET /wings/{wing_name}/wingconfig`
  - **Then** the response is **200** with the chord returned as `250` (mm again, `scale = 1000.0`), and that one spar's origin/vector survive unchanged (gh-1053 `should_preserve_normal_spare` exemption) while any `standard`-mode spar on the same wing has its origin recomputed instead.
- **AC-3 — Unknown aeroplane or wing**
  - **Given** an aeroplane UUID or wing name that does not exist
  - **When** I `GET /wings/{wing_name}/wingconfig`
  - **Then** the response is **404** `not_found`.

**Confidence:** 🟢 CONFIRMED

## US-WING-03 — Manage stations and respect the terminal-station rule

**As an** RC/UAV designer, **I want** to insert, update and delete individual stations (cross-sections) on an existing wing, **so that** I can refine taper, sweep and dihedral segment-by-segment without recreating the whole wing.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET / DELETE | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections` | list / delete all stations |
| GET / POST / PUT / DELETE | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/cross_sections/{i}` | CRUD one station by index |

**Acceptance criteria**

- **AC-1 — Segment data hangs off the inboard station**
  - **Given** a 3-station wing (stations 0, 1, 2)
  - **When** I `POST cross_sections/0` with a `spare_list`
  - **Then** the response is **201** and the spar data is written to station 0's `wing_xsec_details` row, describing the segment between stations 0 and 1.
- **AC-2 — Writing segment data to the terminal station is rejected**
  - **Given** the same 3-station wing
  - **When** I `PUT cross_sections/2` (the last index) with any segment-scoped field
  - **Then** the response is **422** `validation_error` (`_assert_non_terminal_xsec_or_raise`, `wing_service.py:151-156`) — enforced independently at the schema, model and service layers (BR-5).
- **AC-3 — Delete all stations**
  - **Given** the same wing
  - **When** I `DELETE cross_sections` (no index)
  - **Then** the response is **200** and every station is removed.
- **AC-4 — Out-of-range index**
  - **Given** a wing with 3 stations (indices 0–2)
  - **When** I `GET`, `PUT` or `DELETE cross_sections/5`
  - **Then** the response is **404** `not_found`.

**Confidence:** 🟢 CONFIRMED

## US-WING-04 — Configure a dual-role control surface with gh-772 mixing

**As an** RC/UAV designer building a flying wing, **I want** to configure an elevon (combined elevator + aileron) with independent primary/secondary gains and a differential throw ratio, **so that** AVL and AeroSandbox both see two correctly signed, uniquely named control axes instead of one ambiguous surface.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET / PATCH / DELETE | `.../cross_sections/{i}/trailing_edge_device` | the canonical TED, role + mixing fields |
| GET / PATCH / DELETE | `.../trailing_edge_device/servo` | the TED's servo, 1:1 child |
| GET / PATCH / DELETE | `.../control_surface` (+ `/cad_details`, `/cad_details/servo_details`) | the ASB-compatible projection and its CAD-only subsets |

**Acceptance criteria**

- **AC-1 — A dual-role surface decomposes into two control axes**
  - **Given** a station's trailing-edge device has `role = "elevon"` and `deflection_deg = 10`
  - **When** control axes are resolved for any AVL/ASB build
  - **Then** a `"[elevon]pitch_<wing>_<i>"` variable exists with `sgn_dup +1`, gain `mix_gain_primary`, `symmetric = true`, baseline deflection `10°`; and a `"[elevon]roll_<wing>_<i>"` variable exists with `sgn_dup -1`, gain `mix_gain_secondary`, `symmetric = false`, baseline `0.0` — the zero baseline exists specifically so the AeroBuildup fallback never feeds a spurious roll deflection into the single-axis model.
- **AC-2 — Mixing fields are role-gated**
  - **Given** a trailing-edge device with `role = "flap"` (not in `DIFFERENTIAL_ROLE_VALUES`)
  - **When** I `PATCH trailing_edge_device` with `differential_ratio = 1.5`
  - **Then** the response is **422** `validation_error`; the identical patch against `role = "aileron"` (which **is** a differential role) returns **200**.
- **AC-3 — Duplicate control names are rejected before any AVL file is written**
  - **Given** two surfaces on the aircraft resolve to the same control name (`[role]axis_wing_index`)
  - **When** `assert_unique_control_names` runs
  - **Then** it raises — because AVL silently collapses identically named `CONTROL` variables into a single DOF with no error of its own. Whether this raise reaches the HTTP client as 422 or 500 was not confirmed in the source analysis (see *Open questions*).
- **AC-4 — The role gate is skipped on a partial patch that omits role**
  - **Given** an existing TED with `role = "flap"`
  - **When** I `PATCH` only `mix_gain_secondary = 1.3` without including `role` in the same request body
  - **Then** the write is accepted — `_validate_mix_fields` skips the gate entirely whenever `role` is `None` in the patch, a documented validation hole that a multi-step patch sequence could exploit.

**Confidence:** 🟡 mostly CONFIRMED; AC-3's exact HTTP mapping is a GAP.

## US-WING-05 — Add and optimise a leading-edge turbulator

**As an** RC/UAV designer flying at low Reynolds numbers, **I want** to add a zigzag turbulator strip to a segment and then ask for its optimal chordwise position, **so that** I force transition where it actually reduces drag instead of guessing a location.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET / PUT / DELETE | `.../cross_sections/{i}/turbulator` | read / upsert / delete the segment's turbulator |
| POST | `/aeroplanes/{aeroplane_id}/turbulator/optimize` | per-section trip-location optimisation (aircraft-scoped) |

**Acceptance criteria**

- **AC-1 — A turbulator is added with sensible defaults**
  - **Given** a non-terminal station
  - **When** I `PUT turbulator` with only `position_root = 0.35` (the one required field)
  - **Then** the response is **200**, `form` defaults to `"zigzag"`, `height_mm` defaults to `0.3`, `enabled` defaults to `true`, and `position_tip` — omitted — falls back to `position_root`, giving a strip parallel to the leading edge in `x/c` terms.
- **AC-2 — Terminal station rejected**
  - **Given** the terminal station of the same wing
  - **When** I `PUT turbulator` there
  - **Then** the response is **422** `validation_error` — turbulators are segment-scoped.
- **AC-3 — Optimisation reports a per-section optimum and an aircraft-level ΔCD0**
  - **Given** the aircraft has wing sections with a resolved operating `(CL, Re)`
  - **When** I `POST /turbulator/optimize`
  - **Then** the response is **200** with, per half-span section, `xtr_opt` drawn from the 15-point grid `linspace(0.2, 0.9)` and `delta_cd = cd_tripped − cd_clean` (negative = improvement), plus an aircraft-level `ΔCD0` rolled up with `symmetry_factor = 2` (because the underlying section list is half-span only).
- **AC-4 — A boundary optimum is flagged, not hidden**
  - **Given** the true drag minimum for a section lies at the first or last grid point
  - **When** the optimisation completes
  - **Then** the boundary value is still returned, plus an explicit warning that the true minimum may lie outside `[0.2, 0.9]` — the grid is never silently widened (ADR 0012), and no fallback value is substituted for an all-NaN sweep either (that case instead omits `xtr_opt` for the section, with a warning).

**Confidence:** 🟢 CONFIRMED (whether `xtr_opt` is ever written back into the turbulator row is a GAP — see *Open questions*).

## US-WING-06 — Edit wing geometry through the AI copilot

**As an** AI-copilot user, **I want** to describe a wing change in natural language and have the copilot propose and apply the edit, **so that** I don't have to hand-craft REST payloads myself.

**Endpoints exercised** (copilot tool calls over `app/services/copilot_tools.py`, itself layered on the same wing-design services — not raw REST)

| Tool | Purpose |
|---|---|
| `get_wing_geometry(wing)` | read a hybrid editable/derived geometry block, retargeted to the active proposal branch |
| `apply_design_edits(ops: list[EditOp])` | apply one or more edits, creating/extending a `copilot-proposal` branch |
| `discard_proposal()` | abandon the open proposal branch |

**Acceptance criteria**

- **AC-1 — A tip-append edit creates a proposal and reports the metrics diff**
  - **Given** the user asks to add a new tip station
  - **When** the copilot calls `apply_design_edits` with an `AddXsec` op (`wing`, `at_index = n_xsecs`, `chord`, `span`, `airfoil`, `twist` default `0`, `dihedral` default `0`)
  - **Then** a `"copilot-proposal"`-prefixed branch is created or extended, `"AddXsec"` appears in `applied`, and `diff_proposal_branch` reports before/after values for the 13 tracked metrics (`mass_kg`, `span_m`, `aspect_ratio`, `cd0`, `e_oswald`, `ld_max`, `x_np_m`, `static_margin_pct`, `v_stall_mps`, `v_min_sink_mps`, `v_cruise_mps`, `cl_max`, `wing_area_m2`).
- **AC-2 — A genuine mid-wing insert is rejected per-op, not raised**
  - **Given** an `AddXsec` op whose `at_index` is strictly between `1` and the wing's current station count `n_xsecs` (a true interior insert)
  - **When** `apply_design_edits` runs
  - **Then** the op is placed in `rejected` with the message *"Inserting mid-wing (...) is not yet supported. To add a winglet, append at the TIP: use at_index=`<n_xsecs>`"* — it is not raised as an exception, and any `at_index ≥ n_xsecs` is instead silently clamped to a tip-append and accepted (gh-938).
- **AC-3 — `get_wing_geometry` is the one documented unit exception**
  - **Given** any wing
  - **When** I call `get_wing_geometry`
  - **Then** the result is in **millimetres and degrees** — the only copilot tool that breaks the app's metre convention — and `derived.wing_level.note` carries the BR-6 warning ("a segment's root chord follows the previous segment's tip chord and is not independently settable") as free text, because the schema itself cannot express that constraint.
- **AC-4 — One failing op in a batch does not block the others**
  - **Given** a batch of two ops where the second references an unknown wing name
  - **When** `apply_design_edits` runs
  - **Then** the first op still applies and appears in `applied`, while the second appears in `rejected` with its error — the call never raises for a partial failure.

**Confidence:** 🟢 CONFIRMED (`app/services/copilot_apply_service.py`, `copilot_tools.py`).

## US-WING-07 — Drive wing geometry from an MCP agent

**As an** MCP-agent client, **I want** to create and edit a wing's stations and control surfaces through the wing-related MCP tools, **so that** I can automate wing design without going through the interactive HTTP surface.

**Endpoints exercised** (MCP tools on the `da3dalus-cad-tools` server, mounted at `/mcp`; 20 of the server's 76 tools cover wings/cross-sections/control-surfaces/CAD-details/servos)

| Tool | Purpose |
|---|---|
| `create_aeroplane_wing(aeroplane_id, wing_name, request: AsbWingGeometryWriteSchema)` | create a wing — geometry only |
| `create_wing_cross_section(aeroplane_id, wing_name, cross_section_index, request: WingXSecGeometryWriteSchema)` | insert a station — geometry only |
| `patch_wing_cross_section_control_surface(aeroplane_id, wing_name, cross_section_index, request: ControlSurfacePatchSchema)` | patch the bare ASB control-surface projection |

**Acceptance criteria**

- **AC-1 — Geometry-only creation succeeds and mirrors the REST body**
  - **Given** a valid `aeroplane_id`
  - **When** `create_aeroplane_wing` is called with an `AsbWingGeometryWriteSchema` payload (`xyz_le` / `chord` / `twist` / `airfoil` only — `extra="forbid"`)
  - **Then** the tool result is the created wing, `jsonable_encoder`-serialised exactly like the REST **201** body would be.
- **AC-2 — Structural detail has no MCP tool at all**
  - **Given** the agent wants to set a spar, a trailing-edge device with a role/mixing configuration, or a turbulator while creating a station
  - **When** it inspects `create_wing_cross_section`'s input schema
  - **Then** it finds only `WingXSecGeometryWriteSchema` fields (`xyz_le`, `chord`, `twist`, `dihedral`, `airfoil`) — no `spare_list`, `trailing_edge_device` or `turbulator` field exists on **any** MCP tool. Spar CRUD, turbulator CRUD, the `WingConfiguration` mm bridge (`from-wingconfig` / `wingconfig`), and the raw `trailing_edge_device` route (with its `role`/`mix_gain_primary`/`mix_gain_secondary`/`differential_ratio` fields) have **no MCP tool**; `patch_wing_cross_section_control_surface` only reaches the bare ASB projection (`name`, `hinge_point`, `symmetric`, `deflection` — no `role`).
- **AC-3 — Writes do not durably persist (TD-01)**
  - **Given** the agent calls `create_wing_cross_section` and receives a success payload showing the new station
  - **When** it subsequently reads the wing back over plain REST (`GET .../cross_sections`)
  - **Then** the new station is **absent** — `_call_endpoint` (`app/mcp_server.py`) opens `with SessionLocal() as db:` and never calls `db.commit()`, so `Session.__exit__` rolls the write back. The agent cannot distinguish a genuine success from a silently rolled-back one from the tool result alone; this affects roughly 40 of the 76 tools, wherever the underlying service relies on `get_db()`'s commit.
- **AC-4 — Errors are unstructured**
  - **Given** an unknown `aeroplane_id`
  - **When** any wing tool is called
  - **Then** the agent receives a raw `NotFoundError` message as a generic tool failure — not the `{"error": {"code": "not_found", ...}}` envelope a REST client gets — because `_call_endpoint` does not route through the app's `ServiceException` handler.

**Confidence:** 🟢 CONFIRMED (`app/mcp_server.py`; `mcp-server/contracts.md` — TD-01/G-7 is a documented, verified defect, not a hypothetical).

## Open questions 🔴

- Whether `assert_unique_control_names`'s raise reaches the REST client as 422 or 500 was not confirmed (US-WING-04 AC-3).
- Whether `xtr_opt` from `/turbulator/optimize` is ever written back into `wing_xsec_turbulators`, or is propose-then-adopt only, is unconfirmed (US-WING-05).
- Whether the duplicate-wing-name 422 vs. duplicate-fuselage-name 409 divergence is intentional (US-WING-01 AC-3).
