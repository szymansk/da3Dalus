# Sizing and Placing Spars

> **Personas:** RC/UAV designer · Hobbyist · MCP-agent client
> **Modules:** `wing-design` (`spar-sizing`, `cross-section-crud` slices) + `aero-analysis` (spanwise loads, the moment/torsion input)
> **Primary surface:** `/aeroplanes/{aeroplane_id}/wings/.../spars`, `/aeroplanes/{aeroplane_id}/spanwise_loads_with_sizing`, `/aeroplanes/{aeroplane_id}/spar-plan`, `/aeroplanes/{aeroplane_id}/spar-plan/insert`

## Context

A wing's aerodynamic geometry says nothing about how it is actually built inboard-to-tip. This flow covers the structural side: placing an individual spar by hand on one segment, sizing a spar from real bending/torsion loads at a chosen material and cross-section shape, solving a full buildable spar layout (front bending spar + rear torsion spar, telescoping runs, joints) from a spanwise moment distribution, and inserting that solved plan back into the wing as persisted, revertible spares. Every dimensional spar field is **metres on the wire, millimetres in storage** (gh-402); `spare_vector` is a dimensionless unit direction, never scaled.

## US-SPAR-01 — Place a spar directly on a segment

**As an** RC/UAV designer, **I want** to add, read, update and delete a single spar on a specific wing segment, **so that** I can hand-place structure the solver doesn't need to compute for me.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `.../cross_sections/{i}/spars` | list the segment's spars, ordered by `sort_index` |
| POST | `.../cross_sections/{i}/spars` | create a spar |
| PUT | `.../cross_sections/{i}/spars/{spar_index}` | update a spar |
| DELETE | `.../cross_sections/{i}/spars/{spar_index}` | delete a spar |

**Acceptance criteria**

- **AC-1 — Metres on the wire, millimetres in storage**
  - **Given** a non-terminal station and a request body with `spare_length = 0.25` and `spare_support_dimension_width = 0.008` (both metres)
  - **When** I `POST .../spars`
  - **Then** the response is **201**, the `wing_xsec_spares` row stores `spare_length = 250.0` and `width = 8.0` (millimetres, `_M_TO_MM = 1000.0`), and a follow-up `GET` returns `spare_length = 0.25` again (`_MM_TO_M = 0.001` on read).
- **AC-2 — Terminal station rejected**
  - **Given** the terminal station of the wing
  - **When** I `POST` a spar there
  - **Then** the response is **422** `validation_error` — spars are segment-scoped.
- **AC-3 — `spare_vector` is never scaled**
  - **Given** a spar written with `spare_vector = [0, 1, 0]`
  - **When** I read it back
  - **Then** it is exactly `[0, 1, 0]` — dimensionless, untouched by either conversion direction; `spare_mode` is one of `normal | follow | standard | standard_backward | orthogonal_backward`.
- **AC-4 — Unknown spar index**
  - **Given** a segment with 2 spars (indices 0, 1)
  - **When** I `PUT` or `DELETE spars/5`
  - **Then** the response is **404** `not_found`.

**Confidence:** 🟢 CONFIRMED

## US-SPAR-02 — Get real spar dimensions from a flight condition

