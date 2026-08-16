# ai-copilot / copilot-turn-loop — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).
> Every task cites the legacy file, a definition of done and a confidence
> marker.

## Prerequisites

- [ ] `copilot_history_service` (`append_message`, `get_history`).
- [ ] `copilot_tools.list_schemas()` and `.execute(name, db, aeroplane_id,
      **kwargs)`.
- [ ] `openai.AsyncOpenAI` installed; **never** called in CI.
- [ ] `COPILOT_MODEL` / `COPILOT_API_KEY` / `COPILOT_BASE_URL` settings.
- [ ] `get_db()` and `app/core/exceptions.py`.

## Tasks

- [ ] **T-01 — `_make_openai_client()`.**
  `AsyncOpenAI(base_url=?, api_key=COPILOT_API_KEY.get_secret_value() or
  "no-key")`.
  - Legacy origin: `app/services/copilot_service.py:366`
  - Definition of done: importing the module with an empty environment does not
    raise; a test monkeypatching this symbol fully replaces the provider.
  - Confidence: 🟢

- [ ] **T-02 — `_sanitize_error(exc)`.**
  Redact the key **first**, then substitute the auth or connection category
  message, else return the redacted text.
  - Legacy origin: `app/services/copilot_service.py:44`
  - Definition of done: three tests — key embedded in an auth error, a bare
    connection error, and an unrelated error that passes through redacted.
  - Confidence: 🟢

- [ ] **T-03 — `_history_to_openai(history)`.**
  Emit user messages verbatim; for an assistant row with `tool_calls`, emit the
  assistant message and then one `tool` message per call, resolved through
  `results_by_id` or the placeholder.
  - Legacy origin: `app/services/copilot_service.py:396`
  - Definition of done: a test asserts that for every assistant `tool_call` at
    position *i*, the message at *i+1..i+n* are `tool` messages with matching
    `tool_call_id`s. Carry the gh-922 comment explaining that the hub 400s
    otherwise.
  - Confidence: 🟢

- [ ] **T-04 — `run_turn` skeleton and termination.**
  Build `messages` from the system prompt + replayed history; loop
  `MAX_LOOP_ITERATIONS = 6`; implement the three termination cases in order.
  - Legacy origin: `app/services/copilot_service.py:446`
  - Definition of done: `finish_reason == "stop"` ends after one completion;
    a `finish_reason` other than `"tool_calls"` with no accumulated calls also
    ends; only `"tool_calls"` continues.
  - Confidence: 🟢

- [ ] **T-05 — Delta accumulation.**
  Accumulate text into a buffer and tool-call fragments into
  `calls_by_index[index]` (`id`, `function.name`, `function.arguments`
  concatenated).
  - Legacy origin: `app/services/copilot_service.py` (the chunk loop)
  - Definition of done: a fake stream splitting one call's `arguments` across
    five chunks reassembles into valid JSON; two parallel calls with indices 0
    and 1 stay separate.
  - Confidence: 🟢

- [ ] **T-06 — Tool dispatch.**
  `json.loads(arguments)` with a `JSONDecodeError → {}` fallback; yield
  `tool_call`; `await asyncio.to_thread(copilot_tools.execute, …)`; wrap
  exceptions into `{"error": str(exc)}`; yield `tool_result`; append the `tool`
  message to `messages`.
  - Legacy origin: `app/services/copilot_service.py:602-612`
  - Definition of done: a tool that internally calls `asyncio.run` succeeds
    (this is the whole point of `to_thread` — carry the comment). The decode
    fallback is reproduced **and** recorded as a gap.
  - Confidence: 🟢

- [ ] **T-07 — The `done` event.**
  Yield `final_text`, `tool_calls`, `tool_results` and `truncated = not
  turn_complete`.
  - Legacy origin: `app/services/copilot_service.py` (loop epilogue)
  - Definition of done: a model that always requests tools ends with
    `truncated: true` after exactly 6 completions; a normal turn has
    `truncated` falsy.
  - Confidence: 🟢

- [ ] **T-08 — Hub/stream error path.**
  Any exception from `create(...)` or the chunk iteration ⇒
  `{"type":"error","message": _sanitize_error(exc)}`.
  - Legacy origin: `app/services/copilot_service.py`
  - Definition of done: the turn ends after the error event; the key is absent.
  - Confidence: 🟢

