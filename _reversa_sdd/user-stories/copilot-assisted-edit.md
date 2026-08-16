# Copilot-Assisted Edit

> **Personas:** AI-copilot user, Hobbyist, RC/UAV designer, MCP-agent client
> **Modules:** `ai-copilot` (+ `versioning`, `wing-design`, `aero-analysis`, `mcp-server`)
> **Primary surface:** `/aeroplanes/{id}/copilot/stream` (SSE),
> `/aeroplanes/{id}/copilot-history` (+ `/{message_id}`)

## Context

The in-app copilot is a streaming, tool-calling chat assistant scoped to one
aeroplane at a time. It answers design questions with numbers computed in
Python (never narrated by the model, ADR 0004), and — since Slice 2 — it can
propose geometry and assumption edits. Its entire write surface is a single
disposable `copilot-proposal` branch: the copilot can apply edits, read them
back, and discard them, but it has **no tool that adopts a branch onto
main** (ADR 0007). Promotion is a human-only action performed in the Versions
panel, through the plain `versioning` REST surface described in
`version-and-branch-a-design.md`. This flow covers a full turn of that
conversation, the history that backs it, and the parallel path an external
MCP-agent client takes when it wants the same domain capability without a
browser.

## US-CAE-01 — Ask the copilot a design question and get a streamed answer

