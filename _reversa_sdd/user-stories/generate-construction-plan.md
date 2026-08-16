# Generate a Construction Plan

> **Personas:** RC/UAV designer, Hobbyist, AI-copilot user, MCP-agent client
> **Modules:** `construction-plans` (+ `cad-designer-topology`, `cad-generation`)
> **Primary surface:** `/construction-plans`, `/construction-templates`,
> `/aeroplanes/{aeroplane_id}/construction-plans`

## Context

A construction plan is a reusable JSON build recipe — a tree of `cad_designer`
Creators (wing lofts, exporters, cut-outs, etc.) — that produces manufacturable
geometry when run against a real aeroplane. Users browse a catalog of available
build steps, assemble or reuse a plan, bind it to an aeroplane (directly, or by
instantiating a shared template), execute it to get CAD shapes and downloadable
artefacts, and optionally promote a tuned plan back into a template for the next
aircraft. This happens in the workbench's plan editor, through the MCP tool
surface, or via the AI copilot acting on the user's behalf.

## US-CPLAN-01 — Browse the available build steps (Creator catalog)

**As a** RC/UAV designer assembling a custom plan (also relevant to the
AI-copilot user populating a gallery and the MCP-agent client discovering
capabilities), **I want** to list every Creator with its parameters, types,
allowed values and outputs, **so that** I can pick the right build step without
reading source code.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/construction-plans/creators` | List every registered Creator with parameters/outputs/category |

**Acceptance criteria**

- **AC-1 — Catalog reflects the live Creator tree**
  - **Given** the CAD kernel (`cad_designer` / CadQuery) is importable on this platform
  - **When** I `GET /construction-plans/creators`
  - **Then** the response is **200** with a `list[CreatorInfo]` sorted by `(category, class_name)`
  - **And** a Creator whose constructor takes a `Literal`-typed parameter reports its allowed values in `options`, with `typing.` / `cad_designer.airplane.types.` prefixes stripped from its type string
- **AC-2 — Degrades to an empty catalog, never an error, when CAD is unavailable**
  - **Given** `cad_designer` cannot be imported on this deployment (e.g. `linux/aarch64`, ADR 0017)
  - **When** I `GET /construction-plans/creators`
  - **Then** the response is still **200**, with an empty list `[]` — never a 500 and never a 503
- **Confidence:** 🟢 CONFIRMED

## US-CPLAN-02 — Create and edit a plan's build tree

**As a** RC/UAV designer building a bespoke recipe (also the AI-copilot user
generating a plan programmatically), **I want** to save and revise a
`tree_json` build tree under a name, **so that** I can iterate on a plan before
running it.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/construction-plans` | Create a plan or template from a `tree_json` payload |
| GET | `/construction-plans/{plan_id}` | Read a stored plan |
| PUT | `/construction-plans/{plan_id}` | Replace a plan's `tree_json` / metadata |
| DELETE | `/construction-plans/{plan_id}` | Delete a plan |

**Acceptance criteria**

- **AC-1 — A plan is created from a minimally valid tree**
  - **Given** a `tree_json` payload whose root carries a `$TYPE` and a `creator_id`
  - **When** I `POST /construction-plans`
  - **Then** the response is **201** with a `PlanRead` (`id`, `created_at`, `updated_at` added)
  - **And** structural problems *below* the root (e.g. an unresolvable Creator) are **not** caught here — they only surface when the plan is executed
- **AC-2 — A malformed root is rejected at write time**
  - **Given** a `tree_json` payload whose root is missing `$TYPE` or `creator_id`
  - **When** I `POST /construction-plans`
  - **Then** the response is **422**, body `{"detail": "…"}` — **not** the `{"error": {"code","message","details"}}` envelope used by the aeroplane/CAD routers elsewhere in this API
- **AC-3 — Reading and updating an unknown plan**
  - **Given** no plan exists with id `999999`
  - **When** I `GET`, `PUT` or `DELETE /construction-plans/999999`
  - **Then** each responds **404**
  - **And** a successful `DELETE` of an existing plan responds **204** with an empty body
- **Confidence:** 🟢 CONFIRMED

## US-CPLAN-03 — Instantiate a template into an aeroplane-bound plan

