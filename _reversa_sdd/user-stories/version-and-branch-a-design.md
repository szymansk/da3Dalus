# Version and Branch a Design

> **Personas:** RC/UAV designer, Hobbyist, MCP-agent client
> **Modules:** `versioning` (+ `aeroplane-core`, `wing-design`, `ai-copilot`)
> **Primary surface:** `/aeroplanes/{id}/snapshot`, `/aeroplanes/{id}/branch`,
> `/branches/{id}`, `/branches/{id}/adopt`, `/aeroplanes/{id}/restore`,
> `/lineages/{root_id}/tree`, `/aeroplanes/compare`, `/aeroplanes?heads_only=`,
> `/aeroplanes/{id}/design-versions*`

## Context

An aircraft design in da3Dalus is versioned the way Git versions a repository,
except every "commit" is a complete, queryable `aeroplanes` row rather than a
diff or a JSON blob (ADR 0006). A designer takes a snapshot before a risky
change, forks a branch to explore an alternative wing, compares two branches
side by side, and eventually adopts the branch that won onto `main` — or
throws it away. This flow is exercised from the Versions panel in the
frontend, and identically from an external MCP-agent client driving the same
REST surface. Every route in this flow is registered by
`app/api/v2/endpoints/versioning.py`, which is mounted **before** the
aeroplane router precisely so its static path `/aeroplanes/compare` is matched
ahead of the parametrised `/aeroplanes/{aeroplane_id}` (gh-914) — without that
ordering, `compare?a=&b=` would 422 as an invalid UUID.

**A critical id contract to hold in mind throughout this flow:** every route
below — snapshot, branch, adopt, restore, rename, discard, tree — takes the
**integer primary key** of a node or branch in its path, not the public UUID
used everywhere else in the v2 API (aeroplane creation, wing edits, analysis).
A client that reuses a UUID here gets a 404, not a type error, because FastAPI
resolves the path parameter as `int` before the handler ever runs a lookup.

## US-VBD-01 — Snapshot before a risky edit

**As an** RC/UAV designer, **I want** to freeze the current state of my design
before making a structural change, **so that** I have a guaranteed recovery
point if the change goes wrong.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/snapshot` | Freeze the head node into an immutable predecessor |

**Acceptance criteria**

- **AC-1 — Snapshot inserted behind the head**
  - **Given** a mutable head aeroplane with integer PK `H` and an optional predecessor `P`
  - **When** I `POST /aeroplanes/{H}/snapshot` with `{"label": "Before spar insert", "note": "trying a thicker spar"}`
  - **Then** the response is **201** with a `VersionNode` for the **new snapshot** `S` (not for `H`)
  - **And** `S.is_immutable` is `true`, `S.predecessor_id` is `P` (the head's old predecessor)
  - **And** the head `H` keeps its own id and UUID, and its `predecessor_id` now points at `S`
  - **And** `S.created_by` is hard-coded `"human"` regardless of who actually triggered the call
- **AC-2 — Refuse to snapshot an already-frozen node**
  - **Given** a node that is already `is_immutable = true`
  - **When** I `POST /aeroplanes/{that_id}/snapshot`
  - **Then** the response is **422** with `{"detail": "..."}` (this router uses FastAPI's bare detail body, not the `{"error":{code,message,details}}` envelope used elsewhere in v2)
- **AC-3 — Provenance is carried but write-only**
  - **Given** a copilot turn whose `copilot_messages.id` is `42`
  - **When** I snapshot with `"provenance_message_id": 42`
  - **Then** the returned `VersionNode.provenance_message_id` is `42`
  - **And** no other endpoint in the system ever reads that field back — it is accepted, stored, and returned, and nothing else consumes it (🔴 GAP)

**Confidence:** 🟢 CONFIRMED

## US-VBD-02 — Fork a branch to try an alternative

**As a** hobbyist, **I want** to fork my design into a separate branch before
trying a wild idea, **so that** I can experiment freely without risking the
design I already like.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/branch` | Fork a mutable head from any node (live head or frozen snapshot) |

**Acceptance criteria**

- **AC-1 — Forking creates a new mutable head and branch row**
  - **Given** any node `N` (mutable head or immutable snapshot) with integer PK `N`
  - **When** I `POST /aeroplanes/{N}/branch` with `{"name": "winglet-experiment", "created_by": "human"}`
  - **Then** the response is **201** `BranchOut{id, root_id, head_id, name, is_main: false, created_by, created_at}`
  - **And** a new mutable aeroplane is cloned with `predecessor_id = N` and `branch_id` back-filled to the new branch's id
  - **And** the source node `N` is untouched
