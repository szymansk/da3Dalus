# Export CAD Geometry

> **Personas:** RC/UAV designer, Hobbyist, AI-copilot user, MCP-agent client
> **Modules:** `cad-generation` (+ `cad-designer-topology`, `fuselage-design`)
> **Primary surface:** `/aeroplanes/{aeroplane_id}/wings/...`, `/aeroplanes/{aeroplane_id}/status`,
> `/aeroplanes/{aeroplane_id}/tessellation`, `/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/step`

## Context

A designer needs two different things out of a persisted wing or fuselage:
something to **look at** (a tessellated 3D preview in the workbench viewer)
and something to **manufacture with** (an STL/STEP/IGES/3MF file for a
printer or another CAD tool). Both are CPU-bound CadQuery builds, so both run
asynchronously in a worker process: the client kicks off a task, polls a
status endpoint, and then either reads a cached scene or fetches the finished
archive. This flow is only reachable at all when the CAD kernel is available
on this deployment — the entire router is unmounted otherwise (ADR 0017).

## US-EXPORTCAD-01 — Export a wing to a manufacturable file

**As a** RC/UAV designer who needs an STL for printing or a STEP for another
CAD tool (also the Hobbyist doing a simple print-ready export, and the
MCP-agent client automating exports), **I want** to kick off a wing export in
my chosen format, **so that** I get a real file without blocking on the build.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}` | Start an asynchronous wing export |

`creator_url_type ∈ {wing_loft, vase_mode_wing}` (default `wing_loft`);
`exporter_url_type ∈ {stl, step, amf, iges, 3mf}` (default `stl`). The two
vase-mode offset factors (`leading_edge_offset_factor=0.1`,
`trailing_edge_offset_factor=0.15`) are **query** parameters, not body fields.

**Acceptance criteria**

- **AC-1 — An export is accepted and queued**
  - **Given** an aeroplane with a wing named `"main"`
  - **When** I `POST /aeroplanes/{id}/wings/main/wing_loft/stl`
  - **Then** the response is **202 Accepted** with `CadTaskAcceptedResponse {aeroplane_id, href}`
  - **And** the task is registered `PENDING` for that aeroplane
- **AC-2 — A concurrent export for the same aeroplane is rejected**
  - **Given** an export task for aeroplane A is already `PENDING`/`RUNNING`
  - **When** I `POST` a second export for aeroplane A (any wing or format)
  - **Then** the response is **409** with error code `conflict`
  - **And** this guard is scoped to **one aeroplane only** — two exports for two *different* aeroplanes run in parallel and share the same on-disk staging directory, so they can silently overwrite or delete each other's files
- **AC-3 — Two of the five advertised formats do not work**
  - **Given** `exporter_url_type = "amf"`
  - **When** I `POST` the export
  - **Then** the response is **422** — the enum value is published in the API schema but has no exporter mapping
  - **And Given** `exporter_url_type = "3mf"`, **When** the task runs, **Then** it is accepted with 202 but the worker fails asynchronously to `FAILURE` (the mapping resolves to a misspelled, non-existent class name) — a client must poll status to discover either failure; neither is reported synchronously
- **Confidence:** 🟢 CONFIRMED

## US-EXPORTCAD-02 — Poll an export's status

**As a** RC/UAV designer, Hobbyist, AI-copilot user or MCP-agent client who
just started an export, **I want** to check whether it finished, **so that**
I know when the file is ready to download.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/status` | Report task status (`task_type`, `wing_name` query params select which task) |

**Acceptance criteria**

- **AC-1 — Status transitions from pending to a result**
  - **Given** a wing export just started for aeroplane `{id}`
  - **When** I `GET /aeroplanes/{id}/status` (no query params — this selects the export task)
  - **Then** the response is **200** with `status` `"PENDING"` or `"RUNNING"`, and once the worker finishes, `"SUCCESS"` with `result.zipfile` populated
  - **And** `message`/`result` are **omitted** from the JSON (not sent as `null`) whenever they don't apply
- **AC-2 — An unknown task is a 404, and the accepted-response `href` is a trap**
  - **Given** no task has ever been registered for aeroplane `{id}`
  - **When** I `GET /aeroplanes/{id}/status`
  - **Then** the response is **404**
  - **And** a client must build this URL itself with the right `task_type`/`wing_name` query params — the `href` field on the **202** accepted-response points at `/aeroplanes/{id}`, not at this status resource, despite the API docstring saying otherwise
- **Confidence:** 🟢 CONFIRMED

## US-EXPORTCAD-03 — Download the exported archive

**As a** RC/UAV designer or Hobbyist retrieving the finished file (also the
MCP-agent client feeding it to downstream tooling), **I want** to fetch the
completed export, **so that** I have the actual STL/STEP/IGES/3MF bytes.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/{creator_url_type}/{exporter_url_type}/zip` | Get a descriptor for the finished export archive |

**Acceptance criteria**

- **AC-1 — The route returns a descriptor, not the file bytes**
  - **Given** a `SUCCESS` export task for aeroplane `{id}`
  - **When** I `GET /aeroplanes/{id}/wings/main/wing_loft/stl/zip`
  - **Then** the response is **200** JSON `{"url", "filename", "mime_type": "application/zip"}`
  - **And** `url` points at the `/static` mount — the caller must issue a **second** `GET` against that `url` to receive the archive bytes
- **AC-2 — The wing/format path segments are cosmetic only**
  - **Given** the same aeroplane has completed exactly one export (say `main`/`wing_loft`/`step`)
  - **When** I `GET .../htail/vase_mode_wing/stl/zip` (a different wing and format that was never exported)
  - **Then** the response is still **200**, returning the descriptor for that **same, last** archive — the export path is keyed on the aeroplane alone, so a URL built with the wrong wing or format silently returns someone else's file rather than a 404
- **Confidence:** 🟢 CONFIRMED

## US-EXPORTCAD-04 — Tessellate a wing for the 3D viewer

**As a** RC/UAV designer or Hobbyist viewing their wing in the workbench 3D
viewer (also the AI-copilot user refreshing a preview after a design change),
**I want** to trigger a tessellation, **so that** the viewer has geometry to
render.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/wings/{wing_name}/tessellation` | Start an asynchronous wing tessellation |