- [ ] **T-09 — `_sse_format`.**
  `f"event: {event_type}\ndata: {json.dumps(data, separators=(',',':'))}\n\n"`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/copilot_stream.py:53`
  - Definition of done: the payload is a **single line** (compact separators) —
    a multi-line `data:` would need the multi-line SSE form the frontend parser
    tolerates but the backend never emits.
  - Confidence: 🟢

- [ ] **T-10 — The route: pre-stream guards.**
  Append the user message (mapping `NotFoundError` → 404, `ServiceException` →
  500, anything else → 500 `"Unexpected error: …"`); load history; resolve the
  integer PK (`None` ⇒ 404).
  - Legacy origin: `app/api/v2/endpoints/aeroplane/copilot_stream.py:94-119`
  - Definition of done: an unknown UUID produces a JSON 404 body with **no**
    `text/event-stream` content type.
  - Confidence: 🟢

- [ ] **T-11 — The route: `_generate` mapping and persistence.**
  Map the five event types; on `done` persist the assistant row inside its own
  `try/except` that only `logger.error`s, **then** emit `done` with the minimal
  payload.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/copilot_stream.py:121-181`
  - Definition of done: persistence happens **before** the `done` event, so a
    client that reloads on `done` always finds the turn. A persistence failure
    still yields `done`.
  - Confidence: 🟢

- [ ] **T-12 — The route: catch-all.**
  `logger.exception(...)` then `error {"message": "Internal server error"}`.
  - Legacy origin: `…copilot_stream.py:179-181`
  - Definition of done: an exception whose message contains a filesystem path
    produces exactly the flat literal on the wire, with the traceback in the
    server log.
  - Confidence: 🟢

- [ ] **T-13 — Response headers.**
  `media_type="text/event-stream"`, `Cache-Control: no-cache`,
  `X-Accel-Buffering: no`.
  - Legacy origin: `…copilot_stream.py:183-190`
  - Definition of done: asserted in a contract test — without
    `X-Accel-Buffering` an nginx-proxied deployment buffers the whole turn.
  - Confidence: 🟢

- [ ] **T-14 — `SYSTEM_PROMPT` interpolation.**
  One `{context_hint}` placeholder filled from the request body.
  - Legacy origin: `app/services/copilot_service.py` (`SYSTEM_PROMPT`)
  - Definition of done: the hint text appears in the system message; an empty
    hint leaves a well-formed prompt.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Plain turn:** tokens concatenate to the answer; one `done`; one
      persisted assistant row.
- [ ] **TT-02 — Tool turn:** `tool_call` → `tool_result` → `done`; the row
      carries both arrays; exactly two completions requested.
- [ ] **TT-03 — Cap:** exactly 6 completions, `truncated: true`.
- [ ] **TT-04 — Chunk reassembly:** fragmented `arguments` and two parallel
      indices.
- [ ] **TT-05 — Decode failure (characterisation):** malformed arguments ⇒ the
      tool is invoked with `{}`.
- [ ] **TT-06 — Tool exception:** `{"error": …}` summary and the turn continues.
- [ ] **TT-07 — Off-loop:** a tool calling `asyncio.run` succeeds.
- [ ] **TT-08 — Replay pairing:** every `tool_call` immediately followed by its
      `tool` message.
- [ ] **TT-09 — Replay placeholder:** missing result ⇒ `{"error": "tool result
      unavailable"}`.
- [ ] **TT-10 — Pre-stream 404:** no SSE body.
- [ ] **TT-11 — Auth error:** category message only; key absent.
- [ ] **TT-12 — Catch-all:** exactly `"Internal server error"`.
- [ ] **TT-13 — Persistence failure:** `done` still emitted, error logged.
- [ ] **TT-14 — Headers:** content type + both headers.
- [ ] **TT-15 — Wire format:** each event is `event: …\ndata: …\n\n` with a
      single-line compact JSON payload.

## Suggested Order

1. **T-01 → T-02** the provider seam and the sanitiser: everything else can be
   tested only once the hub is fakeable and errors are safe to surface.
2. **T-03** replay before the loop — a wrong `messages` list makes every loop
   test ambiguous.
3. **T-04 → T-08** the loop itself, termination first, then accumulation, then
   dispatch. Dispatch last because it is the only part that needs real tools.
4. **T-09 → T-13** the route. T-10 (pre-stream guards) before T-11, because the
   404 path must not be reachable through the generator.
5. **T-14** the prompt last — it changes answers, not behaviour.

## Pending Gaps (🔴)

- **Should the turn be persisted from a background task** so a client
  disconnect cannot lose it?
- **Should a decode failure abort the tool call** instead of invoking it with
  `{}`?
- **Should the stream emit heartbeats** during a 60 s analysis so proxies do not
  time out?
- **Should the session be released between iterations**, given a turn can hold
  it for minutes?
- **Should a truncated turn roll back its side effects** — a proposal branch can
  exist with no assistant message explaining it?
- **Should `role="tool"` rows ever be written**, or should the replay branch for
  them be deleted?
- **What should be measured per turn** — iterations, tool names, latency, token
  usage, truncation rate? Today: nothing.