- **AC-2 — Forking from a snapshot works identically to forking from a head**
  - **Given** an immutable snapshot node `S`
  - **When** I `POST /aeroplanes/{S}/branch`
  - **Then** the response is **201**, exactly as when forking a mutable head — the source's immutability is irrelevant to `create_branch`
- **AC-3 — Duplicate branch names are allowed at creation time**
  - **Given** a lineage that already has a branch named `"experiment"`
  - **When** I create another branch named `"experiment"` in the same lineage
  - **Then** the response is still **201** — there is **no** collision check on create; uniqueness is only enforced later by `PATCH` (BR-42)
- **AC-4 — Unknown source node**
  - **Given** an integer PK that does not exist
  - **When** I `POST /aeroplanes/{999999}/branch`
  - **Then** the response is **404**

**Confidence:** 🟢 CONFIRMED

## US-VBD-03 — Adopt a branch onto main

**As an** RC/UAV designer, **I want** to promote my experimental branch to be
the design's new main line, **so that** the rest of the team (or my own
future self) treats it as the canonical design going forward.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/branches/{branch_id}/adopt` | Promote a branch to `main`, demoting the previous main |

**Acceptance criteria**

- **AC-1 — Adoption demotes the old main atomically**
  - **Given** a lineage with main branch `M` (`is_main=true`) and feature branch `F` (`is_main=false`)
  - **When** I `POST /branches/{F}/adopt`
  - **Then** the response is **200** `BranchOut` for `F` with `is_main: true`
  - **And** `M.is_main` is now `false` — the service demotes `M` **first** and flushes before promoting `F`, so the database's partial unique index `uq_branches_one_main_per_root` never sees two `is_main=true` rows for the same lineage at once
  - **And** `M` itself still exists — the old main branch is kept, not deleted
- **AC-2 — Adopting an already-main branch is a conflict**
  - **Given** a branch that is already `is_main = true`
  - **When** I `POST /branches/{that_id}/adopt`
  - **Then** the response is **409** `{"detail": "..."}`
- **AC-3 — Unknown branch**
  - **When** I `POST /branches/{999999}/adopt`
  - **Then** the response is **404**

**Confidence:** 🟢 CONFIRMED

## US-VBD-04 — Rename or discard a branch

**As a** hobbyist, **I want** to give my branches meaningful names and delete
the ones I no longer need, **so that** my Versions panel stays readable.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| PATCH | `/branches/{branch_id}` | Rename a branch, uniqueness enforced per lineage |
| DELETE | `/branches/{branch_id}` | Discard a branch and its exclusive nodes |

**Acceptance criteria**

- **AC-1 — Rename succeeds and strips whitespace**
  - **Given** a branch named `"experiment"`
  - **When** I `PATCH /branches/{id}` with `{"name": "  winglet-v2  "}`
  - **Then** the response is **200** `BranchOut` with `name: "winglet-v2"`
- **AC-2 — Rename collision within the same lineage**
  - **Given** branches `"a"` and `"b"` in one lineage
  - **When** I `PATCH` branch `"b"` to `{"name": "a"}`
  - **Then** the response is **409** — uniqueness is application-level only, there is no DB constraint (BR-42)
- **AC-3 — Rename to an empty name (after stripping)**
  - **When** I `PATCH` a branch to `{"name": "   "}`
  - **Then** the response is **422**
- **AC-4 — Discard succeeds and nulls inbound predecessor links**
  - **Given** node `X` on branch `A` whose `predecessor_id` points at node `Y` on branch `B`
  - **When** I `DELETE /branches/{B}`
  - **Then** the response is **204 No Content**
  - **And** node `X` still exists, with `predecessor_id` now `null` — the branch row is deleted **before** its nodes, in the exact order: null inbound predecessors → delete the branch → delete each node (letting the ORM cascade remove its owned subgraph); the ordering is load-bearing on SQLite because its FKs are not deferrable (BR-VR9)
- **AC-5 — The main branch cannot be discarded**
  - **When** I `DELETE /branches/{main_branch_id}`
  - **Then** the response is **409**
- **AC-6 — The only branch of a lineage cannot be discarded**
  - **Given** a lineage with a single branch
  - **When** I `DELETE` it
  - **Then** the response is **409**

**Confidence:** 🟢 CONFIRMED

## US-VBD-05 — Restore an editable copy from a frozen snapshot

**As an** RC/UAV designer, **I want** to bring back an editable copy of a
design I froze weeks ago, **so that** I can continue iterating on that exact
historical state instead of the current main line.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{snapshot_id}/restore` | Fork a mutable branch from an immutable snapshot |