**As an** AI-copilot user (hobbyist), **I want** to ask a plain-language
question about my aircraft's performance, **so that** I get an explained
answer with real numbers instead of having to read charts myself.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/copilot/stream` | Stream one turn of the conversation over SSE |

**Acceptance criteria**

- **AC-1 — A plain advisory turn streams text and completes**
  - **Given** an aeroplane addressed by UUID with an existing copilot history
  - **When** I `POST /aeroplanes/{uuid}/copilot/stream` with `{"message": "What's my glide ratio?", "context_hint": "Active tab: Analysis · Aircraft: MyGlider"}`
  - **Then** the response is **200** with `Content-Type: text/event-stream`, `Cache-Control: no-cache`, `X-Accel-Buffering: no`
  - **And** the user message is persisted **before** the stream opens (so an unknown aeroplane 404s before a single SSE byte is written)
  - **And** I receive one or more `event: token` frames (`data: {"text": "..."}`), each formatted as `event: <type>\ndata: <compact json>\n\n`
  - **And** the final event is `event: done` with `data: {"status": "ok"}`
  - **And** the assistant's full reply is persisted as a new history row after the `done` event, inside its own try/except so a persistence failure never breaks the stream
- **AC-2 — Unknown aeroplane fails before any SSE byte**
  - **Given** a UUID that does not exist
  - **When** I `POST /aeroplanes/{unknown-uuid}/copilot/stream`
  - **Then** the response is a plain **404** (not an SSE stream at all) — the ordering guarantee is that the user message write and the integer-PK resolution both happen before `StreamingResponse` is returned
- **AC-3 — A hub failure never leaks the API key**
  - **Given** the model-provider hub raises an authentication error whose message happens to contain the configured API key
  - **When** the turn runs
  - **Then** the client sees `event: error` with `data: {"message": "..."}`, and that message contains neither the literal key nor a raw provider error — it is replaced by a category message such as `"<Type>: authentication or configuration error"`, or by the flat literal `"Internal server error"` from the endpoint's own catch-all
- **AC-4 — A very long tool-calling turn is truncated, not silently cut**
  - **Given** a question that causes the model to keep requesting tools every iteration
  - **When** the turn runs past `MAX_LOOP_ITERATIONS = 6`
  - **Then** the final event is `event: done` with `data: {"status": "ok", "truncated": true}`, so the client can tell the user the turn hit its cap rather than assuming it finished cleanly

**Confidence:** 🟢 CONFIRMED

## US-CAE-02 — Watch the copilot call tools mid-turn

**As an** AI-copilot user (RC/UAV designer), **I want** to see which tool the
copilot is running and what it got back, **so that** I can trust the numbers
it quotes me are computed, not guessed.

**Endpoints exercised**

Same as US-CAE-01 (`POST /aeroplanes/{aeroplane_id}/copilot/stream`).

**Acceptance criteria**

- **AC-1 — Tool call and tool result events are both emitted**
  - **Given** the model decides to call `run_analysis` to answer a performance question
  - **When** the turn runs
  - **Then** an `event: tool_call` frame carries `{"name": "run_analysis", "args": {"kind": "polar"}}` before the tool executes
  - **And** an `event: tool_result` frame carries `{"name": "run_analysis", "summary": {...}}` with the **full** tool return value — not a truncated summary despite the field name
  - **And** the persisted assistant history row stores both `tool_calls` and `tool_results` together as one row (gh-922), which is what lets the next turn's history replay reconstruct valid interleaved `tool` messages instead of 400ing at the hub on an orphaned tool_use
- **AC-2 — A tool exception degrades the turn, never ends it**
  - **Given** a tool call whose underlying service raises
  - **When** the turn runs
  - **Then** the tool result is `{"error": "<message>"}` — never an unhandled exception — and the turn still ends with `event: done`
- **AC-3 — The induced/parasite drag split is always computed, never narrated**
  - **Given** a `run_analysis(kind="polar")` call with valid `CL`, `CD_total`, `AR`, `e`
  - **When** the tool runs
  - **Then** `drag_breakdown.cd_induced = CL² / (π·AR·e)` and `drag_breakdown.cd_parasite = CD_total − cd_induced`, computed in Python (ADR 0004) — the model is never asked to do this arithmetic
- **AC-4 — A physically impossible split is reported as a note, not silently fixed**
  - **Given** inputs where the computed induced drag would exceed the total drag
  - **When** `run_analysis(kind="polar")` runs
  - **Then** `drag_breakdown` carries a `note` field plus the raw inputs, and **no** `cd_induced`/`cd_parasite` split — the system never invents a physically impossible-but-plausible-looking number

**Confidence:** 🟢 CONFIRMED

## US-CAE-03 — The copilot proposes a wing edit; the live design is untouched

**As an** AI-copilot user (hobbyist), **I want** to ask the copilot to
"increase the wingspan by 200mm", **so that** I can see the effect before
deciding whether to keep it — without any risk to my current design.

**Endpoints exercised**

Same as US-CAE-01. The write path is the copilot's internal `apply_design_edits`
tool, invoked by the model during the turn — there is no separate REST route
for it; it only exists inside the tool-calling loop of `/copilot/stream`.

**Acceptance criteria**

- **AC-1 — The first edit opens a dedicated proposal branch**
  - **Given** an aeroplane with no open copilot proposal
  - **When** the model calls `apply_design_edits` with a valid `SetSegment` op (e.g. `{"type": "SetSegment", "wing": "Main Wing", "seg_index": 0, "length_mm": 700}`)
  - **Then** a new branch named `"copilot-proposal"` is created with `created_by: "copilot"`, `is_main: false`, cloned from the **live** head
  - **And** the live head's own geometry is byte-identical after the call — the edit is applied only to the new branch's head
- **AC-2 — A second edit in the same conversation reuses the same proposal**
  - **Given** an already-open proposal branch for this aeroplane
  - **When** the model calls `apply_design_edits` again (e.g. to also raise `SetAssumption(param="target_static_margin", value=0.12)`)
  - **Then** the returned `branch_id` is the **same** as before — `get_or_open_proposal` reuses the newest branch matching `root_id, is_main=false, created_by='copilot', name LIKE 'copilot-proposal%'` rather than opening a second one
- **AC-3 — A bad op is rejected, the rest of the batch still applies**
  - **Given** two ops in one call, one of which names a wing that does not exist
  - **When** `apply_design_edits` runs
  - **Then** the response includes `applied: ["SetSegment on Main Wing"]` and `rejected: [{"op": {...}, "error": "..."}]` for the bad one — the batch is never aborted by a single invalid op
- **AC-4 — Read tools follow the open proposal, not the live design**
  - **Given** an open proposal whose wingspan differs from the live aeroplane
  - **When** the model calls `get_design_snapshot` or `get_wing_geometry` later in the same turn
  - **Then** it reads the **proposal's** branch head (`branch.head_id`), so the copilot can verify its own edit before reporting back to the user
  - **And** `get_version_tree` still returns the **live** lineage, unaffected by the open proposal — it is one of the two tools that never retarget
- **AC-5 — There is no tool that adopts the proposal**
  - **Given** the copilot's full 6-tool registry (`get_design_snapshot`, `get_wing_geometry`, `run_analysis`, `get_version_tree`, `apply_design_edits`, `discard_proposal`)
  - **When** the user asks the copilot (in chat) to "make this permanent" or "adopt this"
  - **Then** no tool call can promote the branch — the model can only tell the user to go adopt it in the UI; adoption is exclusively `POST /branches/{branch_id}/adopt` on the plain `versioning` surface, called by a human, never by the copilot (ADR 0007)

**Confidence:** 🟢 CONFIRMED

## US-CAE-04 — Human reviews the copilot's proposal and adopts or discards it

**As an** RC/UAV designer, **I want** to review the copilot's proposed edit in
the Versions panel and either keep it as my new main design or throw it
away, **so that** the copilot never has the final say on my aircraft.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/branches/{branch_id}/adopt` | (Human, via Versions panel) promote the copilot's proposal branch to main |
| DELETE | `/branches/{branch_id}` | (Human, via Versions panel) discard the proposal branch entirely |

