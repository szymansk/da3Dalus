# AI Copilot — Slice 1: Foundation (advisory) — Design Spec

**Epic:** #902 (AI Copilot) · **Slice:** 1 of N · **Date:** 2026-06-08 · **Status:** design approved
**Depends on:** #901 (Versioning — shipped; agentic slices later land changes on its branches)

## 1. Goal & scope

#902 is large (transport, RAG, agentic apply, code-exec sandbox, multi-agent, decisions-log). It is **decomposed into slices**, each with its own spec → plan → build. **This spec is Slice 1: a working ADVISORY copilot end-to-end** — the foundation that validates the transport + tool-calling loop against the (already-verified) LiteLLM ai-hub.

**In scope (Slice 1):**
- pydantic-settings config + `COPILOT_*` settings.
- `POST /aeroplanes/{id}/copilot/stream` SSE endpoint + a hand-rolled tool-calling loop against the hub (OpenAI SDK).
- A small curated tool facade: `get_design_snapshot`, `run_analysis` (fast: polar/stability), `get_version_tree`.
- System-prompt grounding (no RAG yet).
- `CopilotStrip` wired to stream + render the conversation (persistence already exists).

**Out of scope (later slices):** agentic `propose/apply` on branches (Slice 2), code-exec sandbox + `save_tool` library (Slice 3), RAG over a built knowledge corpus (Slice 4 — note: the skill vaults are NOT on disk, a corpus must be built), per-tab agents + supervisor (Slice 5), Design-Decisions log / shared memory (Slice 6).

## 2. Settled decisions
- **Advisory + `run_analysis`:** the copilot may read AND trigger fast analyses; it does NOT change the design in Slice 1.
- **Loop = OpenAI Python SDK + hand-rolled tool loop** (client `base_url`=hub, `api_key`=hub key; OpenAI-compatible — verified: auth + SSE streaming + tool-calls all pass). Light dep, full control for later slices.
- **Reply in the user's language** (German if the user writes German). English-only applies to UI chrome/code, not conversation.
- Conversation persistence is **already built** (`copilot_messages` model + `copilot_history_service` + REST). Reuse it.

## 3. Existing building blocks (reuse, don't rebuild)
- **Persistence:** `app/models/aeroplanemodel.py::CopilotMessageModel` (cols: aeroplane_id, sort_index, role, content, tool_calls JSON, tool_results JSON, parent_id, created_at); `app/services/copilot_history_service.py` (get/append/clear/delete); REST `GET/POST/DELETE /aeroplanes/{id}/copilot-history`.
- **SSE pattern:** `_sse_format(event,data)` + `StreamingResponse` (see openvsp_import / operating-points stream). Frontend consumer: `frontend/lib/sseStream.ts`.
- **Snapshot source:** `aeroplane_version_service._metrics_payload()` + `AeroplaneModel.assumption_computation_context` (what the Metrics Dashboard reads).
- **Analyses:** existing analysis/stability services (fast AeroBuildup polar + stability).
- **Version graph:** `aeroplane_version_service.list_tree()`.
- **Frontend shell:** `frontend/components/workbench/CopilotStrip.tsx` (collapsible, no wiring yet).

## 4. Design

### 4.1 Config
Upgrade `app/core/config.py` to **pydantic-settings** (`BaseSettings`, `env_file=.env`), keeping existing fields. Add:
- `COPILOT_API_KEY: SecretStr | None`
- `COPILOT_BASE_URL: str | None`
- `COPILOT_MODEL: str = "claude-sonnet-4-6"`
- `COPILOT_EMBEDDING_MODEL: str = "text-embedding-3-large"` (unused until Slice 4)
New dep: `openai` (Python SDK). Config is the single source — no scattered `os.getenv`.

### 4.2 Transport — `POST /aeroplanes/{aeroplane_id}/copilot/stream`
Body `{ "message": str }`. (Suffix `/copilot/stream` → no collision with `/aeroplanes/{aeroplane_id}`; cf. gh-914.) Flow:
1. `append_message(role="user", content=message)`.
2. Load history → build OpenAI `messages` (system prompt + thread).
3. Run `copilot_service.run_turn(...)` against the hub, streaming:
   - assistant text deltas → `event: token {text}`
   - on `tool_calls` → `event: tool_call {name, args}`; execute the tool **server-side**; `event: tool_result {name, summary}`; continue the loop.
   - **max-iterations guard** (e.g. 6) to prevent infinite tool loops.