**As a** Hobbyist who doesn't want to hand-supply a bending-moment table, **I want** to give the system a flight condition and a material and get back sized spar dimensions per surface, **so that** I get a structurally grounded answer from a number I already understand (an airspeed) instead of an engineering abstraction I don't.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/spanwise_loads_with_sizing` | spanwise loads for every surface, extended with per-surface spar sizing (gh-1008) |

**Acceptance criteria**

- **AC-1 — Defaults produce a conservative sized answer**
  - **Given** an `OperatingPointSchema` body (alpha, velocity, altitude) and query params `material_id=<a material Component id>` only — `shape` defaults to `"tube"`, `safety_factor_j` to `1.5`, `packing_factor` to `0.8`
  - **When** I `POST /spanwise_loads_with_sizing?material_id=7`
  - **Then** the response is **200** `SpanwiseLoadsWithSizingResponse` with one `SparSizingResult` per surface (matched by position and `surface_name`), each carrying per-station `stations[]` (ordered tip→root), a `root_station`, `spar_mass_half_kg` / `spar_mass_full_kg`, and `g_limit` taken from the aeroplane's design assumptions (`g_limit_fallback = true` with a fallback of `3.0` when no assumption row exists).
- **AC-2 — `material_id` is required, but the 422 bypasses the app's error envelope**
  - **Given** `material_id` is omitted
  - **When** I call the endpoint
  - **Then** the response is **422**, but with the plain FastAPI `{"detail": "material_id is required for spar sizing"}` body — the handler raises a bare `HTTPException` here rather than the domain `ValidationError` the rest of the module uses, so this one path does **not** get the `{"error": {"code": "validation_error", ...}}` envelope.
- **AC-3 — A capped shape without a cap width is under-specified**
  - **Given** `shape=capped` and `cap_width_mm` omitted
  - **When** I call the endpoint
  - **Then** the request itself is accepted (the field is optional at the schema level even though its own description says "required for shape='capped'") — the practical consequence (a per-station infeasibility, an implicit default, or an error deeper in the solver) is unconfirmed; see *Open questions*.
- **AC-4 — Missing airfoil thickness data degrades to a documented fallback**
  - **Given** a station whose airfoil thickness cannot be resolved
  - **When** sizing runs
  - **Then** that station uses `t/c = 0.12` (the fallback ratio), sets `tc_fallback = true` on the station, and the response-level `tc_fallback_warning` lists the affected span positions — it is never a silent, unflagged substitution.

**Confidence:** 🟢 CONFIRMED (verified directly against `app/api/v2/endpoints/aeroanalysis.py` and `app/schemas/spar_sizing.py`); AC-3's runtime consequence is 🔴 GAP.

## US-SPAR-03 — Compute a buildable root-to-tip spar plan

**As an** RC/UAV designer, **I want** to solve a full front (bending) + rear (torsion) spar layout from a spanwise moment distribution, **so that** I get real pieces — origin, direction, diameter, joints — instead of a single per-station dimension.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/spar-plan` | solve the buildable spar plan (gh-1031) |

**Acceptance criteria**

- **AC-1 — A plan is returned with front and rear pieces, root→tip**
  - **Given** `material_id`, a spanwise `moments` list (`[{y_span, bending_moment_Nm}, ...]`, at least one sample, from the `spanwise_loads` endpoint) and defaults for everything else
  - **When** I `POST /spar-plan`
  - **Then** the response is **200** `SparPlanResponse` with `front_pieces` and `rear_pieces` (each a `SparPieceOut`: `spare_origin`/`spare_vector` in the wing-local frame, `outer_d`/`inner_d`/`wall` in metres, `governing_y`, `x_over_chord`, `utilisation`, `feasible`), `front_joint ∈ {"continuous", "reinforcement+joiner"}`, `rear_joint ∈ {"continuous", "bent-pin"}`.
- **AC-2 — The rear spar is torsion-driven, with a documented proxy when torsion isn't supplied**
  - **Given** `torsion_moments` (T(y) about the front spar) is supplied
  - **When** the plan is solved
  - **Then** the rear spar is sized for that couple reacted over the front–rear spar spacing, plus `rear_secondary_bending_fraction` (default `0.0`, i.e. torsion-only) of the bending moment; when `torsion_moments` is **omitted**, the documented proxy `T(y) ≈ pitching_moment_proxy_ratio (0.10) · M(y)` is used instead — the front spar always stays bending-driven via `moments`.
- **AC-3 — Layout defaults are sensible without tuning**
  - **Given** `front_x_over_chord` omitted
  - **When** the plan is solved
  - **Then** the front spar is placed at each section's max-thickness location; `rear_x_over_chord` defaults to `0.65`, `n_span` to `6` stations root→tip, `shape` to `"tube"`.
- **AC-4 — Unknown aeroplane/wing, or geometry unavailable**
  - **Given** an unknown `aeroplane_id`, or a platform without CadQuery (e.g. `linux/aarch64`), or invalid material/strength inputs
  - **When** I call the endpoint
  - **Then** the response is **404** for the unknown aeroplane/wing, or **422** for unavailable section geometry or invalid sizing inputs.