**Acceptance criteria**

- **AC-1 — Restore from an immutable snapshot succeeds with a default name**
  - **Given** an immutable snapshot node labelled `"before spar"`
  - **When** I `POST /aeroplanes/{snapshot_id}/restore` with no `name` in the body
  - **Then** the response is **201** `BranchOut` with `name: "restore/before spar"`
  - **And** functionally this is identical to `create_branch` from that snapshot, with the added immutability requirement
- **AC-2 — Restore falls back to the node id when the snapshot has no label**
  - **Given** an immutable snapshot with no `version_label`
  - **When** I restore it without a `name`
  - **Then** the new branch is named `"restore/<snapshot_id>"`
- **AC-3 — Restore requires an immutable source**
  - **Given** a mutable head
  - **When** I `POST /aeroplanes/{that_head_id}/restore`
  - **Then** the response is **422** — this is the mirror rule of snapshot's immutability guard: restoring from a live head is just `create_branch`, so `restore` refuses it to force the caller to use the right verb

**Confidence:** 🟢 CONFIRMED

## US-VBD-06 — See the whole version history and compare two points

**As an** RC/UAV designer, **I want** to see every branch and snapshot in my
design's lineage as a graph, and compare two of them side by side, **so
that** I can decide which one to adopt.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/lineages/{root_id}/tree` | Read every node and branch of a lineage, with a computed `is_head` flag |
| GET | `/aeroplanes/compare?a=&b=` | Return both nodes' metrics payloads for client-side comparison |
| GET | `/aeroplanes?heads_only=true` | List only branch-head aeroplanes (hide immutable snapshots), the default aeroplane picker view |

**Acceptance criteria**

- **AC-1 — The lineage tree lists nodes and branches with a head flag**
  - **Given** a lineage whose root has integer PK `R`
  - **When** I `GET /lineages/{R}/tree`
  - **Then** the response is **200** `TreeOut{root_id: R, nodes: TreeNodeOut[], branches: BranchOut[]}`
  - **And** every node that is some branch's `head_id` has `is_head: true` on its `TreeNodeOut`
  - **And** nodes are selected by `id == R OR root_id == R`, ordered by `id`
- **AC-2 — A node with a NULL root_id is invisible in the tree (known gap)**
  - **Given** a node whose `root_id` column is `NULL` (a data anomaly, e.g. from an incomplete migration path)
  - **When** I `GET /lineages/{R}/tree`
  - **Then** that node does not appear in `nodes[]` even though the row exists (🔴 GAP, BR-VR11)
- **AC-3 — Compare returns two raw metrics payloads, no server-side diff**
  - **Given** two node ids `a` and `b` (integer PKs, not necessarily in the same lineage)
  - **When** I `GET /aeroplanes/compare?a={a}&b={b}`
  - **Then** the response is **200** `CompareOut{node_a, node_b, metrics_a, metrics_b}`
  - **And** `metrics_a`/`metrics_b` are the same free-form `_metrics_payload` dict the copilot's `get_design_snapshot` tool uses: `id`, `uuid`, `name`, `total_mass_kg`, `wing_count`, `wing_names`, `wings: [{name, n_xsecs}]`, `fuselage_count`, and (when stability results exist) `stability: {static_margin_pct, is_statically_stable, neutral_point_x, mac}`
  - **And** no structural diff is computed server-side — that responsibility was retired along with `design_versions` (BR-VR10) — the client must diff the two payloads itself
- **AC-4 — Compare 404s when either node is missing**
  - **When** I `GET /aeroplanes/compare?a=999999&b=1`
  - **Then** the response is **404**
- **AC-5 — `heads_only` hides immutable snapshots from the picker**
  - **Given** a lineage with one mutable head and three immutable snapshots behind it
  - **When** I `GET /aeroplanes?heads_only=true` (the default)
  - **Then** the snapshots do not appear in the list — only branch heads, plus any legacy `branch_id IS NULL` rows, enriched with `branch_name` and `is_main_branch`
  - **When** I `GET /aeroplanes?heads_only=false`
  - **Then** every row, including the three snapshots, is returned

**Confidence:** 🟢 CONFIRMED

## US-VBD-07 — MCP-agent client drives branching the same way a human does

**As an** MCP-agent client, **I want** to snapshot, branch, and compare an
aircraft design through the same REST semantics a human designer uses,
**so that** I can automate exploratory design iterations without a browser.

**Endpoints exercised**

Same table as US-VBD-01…06 — the versioning router is plain REST with no
MCP-specific wrapper.

**Acceptance criteria**

- **AC-1 — Versioning is not exposed as an MCP tool**
  - **Given** the 76-tool MCP surface mounted at `/mcp`
  - **When** an agent enumerates the available tools
  - **Then** none of `snapshot_aeroplane`, `create_branch`, `adopt_branch`, `restore_snapshot`, `rename_branch`, `discard_branch`, `get_lineage_tree`, or `compare_aeroplane_nodes` appear — versioning, copilot history/stream, and several other module families are explicitly absent from the 76-tool inventory (only ~76 of ~230 v2 routes have an MCP tool)
  - **And** an agent that needs branch/snapshot semantics must call the plain REST endpoints directly (outside `/mcp`), reusing its own HTTP client rather than the MCP tool-call protocol
- **AC-2 — An agent must still use the integer PK, not the UUID, on these routes**
  - **Given** an agent that just created an aeroplane via the `create_aeroplane` MCP tool and received a UUID
  - **When** it calls `POST /aeroplanes/{uuid}/snapshot` using that UUID directly
  - **Then** the response is **404** — the path parameter is typed `int`, and FastAPI's integer coercion fails against a UUID string before any lookup runs; the agent must first resolve the integer PK (e.g. via the lineage tree or a heads-only list) before calling any versioning route

**Confidence:** 🟡 INFERRED — the 404-on-UUID behavior follows directly from
FastAPI's path-parameter typing (`aeroplane_id: int`) documented in the
contract, but no test in the reviewed evidence exercises this exact failure
mode explicitly.

## US-VBD-08 — Read (and reject) the retired `design-versions` surface

**As an** RC/UAV designer, **I want** to know what happens if I hit the old
version-history endpoints that predate branching, **so that** I don't build
against a URL that will never work.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/design-versions` | Retired — always fails |
| POST | `/aeroplanes/{aeroplane_id}/design-versions` | Retired — always fails |
| GET | `/aeroplanes/{aeroplane_id}/design-versions/{version_id}` | Retired — always fails |
| DELETE | `/aeroplanes/{aeroplane_id}/design-versions/{version_id}` | Retired — always fails |
| GET | `/aeroplanes/{aeroplane_id}/design-versions/{version_a}/diff/{version_b}` | Retired — always fails |