4. Persist the final assistant message (+ tool_calls/tool_results) via `append_message`; `event: done`.
Hub/tool errors → `event: error {message}` (never leak the key). Returns `StreamingResponse(media_type="text/event-stream")`.

### 4.3 Tools — curated facade
New `app/services/copilot_tools.py` (NOT the 51-tool MCP surface). A registry of `{openai_schema, impl(db, aeroplane_id, **args) -> dict}`:
- **`get_design_snapshot()`** — full metrics payload (speeds/geometry/quality/balance/tail/powertrain) from the `_metrics_payload`/computation-context path. No args (uses the conversation's aeroplane_id).
- **`run_analysis(kind)`** — `kind ∈ {"polar","stability"}` (fast). Triggers via the existing service, awaits with a **timeout**, returns a concise summary (key numbers). Slow AVL/CAD/envelope are excluded in Slice 1 (or time-boxed → "still running, see Analysis tab").
- **`get_version_tree()`** — `list_tree()` for the lineage (branches/snapshots), read-only.
Rules: each tool returns a JSON-serializable dict; **one unit convention to the model** (SI/m, like the dashboard); numbers come only from services. The schemas use `Field(description=...)` so the model wields them well.

### 4.4 Grounding (system prompt, no RAG)
A curated system prompt: role (da3Dalus aircraft-design copilot, serves hobbyists AND pros), advisory-only behaviour for Slice 1, **hard anti-hallucination** (always pull numbers from tools; never invent; cite the tool), a SHORT curated rule set (SM target bands by mission, V_H bands, Scholz/Sadraey for sizing, Anderson for "why", RC rules for model aircraft only) as a **stopgap until Slice-4 RAG**, SI units, reply in the user's language. A 1-line context hint (active tab + aircraft name/mission) is injected.

### 4.5 Frontend — `CopilotStrip` + `useCopilot`
- New hook `useCopilot(aeroplaneId)`: history via SWR (`GET …/copilot-history`) + `sendMessage` (POST `/copilot/stream`, consume SSE via the `lib/sseStream.ts` pattern) + streaming state.
- Wire `CopilotStrip`: render the thread; on send, stream assistant tokens live; show tool-call **status chips** ("reading design snapshot…", "running polar…") from `tool_call`/`tool_result`; finalize on `done`; show `error` inline. No aeroplane selected → disabled placeholder. UI chrome English; message content in the user's language.

### 4.6 Testing
- **Backend (hub MOCKED — no real API call in CI):** `copilot_service` loop (tool-calls executed, results + final message persisted, max-iter guard); `copilot_tools` (shapes, `run_analysis` timeout); HTTP `/copilot/stream` via TestClient with a mocked hub → asserts SSE `token`/`tool_call`/`done` events + history persisted; pydantic-settings loads `COPILOT_*`.
- **Frontend (vitest):** `useCopilot` (fetch/SSE mocked) + `CopilotStrip` (history render, streaming tokens, tool chips, error).
- The real-hub connectivity check stays a manual script (needs the key).

## 5. Sub-tickets (cut under #902)
1. **Config + deps** — pydantic-settings upgrade + `COPILOT_*` + `openai` dep (+ poetry.lock). Test: settings load.
2. **Tool facade** — `copilot_tools.py` (get_design_snapshot, run_analysis[polar/stability,timeout], get_version_tree) + unit tests.
3. **copilot_service loop + `/copilot/stream` SSE endpoint + system prompt** — the agent loop (OpenAI SDK), tool execution, persistence, max-iter guard; HTTP test with a mocked hub.
4. **Frontend** — `useCopilot` hook + `CopilotStrip` wiring (history, streaming, tool chips, errors) + vitest.

## 6. Deferred (later #902 slices)
Agentic propose/apply on #901 branches; code-exec sandbox + global `save_tool` library; RAG (build the knowledge corpus first — skill vaults are NOT on disk); per-tab agents + supervisor; Design-Decisions log / shared memory; per-request model override; streaming tool-output (partial results).