**Confidence:** 🟢 CONFIRMED (`app/schemas/spar_plan.py`, `app/api/v2/endpoints/aeroanalysis.py`)

## US-SPAR-04 — Insert the computed plan into the wing, with a safety net

**As an** RC/UAV designer, **I want** to preview the plan's insertions before committing them, and know I can revert a commit, **so that** I never lose an existing spar layout by accident.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/spar-plan/insert` | map the plan to persisted `Spare` rows (gh-1049) |

**Acceptance criteria**

- **AC-1 — A dry run previews without writing**
  - **Given** the same `SparPlanRequest` inputs plus `dry_run = true` (the default)
  - **When** I `POST /spar-plan/insert`
  - **Then** the response is **200** `SparInsertResponse` with `committed = false`, `planned_spares[]` each carrying `segment_index`, `spar_index` (front = `0` in every segment, rear = `1`, a reinforcement piece = the next index — the same logical spar keeps the same index across every segment it touches), `role`, dimensions and `spare_origin`/`spare_vector` — and `snapshot_id = null` because nothing was mutated.
- **AC-2 — A commit persists and snapshots the pre-insert state first**
  - **Given** the same request with `dry_run = false`
  - **When** I `POST`
  - **Then** the response has `committed = true`, each piece is persisted as a `Spare` **replacing** any existing spares in the touched segments, and — because that replace is destructive — an immutable snapshot of the aeroplane's pre-insert state is auto-created first (gh-1058) with its id returned as `snapshot_id`, so the user can one-click revert via `POST /aeroplanes/{snapshot_id}/restore` (versioning module, **201**).
- **AC-3 — An infeasible plan is refused, not built**
  - **Given** the computed plan reports `feasible = false`
  - **When** I `POST` with `dry_run = false`
  - **Then** the response is **422** — an infeasible plan is never committed.
- **AC-4 — A telescoping front spar splits its host segment (gh-1063)**
  - **Given** the solved front spar telescopes into more than one piece
  - **When** the plan is committed
  - **Then** the host wing segment is split at each joint so every resulting sub-segment carries exactly one main piece at `spar_index = 0` (the VaseMode invariant), and `planned_segment_lengths` lists the per-sub-segment spanwise lengths root→tip; the field is `null` when the front spar is single-piece.

**Confidence:** 🟢 CONFIRMED (`app/schemas/spar_insert.py`)

## US-SPAR-05 — See an infeasible or negligible-load region reported honestly

**As an** RC/UAV designer, **I want** the solver to tell me plainly when no round tube fits a station, or when a tip region needs no spar at all, **so that** I can react to a real structural finding instead of building from a silently clamped or fabricated dimension.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/spar-plan` | same solve; this story reads the feasibility and no-spar fields |

**Acceptance criteria**

- **AC-1 — An over-loaded root is reported, not clamped**
  - **Given** a root station whose strength-required outer diameter exceeds the local containment band
  - **When** the plan is solved
  - **Then** `feasible = false`, `utilisation` (`od / max(tightest_band, 1e-6)`) is `> 1.0`, and `infeasibility_reason` names the governing station and suggests a capped or box spar — the piece is still emitted, never silently resized to fit (ADR 0012).
- **AC-2 — A negligible-load tip gets no spar, and the boundary is reported**
  - **Given** a tip station whose strength-required OD falls below `1.0 mm` (`NEGLIGIBLE_OD_FLOOR_MM`)
  - **When** the plan is solved
  - **Then** no piece is emitted for that outboard region, and `front_no_spar_from_y` / `rear_no_spar_from_y` report the spanwise position where the spar stops (`null` when the spar runs all the way to the tip; the root `y` when the whole span is negligible).
- **AC-3 — A single-half surface forces a continuous front joint (gh-1091)**
  - **Given** a vertical stabiliser (one half only, no port/starboard pair)
  - **When** the plan is solved
  - **Then** `front_joint = "continuous"` is forced rather than the solver indexing into the (non-existent) other half.

**Confidence:** 🟢 CONFIRMED (`cad_designer/airplane/geometry/spar_solver.py`)

## US-SPAR-06 — Keep a computed rear spar clear of the control-surface hinge

**As an** RC/UAV designer with an aileron or flap on the same segment, **I want** the computed rear (torsion) spar to automatically stay clear of the hinge line, **so that** I don't have to manually check for a structural/control-surface collision every time I resize.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/spar-plan` | same solve; this story exercises the hinge-clearance guard (gh-1059) |

