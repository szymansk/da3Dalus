# ai-copilot / copilot-turn-loop

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

One **turn** = one user message in, one persisted assistant message out, with up
to six streamed completions and any number of tool executions in between. This
use case owns the loop, the SSE wire format, the history-replay adapter and the
error sanitiser. 🟢

## Responsibilities

- Persist the user message, then stream the model's answer as SSE. 🟢
- Iterate at most `MAX_LOOP_ITERATIONS = 6` completions per turn. 🟢
- Execute tool calls **off the event loop** and feed the results back. 🟢
- Persist the whole turn as **one** assistant row carrying `tool_calls` and
  `tool_results`. 🟢
- Reconstruct protocol-valid `tool` messages when replaying that row. 🟢
- Guarantee the hub credential never reaches the browser. 🟢

## Business Rules

- **BR-CO3 — `MAX_LOOP_ITERATIONS = 6`.** 🟢 Exhausting the budget while the
  model still wants tools yields `done` with `truncated: true`.
- **BR-CO26 — Termination is decided by three cases, in this order.** 🟢
  | Condition | Action |
  |---|---|
  | `finish_reason == "stop"` | complete, break |
  | no tool-call chunks accumulated (any other `finish_reason`) | complete, break |
  | `finish_reason == "tool_calls"` | execute all calls, append results, continue |
- **BR-CO27 — Tool-call chunks are accumulated by `index`.** 🟢 The stream
  delivers `id`, `function.name` and `function.arguments` fragmented across
  deltas; the loop reassembles them per `index` before dispatch.
- **BR-CO4 — Dispatch is `asyncio.to_thread`.** 🟢 There is no running event
  loop inside the worker thread, which is exactly what lets a tool call
  `asyncio.run(...)` for the async AeroSandbox coroutine.
- **BR-46 — A tool exception becomes `{"error": str(exc)}`** and the loop
  continues. 🟢
- **BR-CO5 — A `json.JSONDecodeError` on the arguments string sets `args = {}`
  and the tool is still invoked.** 🟢 (behaviour) / 🟡 (`Q-CO-2`: must not proceed)
- **BR-49 — Replay must preserve tool-call pairing.** 🟢 (gh-922)
  A missing result is replaced by `{"error": "tool result unavailable"}` rather
  than dropped, because an orphaned `tool_use` makes the hub **400 on every turn
  after the first tool use**.
- **BR-48 — Two layers of secret protection.** 🟢 `_sanitize_error` (key
  redaction + category substitution) inside the service, and the endpoint's
  catch-all which emits the flat literal `"Internal server error"`.
- **BR-CO28 — The user message is persisted before the stream opens.** 🟢
  This is what makes "unknown aeroplane" a real **404** instead of an in-band
  error event.
- **BR-CO29 — Assistant persistence failure is non-fatal.** 🟢 It is wrapped in
  its own `try/except` that only `logger.error`s; the `done` event is still
  emitted.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Append the user message, mapping `NotFoundError` → 404 pre-stream | Must | 404 with **no** SSE body |
| RF-02 | Load the full history including that message | Must | The first turn's history has ≥ 1 message |
| RF-03 | Resolve the aeroplane's integer PK for the tools | Must | A missing row is a second 404 guard |
| RF-04 | Stream `text/event-stream` with `Cache-Control: no-cache` and `X-Accel-Buffering: no` | Must | Response headers match |
| RF-05 | Emit `token` per text delta | Must | Concatenated `token.text` equals the final text |
| RF-06 | Emit `tool_call` before and `tool_result` after each execution | Must | Both events carry `name` |
| RF-07 | Loop at most 6 times | Must | The 7th completion is never requested |
| RF-08 | Emit `done {status:"ok"}`, adding `truncated: true` only on cap exhaustion | Must | A single-completion turn has no `truncated` key |
| RF-09 | Persist one assistant row with `content`, `tool_calls`, `tool_results` | Must | Row present after `done` |
| RF-10 | Reconstruct interleaved `tool` messages on replay | Must | Every assistant `tool_call` is immediately followed by a matching `tool` message |
| RF-11 | Substitute a placeholder for a missing tool result | Must | `{"error": "tool result unavailable"}` |
| RF-12 | Redact the key and categorise auth/connection failures | Must | No `error` payload contains the key |
| RF-13 | Emit `"Internal server error"` for anything unhandled | Must | The traceback stays server-side (`logger.exception`) |
| RF-14 | Execute tools off the event loop | Must | A tool calling `asyncio.run` succeeds |
| RF-15 | Continue the loop after a tool failure | Must | The turn still reaches `done` |
| RF-16 | Interpolate `context_hint` into the system prompt | Should | The prompt contains the hint text |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Security | No client-visible payload may contain the configured key | `copilot_service.py:44`, `copilot_stream.py:181` | 🟢 |
| Performance | CPU-bound tool work never blocks the event loop | `asyncio.to_thread` dispatch | 🟢 |
| Reliability | A persistence failure never breaks an in-flight stream | `copilot_stream.py:140-152` | 🟢 |
| Interoperability | Replayed history is valid for both the OpenAI and Anthropic tool protocols | `_history_to_openai:396` | 🟢 |
| Availability | The request-scoped session is held for the entire turn; the commit happens only after the generator is consumed | `copilot_stream.py`, `db/session.py:55` | 🔴 |
| Observability | Only the endpoint catch-all logs; there is no per-turn metric, token count or latency record | — | 🔴 |