*(Both routes belong to `versioning`, not `ai-copilot` — cross-referenced here
because this is the human half of ADR 0007's propose/adopt contract; full
acceptance criteria for these two routes are in
`version-and-branch-a-design.md` US-VBD-03 and US-VBD-04.)*

**Acceptance criteria**

- **AC-1 — Adopting the copilot's proposal is indistinguishable from adopting any other branch**
  - **Given** a `"copilot-proposal"` branch with `created_by: "copilot"` that the copilot's `apply_design_edits` opened
  - **When** a human clicks "Adopt" in the Versions panel, issuing `POST /branches/{branch_id}/adopt`
  - **Then** the response is **200**, the proposal branch becomes `is_main: true`, and the previous main is demoted — the exact same demote-then-flush mechanics as any other branch adoption (BR-VR7); there is no special-cased copilot adoption path
- **AC-2 — Discarding the proposal removes it via `discard_proposal`, not just `DELETE /branches`**
  - **Given** an open copilot proposal the user does not want
  - **When** the model calls `discard_proposal()` (e.g. because the user typed "never mind, undo that" in chat)
  - **Then** the response is `{"discarded": true}`
  - **And** internally this is `flush()` → `expunge_all()` → re-resolve → `discard_branch` — the explicit `expunge_all()` is required, or the cascade delete raises `InvalidRequestError: Can't attach instance <WingXSecSpareModel …>` from stale spare instances left in the session
  - **When** `discard_proposal()` is called again with nothing open
  - **Then** the response is `{"discarded": false}` (not an error)
- **AC-3 — A UI that filters branches on `created_by == "ai"` misses every copilot branch**
  - **Given** a lineage containing a copilot-authored proposal branch
  - **When** a client (browser or MCP-agent) filters `GET /lineages/{root_id}/tree` branches on `created_by == "ai"` (the value the `BranchRequest` schema documents as the AI provenance value)
  - **Then** the copilot's branch is silently excluded from that filter, because `get_or_open_proposal` actually writes `created_by = "copilot"`, a third vocabulary value never reconciled with the documented `'human' | 'ai'` pair (🔴 GAP)

**Confidence:** 🟢 CONFIRMED

## US-CAE-05 — Read, append to, and clear the conversation history