**Acceptance criteria**

- **AC-1 — A requested rear spar is pulled forward of the hinge**
  - **Given** a requested `rear_x_over_chord = 0.80` and a control surface hinged at `x/c = 0.72` on the same segment
  - **When** the plan is solved
  - **Then** the resulting piece's `x_over_chord` is `≤ 0.69` (`hinge_x_c − 0.03`) and `≥ 0.05` — this guard applies only to the **computed** rear spar; a manually placed reinforcement spar is not subject to it.
- **AC-2 — A hinge too far forward defeats the clearance without warning**
  - **Given** `hinge_x_c − 0.03 < 0.05` (an unusually forward hinge)
  - **When** the plan is solved
  - **Then** the `0.05` floor wins and the computed rear spar sits at `x/c = 0.05`, inside the intended `0.03` clearance margin from the hinge — no warning is emitted for this case (a documented gap).
- **AC-3 — No hinge means no clamp**
  - **Given** the segment has no control surface
  - **When** the plan is solved
  - **Then** the requested `rear_x_over_chord` is used unchanged.

**Confidence:** 🟢 CONFIRMED (`cad_designer/airplane/geometry/spar_solver.py:181-221`)

## US-SPAR-07 — Discover that spar planning has no MCP tool

**As an** MCP-agent client, **I want** to size or insert a spar plan through the tool registry, **so that** I can automate structural design the way I can automate wing geometry edits.

**Endpoints exercised** (none — this story documents a verified absence in the `da3dalus-cad-tools` MCP server)

| Tool | Purpose |
|---|---|
| — | no tool exists for spar CRUD, `spanwise_loads_with_sizing`, `spar-plan`, or `spar-plan/insert` |

**Acceptance criteria**

- **AC-1 — No spar-related tool exists**
  - **Given** the agent enumerates the 76 tools on `da3dalus-cad-tools`
  - **When** it searches for anything matching spar CRUD, spar sizing, or spar-plan compute/insert
  - **Then** it finds none — a direct search of the server's tool declarations confirms zero matches for `spar` (or `turbulator`, or `wingconfig`) anywhere in `app/mcp_server.py`. The 20 wing-related MCP tools cover only wings, cross-sections and the ASB control-surface projection (see `design-a-wing.md` US-WING-07).
- **AC-2 — The agent must fall back to a direct REST call**
  - **Given** the agent still needs to compute or insert a spar plan
  - **When** it calls `POST /aeroplanes/{aeroplane_id}/spar-plan` or `.../spar-plan/insert` directly over HTTP, outside the MCP tool registry
  - **Then** it gets the normal REST contract (US-SPAR-03/04) — including the app's structured `{"error": {...}}` envelope and a durable commit via `get_db()`, neither of which the MCP transport provides for its own tools (TD-01, see `design-a-wing.md` US-WING-07 AC-3). A hypothetical future MCP wrapper around this endpoint would need to be built carefully to avoid inheriting that non-persistence defect.

**Confidence:** 🟢 CONFIRMED (verified absent via direct search of `app/mcp_server.py`; `mcp-server/contracts.md` lists "turbulator optimizer" among modules with no MCP tools at all, and spar-plan/spar CRUD are absent from the same 76-tool inventory).

## Open questions 🔴

- The runtime consequence of `shape=capped` with `cap_width_mm` omitted on `/spanwise_loads_with_sizing` (silent default, per-station infeasibility, or a deeper error) was not confirmed (US-SPAR-02 AC-3).
- Whether `packing_factor` scaling the sizing formula's `outer(y)` and the same knob deriving the containment band in station sampling is one conceptual application or a double application was not confirmed (flagged in the module's own design doc).
- Which service supplies `moment_fn(y_span)` to the spar-plan solver, and whether `g_limit`/`j` are already applied upstream before `spar-plan` applies them again, was not confirmed.