**Acceptance criteria**

- **AC-1 — Every route in the family 404s regardless of input**
  - **Given** any aeroplane id and any version id, valid or not
  - **When** I call any of the five `design-versions` routes
  - **Then** the response is **404** — every one calls a `design_version_service` stub that unconditionally raises `NotFoundError`; the underlying `design_versions` table was dropped by the gh-903 migration, but the five routes are still registered in `app/api/v2/endpoints/aeroplane/__init__.py`
  - **And** the response is a plausible-looking 404 rather than a 410 Gone or 501 Not Implemented, so a client cannot distinguish "this aircraft has no such version" from "this entire route family is dead" (🔴 GAP)
- **AC-2 — The replacement is the `/lineages` + `/branches` surface**
  - **Given** the same versioning need (list versions, read one, diff two, delete one)
  - **When** a client wants an equivalent capability
  - **Then** it should use `GET /lineages/{root_id}/tree` (list), a `VersionNode` read via the tree or compare response (read one), `GET /aeroplanes/compare?a=&b=` (compare two — client-side diff only), and `DELETE /branches/{id}` (discard, at branch granularity, not single-version granularity)

**Confidence:** 🟢 CONFIRMED

## Open questions 🔴

- **`provenance_message_id` is accepted and stored on snapshots but read by
  nothing.** No endpoint surfaces "which copilot turn produced this snapshot"
  back to a user — the accountability trail described in the copilot-adopted
  flow is only half-wired on the versioning side.
- **`created_by` has three vocabularies in practice** (`"human"` hard-coded by
  `snapshot()`, `"human"`/`"ai"` documented by `BranchRequest`, `"copilot"`
  actually written by the copilot's `get_or_open_proposal`) with no enum
  enforcing any of them. A UI or agent that filters branches on `created_by ==
  "ai"` will silently miss every copilot-authored branch.
- **No retention or pruning policy exists for snapshots.** Every snapshot is a
  full row-copy of the entire design subgraph (17 cloned tables), taken
  automatically before every destructive spar commit, with no size accounting
  or expiry — a design that iterates heavily will accumulate unbounded rows.
- **`GET /aeroplanes/compare` performs no server-side diff.** Two full metrics
  payloads are returned and the caller (browser or MCP-agent) must compute the
  comparison itself; there is no structural per-field diff endpoint since
  `design_versions/diff` was retired.