**As a** Hobbyist starting from a shared build template (also the RC/UAV
designer batch-producing plans across several airframes), **I want** to spin
up my own copy of a template bound to my aeroplane, **so that** I can build my
own geometry without touching the shared recipe.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/construction-plans/from-template/{template_id}` | Deep-copy a template into a new plan bound to this aeroplane |

**Acceptance criteria**

- **AC-1 — A template instantiates as an independent, bound copy**
  - **Given** a stored plan with `plan_type == "template"` and `aeroplane_id == null`, and an aeroplane that exists
  - **When** I `POST /aeroplanes/{aeroplane_id}/construction-plans/from-template/{template_id}` (an optional body may override `name`)
  - **Then** the response is **201** with `plan_type == "plan"`, `aeroplane_id` set to the path aeroplane, and name `"{template.name} — Plan"` unless overridden
  - **And** the new row's `tree_json` is a deep copy — editing it afterwards never changes the source template, and there is no version link back to it
- **AC-2 — Instantiating a non-template is rejected**
  - **Given** a stored row with `plan_type == "plan"` (not `"template"`)
  - **When** I `POST from-template/{that_id}`
  - **Then** the response is **422**
- **Confidence:** 🟢 CONFIRMED

## US-CPLAN-04 — Execute a plan and get shapes plus downloadable artefacts

**As a** RC/UAV designer producing a manufacturable file (also the Hobbyist
running a saved recipe, and the MCP-agent client automating a build),
**I want** to run a plan against my aeroplane, **so that** I get real CAD
shapes and files I can inspect or export.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/construction-plans/{plan_id}/execute` | Execute a plan; `aeroplane_id` in the body only if the plan is a template |
| POST | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/execute` | Execute a plan already scoped to the path's aeroplane |

**Acceptance criteria**

- **AC-1 — A bound plan executes and captures artefacts**
  - **Given** a plan bound to an aeroplane that has at least one wing
  - **When** I `POST /construction-plans/{plan_id}/execute`
  - **Then** the response is **200** with `ExecutionResult.status == "success"`, non-empty `shape_keys`, and populated `artifact_dir` + `execution_id`
  - **And** running the same plan again creates a **second**, independent execution directory (plan runs accumulate; only template runs are wiped)
- **AC-2 — A template with no aeroplane anywhere is rejected**
  - **Given** a plan with `plan_type == "template"` and `aeroplane_id == null`
  - **When** I `POST /construction-plans/{plan_id}/execute` with an empty body (no `aeroplane_id`)
  - **Then** the response is **422**
- **AC-3 — A failing Creator is a structured result, not a server error**
  - **Given** a plan whose Creator raises during `create_shape`
  - **When** I execute it
  - **Then** the HTTP response is still **200**
  - **And** `ExecutionResult.status == "error"` with `error`, `duration_ms`, `artifact_dir` and `execution_id` populated — a caller **must** inspect the response body, not the HTTP status, to detect failure
- **Confidence:** 🟢 CONFIRMED

## US-CPLAN-05 — Watch a plan build live

**As a** RC/UAV designer or Hobbyist watching a multi-step build in the
workbench (also the AI-copilot user narrating progress), **I want** to see
each shape appear as it's built, **so that** I get feedback during a
multi-second/minute execution instead of a blank wait.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/execute-stream` | Execute a plan as Server-Sent Events |

**Acceptance criteria**

- **AC-1 — Every displayed shape produces an SSE frame**
  - **Given** a plan whose Creators call `Workplane.display(...)` twice
  - **When** I `GET .../execute-stream`
  - **Then** the response media type is `text/event-stream` with header `X-Accel-Buffering: no`
  - **And** exactly two `event: shape` frames arrive before one `event: complete` frame carrying `duration_ms`, `shape_keys`, `artifact_dir` and `execution_id`
- **AC-2 — A stalled build times out instead of hanging forever**
  - **Given** an execution that produces nothing for 300 seconds
  - **When** the queue starves
  - **Then** an `event: error` frame `{"error": "Execution timed out"}` is emitted
  - **And** the worker thread is joined with a 5-second timeout (it is a daemon thread, so a genuinely hung OCCT call is abandoned, not awaited)
- **Confidence:** 🟢 CONFIRMED

## US-CPLAN-06 — Promote a tuned plan back into a reusable template