**As an** AI-copilot user, **I want** my chat with the copilot to persist
across page reloads, and to be able to delete a message or clear the whole
thread, **so that** I can manage the conversation the same way I'd manage any
chat history.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| GET | `/aeroplanes/{aeroplane_id}/copilot-history` | Read the full ordered thread |
| POST | `/aeroplanes/{aeroplane_id}/copilot-history` | Append one message (used by the client before opening a stream, or to inject system context) |
| DELETE | `/aeroplanes/{aeroplane_id}/copilot-history/{message_id}` | Delete a single message |
| DELETE | `/aeroplanes/{aeroplane_id}/copilot-history` | Clear the entire thread |

**Acceptance criteria**

- **AC-1 — History reads back in order**
  - **Given** a conversation of five prior turns
  - **When** I `GET /aeroplanes/{uuid}/copilot-history`
  - **Then** the response is **200** `CopilotHistory{messages: [...]}`, ordered by `sort_index`, each a `CopilotMessageRead{id, role, content, tool_calls, tool_results, parent_id, created_at}`
- **AC-2 — Appending assigns the next sort index**
  - **Given** a thread with 4 existing messages
  - **When** I `POST /aeroplanes/{uuid}/copilot-history` with `{"role": "user", "content": "..."}`
  - **Then** the response is **201** `CopilotMessageRead`, and its `sort_index` is assigned as `COUNT(*)` over the aeroplane's messages at write time
  - **And** (known limitation) two concurrent appends, or an append issued right after a delete, can produce duplicate or reused `sort_index` values — there is no collision-safe sequence (🔴 GAP)
- **AC-3 — Deleting a single message succeeds and does not renumber the rest**
  - **Given** message `id=17` in a thread
  - **When** I `DELETE /aeroplanes/{uuid}/copilot-history/17`
  - **Then** the response is **204 No Content**
  - **And** the remaining messages keep their original `sort_index` values — the next append can therefore reuse an index already in use (🔴 GAP)
- **AC-4 — Clearing the whole thread removes every message**
  - **When** I `DELETE /aeroplanes/{uuid}/copilot-history`
  - **Then** the response is **204 No Content**, and a subsequent `GET` returns `{"messages": []}`