## Acceptance Criteria

```gherkin
Feature: One copilot turn

  Scenario: A plain answer
    Given a fake client that returns text and finish_reason "stop"
    When I POST a message to the stream endpoint
    Then I receive token events whose concatenation is the answer
    And the final event is done with status "ok" and no truncated flag
    And exactly one assistant message is persisted

  Scenario: A tool round-trip
    Given a fake client that requests get_design_snapshot then answers
    When the turn runs
    Then a tool_call event precedes a tool_result event
    And the persisted assistant row carries one tool_call and one tool_result
    And exactly two completions were requested

  Scenario: The iteration cap
    Given a fake client that requests a tool on every completion
    When the turn runs
    Then exactly 6 completions are requested
    And the done event carries truncated true

  Scenario: Unknown aeroplane
    When I POST to the stream endpoint with an unknown UUID
    Then the response status is 404
    And no event-stream body is produced

  Scenario: The key is never leaked
    Given the hub raises AuthenticationError containing the configured key
    When the turn runs
    Then the error event message is "AuthenticationError: authentication or configuration error"

  Scenario: An unexpected failure is opaque
    Given the generator raises a ValueError with an internal path in its message
    When the turn runs
    Then the error event message is exactly "Internal server error"
    And the traceback was logged server-side

  Scenario: A tool failure does not end the turn
    Given run_analysis raises RuntimeError("solver exploded")
    When the turn runs
    Then the tool_result summary is {"error": "solver exploded"}
    And the turn still reaches done

  Scenario: Replay keeps pairing
    Given a persisted assistant row with tool_call "call_1" and a matching result
    When a second turn replays the history
    Then the message list contains an assistant message with tool_calls
    And it is immediately followed by a tool message with tool_call_id "call_1"

  Scenario: Replay survives a missing result
    Given a persisted assistant row with tool_call "call_1" and no results
    When the history is replayed
    Then the tool message content is {"error": "tool result unavailable"}

  Scenario: Malformed arguments still invoke the tool
    Given the accumulated arguments string is "{\"kind\": "
    When the turn dispatches the call
    Then the tool is invoked with an empty argument dict
```

> The last scenario is a **characterisation test** of current behaviour, not desired
> behaviour.

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Pre-stream persistence + 404 (RF-01…RF-03) | Must | The only way a client can distinguish a bad id from a model failure |
| The loop with its cap (RF-07/RF-08) | Must | Unbounded tool looping is an open-ended hub bill |
| Off-loop dispatch (RF-14) | Must | Without it every solver tool deadlocks the server |
| Replay reconstruction (RF-10/RF-11) | Must | Without it multi-turn conversation is impossible |
| Two-layer sanitisation (RF-12/RF-13) | Must | The credential boundary |
| The SSE event set (RF-04…RF-06, RF-09) | Must | The UI contract |
| Continue-after-tool-failure (RF-15) | Must | The model's self-correction depends on it |
| `context_hint` interpolation (RF-16) | Should | Improves answers; the turn works without it |
| Heartbeat / keep-alive frames | **Won't** | 🟢 decided (`Q-CO-4`): rejected as hardening against a deployment this project does not have (ADR 0024) |
| Resumable or replayable streams | **Won't** | 🟢 decided (`Q-CO-4`); the assistant row is committed at `done`, which removes the loss that motivated this |
| Per-turn token/cost metrics | Won't | 🔴 not addressed by the interview; no consumer at single-user scale |

## Code Traceability

| File | Function | Coverage |
|---|---|---|
| `app/api/v2/endpoints/aeroplane/copilot_stream.py:53` | `_sse_format` | 🟢 |
| `…:83-119` | pre-stream persistence, history load, PK lookup | 🟢 |
| `…:121-181` | `_generate` — the event mapper + catch-all | 🟢 |
| `app/services/copilot_service.py:446` | `run_turn` | 🟢 |
| `…:602-612` | argument decode + `asyncio.to_thread` dispatch | 🟢 / 🟡 (`Q-CO-2`) |
| `…:396` | `_history_to_openai` | 🟢 |
| `…:44` | `_sanitize_error` | 🟢 |
| `…:366` | `_make_openai_client` | 🟢 |
| `app/schemas/copilot_history.py` | `CopilotMessageWrite/Read` | 🟢 |