**As a** RC/UAV designer who refined a plan for one aircraft, **I want** to
lift it back into a template, **so that** I can reuse the same recipe on the
next airframe.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/construction-plans/{plan_id}/to-template` | Deep-copy a bound plan into a reusable template |

**Acceptance criteria**

- **AC-1 — A bound plan is lifted into an independent template**
  - **Given** a plan bound to an aeroplane
  - **When** I `POST .../{plan_id}/to-template` (an optional body may override `name`)
  - **Then** the response is **201** with `plan_type == "template"`, `aeroplane_id == null`, and name `"{plan.name} — Template"` unless overridden
  - **And** there is no back-link to the source plan — the two evolve independently from this point on
- **AC-2 — An unknown plan cannot be promoted**
  - **Given** no plan exists with the given id
  - **When** I `POST .../{plan_id}/to-template`
  - **Then** the response is **404**
- **Confidence:** 🟢 CONFIRMED

## US-CPLAN-07 — Browse, download and delete execution artefacts

**As a** RC/UAV designer fetching the STL/STEP output of a run (also the
MCP-agent client retrieving files programmatically), **I want** to list,
download and clean up the files an execution produced, **so that** I can get
my manufacturable file and keep old runs from piling up.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/construction-plans/{plan_id}/artifacts` | List every execution directory for a plan |
| GET | `/construction-plans/{plan_id}/artifacts/{execution_id}` | List files in one execution (`subpath`, `recursive` query params) |
| GET | `/construction-plans/{plan_id}/artifacts/{execution_id}/zip` | Download the whole execution as a zip |
| GET | `/construction-plans/{plan_id}/artifacts/{execution_id}/{filename:path}` | Download a single file |
| DELETE | `/construction-plans/{plan_id}/artifacts/{execution_id}/{filename:path}` | Delete a single file |
| DELETE | `/construction-plans/{plan_id}/artifacts/{execution_id}` | Delete an entire execution |

**Acceptance criteria**

- **AC-1 — Executions and their files are listable**
  - **Given** a plan with two prior executions
  - **When** I `GET /construction-plans/{plan_id}/artifacts`
  - **Then** the response is **200** with two `ArtifactDirectory` entries (`execution_id`, `created`, `file_count`)
  - **And** `GET .../{execution_id}?subpath=wing&recursive=true` returns a flat `list[ArtifactFile]` including files nested under `wing/`
- **AC-2 — The whole execution downloads as a zip, even when empty**
  - **When** I `GET .../{execution_id}/zip`
  - **Then** the response is **200** `application/zip` named `plan-{plan_id}-{execution_id}.zip`
  - **And** an execution with no files still yields a **valid, empty** archive rather than a 404
- **AC-3 — Path traversal is rejected**
  - **Given** a requested filename such as `../../etc/passwd`, or a filename that resolves to a symlink inside the execution directory
  - **When** I `GET .../{execution_id}/{filename:path}`
  - **Then** the response is **422** — every artefact path is resolved and confined to the execution directory before it is opened
- **AC-4 — Deleting a file or a whole execution**
  - **When** I `DELETE .../{execution_id}/{filename:path}` or `DELETE .../{execution_id}`
  - **Then** each responds **204** with an empty body; a request against an unknown `plan_id` or `execution_id` responds **404**
- **Confidence:** 🟢 CONFIRMED

## Open questions 🔴

- **Silent partial execution:** a wing that fails millimetre conversion during
  execution is quietly dropped from `wing_config`, and the plan then runs
  against a partial aircraft. `ExecutionResult` has no warnings field, so a
  client cannot tell "success" from "success, minus a wing" (BR-CP6).
- **Two error-envelope shapes across the API:** every route in this flow
  answers `{"detail": "…"}` on error, while the CAD/aeroplane routers answer
  `{"error": {"code","message","details"}}`. A client (especially an MCP-agent
  client written against a single error shape) must special-case this module.
- **`ConflictError` has no mapping on the plan routers** — no path raises it
  today, but if one ever does, it will surface as a **500**, not a 409.
- **Process isolation is unclear for plan execution.** The synchronous
  `/execute` route runs `create_shape()` on the FastAPI request thread and the
  streaming route runs it on a plain Python thread — both drive the same
  OCCT/CadQuery stack that `cad-generation`'s module docstring says must never
  run outside a spawned worker process (ADR 0005, because a hung OCCT call
  blocks indefinitely). Whether this is an accepted trade-off or a latent
  outage risk is unresolved (BR-CP11).