- **AC-5 — Unknown aeroplane on any history route**
  - **Given** a UUID that does not exist
  - **When** I call any of the four history routes against it
  - **Then** the response is **404** `{"detail": "..."}` (this router's own `_raise_http`/`_call` pair, not the global `{"error":{code,message,details}}` envelope)

**Confidence:** 🟢 CONFIRMED

## US-CAE-06 — Branching or snapshotting an aircraft never copies its chat

**As an** RC/UAV designer, **I want** a branch or snapshot of my design to be
a clean design fork, **so that** my conversation history with the copilot
doesn't get duplicated across every version I create.

**Endpoints exercised**

| Method | Path | Purpose |
|---|---|---|
| POST | `/aeroplanes/{aeroplane_id}/snapshot` | (cross-module) confirms `copilot_messages` is excluded from the clone |
| POST | `/aeroplanes/{aeroplane_id}/branch` | (cross-module) same |

**Acceptance criteria**

- **AC-1 — `copilot_messages` is never cloned**
  - **Given** an aeroplane with an active copilot conversation
  - **When** I snapshot or branch it via the `versioning` routes
  - **Then** the new node exists with its own wings/xsecs/assumptions/etc. (the 17 cloned tables), but `GET /aeroplanes/{new_node}/copilot-history` returns an **empty** thread — `copilot_messages` is deliberately in `EXCLUDED_TABLES`, with the documented reason *"provenance captured via note + cursor"* rather than by copying the conversation itself

**Confidence:** 🟢 CONFIRMED

## US-CAE-07 — MCP-agent client drives the same domain operations without the copilot's chat loop

**As an** MCP-agent client, **I want** to accomplish the same kind of design
iteration the in-app copilot does — read the geometry, run an analysis,
change a wing, snapshot, branch — **so that** I can automate design work from
an external agent harness instead of the browser chat UI.

**Endpoints exercised**

The MCP tool surface at `/mcp` (76 tools, distinct registry from the
copilot's 6) — for example `get_aeroplane_by_id`, the wing/cross-section
tools, `analyze_alpha_sweep`, `run_stability`. **Not** exercised: the
copilot's `/copilot/stream`, `/copilot-history*`, or its 6-tool registry,
which is a completely separate mechanism sharing no code with `/mcp`
(confirmed in both contracts).

**Acceptance criteria**

- **AC-1 — The MCP surface has no copilot-equivalent conversational loop**
  - **Given** an MCP-agent client connected to `/mcp`
  - **When** it enumerates the 76 available tools
  - **Then** it finds direct data/action tools (wing CRUD, analysis, CAD export, operating points) but **no** streaming-turn tool, no `apply_design_edits`-style proposal-branch writer, and no history read/append/clear — those all belong exclusively to `ai-copilot`'s in-app surface and are not mounted at `/mcp`
  - **And** it must instead call the plain wing/analysis endpoints directly (through its own tool, e.g. `set_wing_segment`-equivalent) and manage its own before/after comparison — there is no server-side "propose, then let a human adopt" scaffold on the MCP path; every MCP write applies to the aeroplane it targets directly, subject to the caveat in AC-2
- **AC-2 — Known reliability gap: many MCP writes do not persist**
  - **Given** an MCP tool whose underlying service relies on `get_db()`'s commit (the same pattern REST endpoints use)
  - **When** the tool is called through `/mcp`'s `_call_endpoint` bridge, which opens a bare `SessionLocal()` with **no commit**
  - **Then** the tool returns what looks like a successful payload, but the session's `__exit__` calls `close()`, which **rolls back** the transaction — so the row the agent believes it just created or edited was never actually persisted (🔴 GAP, tracked as the top-severity defect in `mcp-server`'s contract; only tools whose service commits itself, e.g. `retrim_service`, actually persist through this path)
  - **And** an MCP-agent client relying on this surface to perform copilot-style iterative geometry edits should verify persistence with a subsequent read (e.g. re-fetch the aeroplane) rather than trusting the write tool's own response — because a successful-looking response and a silently-discarded write are indistinguishable from the tool result alone
- **AC-3 — No authentication gates either surface**
  - **Given** both `/copilot/stream` and `/mcp` are mounted with no application-level authentication (ADR 0016 — the ngrok/oauth2-proxy tunnel is the only boundary)
  - **When** an MCP-agent client or a browser reaches either endpoint through the tunnel
  - **Then** no login or token is required by the application itself; access control is entirely the deployment tunnel's responsibility, not this module's

**Confidence:** 🟢 CONFIRMED (MCP persistence gap and no-auth posture are both
explicitly documented in the `mcp-server` contract); 🟡 INFERRED that an
MCP-agent client would specifically want copilot-equivalent iterative editing
— the contracts confirm the capability gap but not a documented user
expectation for it.

## Open questions 🔴

- **The provenance link from an adopted branch back to the copilot turn that
  proposed it is designed but not wired.** `get_or_open_proposal` accepts a
  `message_id` parameter that no caller ever supplies, and `snapshot()`'s
  `provenance_message_id` field, once populated, is read by nothing. A user
  cannot currently answer "which chat message produced this branch?" from the
  API.
- **`created_by` has no enum and three real-world values** (`"human"`,
  `"ai"` as documented but apparently unused, `"copilot"` as actually
  written) — any consumer that branches logic on provenance needs to account
  for all three, not the two the schema documents.
- **A mid-stream client disconnect loses the assistant's turn.** The SSE
  generator is abandoned, the `done` branch never runs, and `get_db()`'s
  commit — which only happens after the response is fully consumed — never
  fires, so neither the assistant's reply nor any proposal-branch edit from
  that turn is guaranteed to persist.
- **The MCP write-persistence gap (US-CAE-07 AC-2) has no test coverage that
  would catch a regression or a fix** — the existing MCP test suite
  monkeypatches the bridge function wholesale rather than driving it through a
  real session.