**Acceptance criteria**

- **AC-1 — A tessellation is accepted and eventually cached**
  - **Given** a persisted wing `"main"`
  - **When** I `POST /aeroplanes/{id}/wings/main/tessellation`
  - **Then** the response is **202** `CadTaskAcceptedResponse`
  - **And** `GET /aeroplanes/{id}/status?task_type=tessellation&wing_name=main` eventually reports `"SUCCESS"`
- **AC-2 — A second tessellation for the same wing silently overwrites the first**
  - **Given** a tessellation for `"main"` is still `PENDING`/`RUNNING`
  - **When** I `POST` a second tessellation for the **same** wing
  - **Then** the response is still **202** — this route never checks for a conflicting task the way the export route does, so the first task's registry entry is overwritten and its result becomes unreachable (the declared `409` on this route is never actually returned)
- **Confidence:** 🟢 CONFIRMED

## US-EXPORTCAD-05 — Read the merged 3D scene for an aeroplane

**As a** RC/UAV designer or Hobbyist opening the workbench viewer (also the
AI-copilot user checking whether a rebuild is needed), **I want** one
combined scene of every tessellated part, **so that** I see the whole
aircraft, not one wing at a time.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/tessellation` | Read the merged, cached scene for the whole aeroplane |

**Acceptance criteria**

- **AC-1 — Multiple cached parts merge into one scene**
  - **Given** cached tessellations exist for wings `"main"` and `"htail"`
  - **When** I `GET /aeroplanes/{id}/tessellation`
  - **Then** the response is **200** with both parts in one `data.shapes` tree, every `{ref: N}` rebased into one merged `instances` array, wings coloured `#FF8400` and every non-wing part `#888888`
  - **And** `is_stale` reports whether any contributing entry is stale relative to the current wing geometry
- **AC-2 — Nothing cached yet**
  - **Given** an aeroplane with no cached tessellation at all
  - **When** I `GET /aeroplanes/{id}/tessellation`
  - **Then** the response is **404**
  - **And** regardless of the real geometry extent, `bb.min`/`bb.max` are always reported as `[0,0,0]`/`[0,0,0]` — a client must not use this field for camera framing
- **Confidence:** 🟢 CONFIRMED

## US-EXPORTCAD-06 — Download fuselage STEP artefacts

**As a** RC/UAV designer downloading precise fuselage geometry for another
CAD tool (also the MCP-agent client fetching the same files programmatically),
**I want** to retrieve the surface and, when available, the solid STEP for a
fuselage, **so that** I can work with the exact geometry outside this app.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/step` | Download the Surface STEP |
| GET | `/aeroplanes/{aeroplane_id}/fuselages/{fuselage_name}/solid_step` | Download the sewn Solid STEP |

**Acceptance criteria**

- **AC-1 — The surface STEP downloads whenever one is recorded**
  - **Given** a fuselage with a recorded `step_path` (for example, from an OpenVSP import)
  - **When** I `GET /aeroplanes/{id}/fuselages/{name}/step`
  - **Then** the response is **200** with the Surface STEP file
- **AC-2 — The solid STEP may legitimately be missing**
  - **Given** a fuselage whose solid sewing failed, or that was never produced from an OpenVSP import (`solid_step_path` is `null`)
  - **When** I `GET /aeroplanes/{id}/fuselages/{name}/solid_step`
  - **Then** the response is **404**, even though the surface-STEP route for the same fuselage still succeeds
- **Confidence:** 🟢 CONFIRMED

## Open questions 🔴

- **This whole flow disappears, not degrades, without a CAD kernel.** On a
  platform where CadQuery cannot be imported, none of routes 01–05 exist at
  all — the entire router is left unmounted and every one of these paths
  answers a plain router-table 404 (ADR 0017). There is no discovery endpoint
  that tells a client "CAD is unavailable here" versus "unknown aeroplane" —
  the two look identical.
- **Should `amf` be mapped or removed, and should the `ExportTo3mfCreator`
  spelling defect be fixed?** Both are published, user-facing formats that
  fail today (see AC-3 of US-EXPORTCAD-01); an existing unit test currently
  pins the wrong spelling.
- **Is the `href` on the 202 accepted-responses meant to point at `/status`?**
  Both the wing-export and wing-tessellation accept-responses carry
  `href = "/aeroplanes/{id}"`, while their own docstrings describe polling via
  `GET /status`.
- **Is the merged-scene bounding box expected to ever be useful?** The
  producer and the consumer disagree on the bounding-box key set
  (`xmin/xmax/…` vs `min`/`max`), so `bb` in US-EXPORTCAD-05 always comes back
  degenerate regardless of the real model — no re-implementation should
  reproduce this without deciding whether camera-fit quality actually matters.
