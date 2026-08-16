# ai-copilot / copilot-turn-loop — Technical Design

> Use-case design. Parent module: [`../design.md`](../design.md).
> HTTP contract: [`../contracts.md`](../contracts.md).

## Interface

| Symbol | Signature | Note |
|---|---|---|
| `copilot_stream` | `(aeroplane_id: UUID4, body: CopilotStreamRequest, db) -> StreamingResponse` | the route |
| `_sse_format` | `(event_type: str, data: dict) -> str` | `f"event: {t}\ndata: {json}\n\n"`, `separators=(',',':')` |
| `run_turn` | `(db, aeroplane_id: int, history: CopilotHistory, context_hint: str) -> AsyncGenerator[dict, None]` | yields `{"type": …}` dicts |
| `_history_to_openai` | `(history) -> list[dict]` | the replay adapter |
| `_sanitize_error` | `(exc: Exception) -> str` | |
| `_make_openai_client` | `() -> AsyncOpenAI` | the monkeypatch seam |
| `MAX_LOOP_ITERATIONS` | `= 6` | |

Yielded event dicts and their SSE projection:

| `event["type"]` | SSE event | SSE data |
|---|---|---|
| `token` | `token` | `{"text": event["text"]}` |
| `tool_call` | `tool_call` | `{"name": …, "args": …}` |
| `tool_result` | `tool_result` | `{"name": …, "summary": …}` |
| `done` | `done` | `{"status":"ok"}` (+ `"truncated": true`) — the endpoint **drops** `final_text` / `tool_calls` / `tool_results` from the wire payload after persisting them |
| `error` | `error` | `{"message": …}` |

## Main Flow

### F1 — The endpoint 🟢

```
1  hist_svc.append_message(db, uuid, CopilotMessageWrite(role="user", content=body.message))
     except NotFoundError    -> HTTPException(404, str(exc))
     except ServiceException -> HTTPException(500, str(exc))
     except Exception        -> HTTPException(500, f"Unexpected error: {exc}")
2  history = hist_svc.get_history(db, uuid)
3  plane = db.query(AeroplaneModel).filter(uuid == ?).first()   -> None ⇒ 404
4  return StreamingResponse(_generate(), media_type="text/event-stream",
                            headers={"Cache-Control":"no-cache","X-Accel-Buffering":"no"})
```

Steps 1–3 run **before** the response object exists, which is why they can still
produce a status code. Everything after step 4 is in-band. 🟢

`X-Accel-Buffering: no` disables nginx response buffering — without it a
reverse-proxied deployment would deliver the whole turn at once instead of
streaming. 🟡

### F2 — `_generate` 🟢

```
accumulated_tool_calls, accumulated_tool_results, final_text = [], [], ""
try:
    async for event in run_turn(db, plane.id, history, body.context_hint):
        match event["type"]:
          "done":
              accumulated_* = event[...]                 # captured for persistence
              try:  hist_svc.append_message(db, uuid,
                        CopilotMessageWrite(role="assistant", content=final_text,
                                            tool_calls=accumulated_tool_calls or None,
                                            tool_results=accumulated_tool_results or None))
              except Exception as e: logger.error("Failed to persist assistant message: %s", e)
              done_data = {"status": "ok"} | ({"truncated": True} if event.get("truncated") else {})
              yield _sse_format("done", done_data)
          "error":       yield _sse_format("error", {"message": event.get("message","Unknown error")})
          "token":       yield _sse_format("token", {"text": event.get("text","")})
          "tool_call":   yield _sse_format("tool_call",   {"name":…, "args":…})
          "tool_result": yield _sse_format("tool_result", {"name":…, "summary":…})
except Exception:
    logger.exception("Unhandled error in copilot stream generator")
    yield _sse_format("error", {"message": "Internal server error"})
```

Note the ordering inside the `done` branch: **persist first, emit second**. A
client that sees `done` can therefore reload the history and find the turn.
🟢 The assistant row is committed in its own session at `done` (`Q-CO-4`), so a client that disconnects before `done`
loses it entirely, because the generator is abandoned and `get_db()`'s commit
(which runs only after the response is fully consumed) never fires.

### F3 — `run_turn` 🟢

```
client   = _make_openai_client()
messages = [{"role":"system","content": SYSTEM_PROMPT.format(context_hint=context_hint)}]
messages += _history_to_openai(history)

turn_complete = False
for iteration in range(MAX_LOOP_ITERATIONS):          # 6
    text_buf = ""
    calls_by_index: dict[int, {"id","name","arguments"}] = {}
    finish_reason = None

    stream = await client.chat.completions.create(
        model=settings.COPILOT_MODEL, messages=messages,
        tools=copilot_tools.list_schemas(), tool_choice="auto", stream=True)

    async for chunk in stream:
        delta.content        -> text_buf += ; yield {"type":"token","text": delta}
        delta.tool_calls[i]  -> calls_by_index[i].id        |= tc.id
                                calls_by_index[i].name      |= tc.function.name
                                calls_by_index[i].arguments += tc.function.arguments
        chunk.choices[0].finish_reason -> finish_reason

    if finish_reason == "stop" or not calls_by_index:
        turn_complete = True ; break

    if finish_reason == "tool_calls":
        messages.append(assistant message with the reassembled tool_calls)
        for call in calls_by_index.values():
            try:    args = json.loads(call.arguments)
            except json.JSONDecodeError: args = {}          # 🟡 must not proceed (Q-CO-2)
            yield {"type":"tool_call", "name": call.name, "args": args}
            try:    result = await asyncio.to_thread(copilot_tools.execute,
                                                     call.name, db, aeroplane_id, **args)
            except Exception as exc: result = {"error": str(exc)}
            yield {"type":"tool_result", "name": call.name, "summary": result}
            messages.append({"role":"tool","tool_call_id": call.id,
                             "content": json.dumps(result)})
        continue

yield {"type":"done", "final_text": …, "tool_calls": …, "tool_results": …,
       "truncated": not turn_complete}
```

The `to_thread` hop is documented at l.609-612: *inside the worker thread there
is no running event loop*, which is precisely what lets `_run_analysis` call
`asyncio.run(...)` on the AeroSandbox coroutine. Moving the dispatch back onto
the loop would break every solver tool. 🟢

Any exception raised by the hub or the stream is caught, passed through
`_sanitize_error` and yielded as `{"type":"error", "message": …}`. 🟢

### F4 — `_history_to_openai` 🟢

```
out = []
for m in history.messages:
    if m.role == "user":
        out.append({"role":"user","content": m.content})
    elif m.role == "assistant":
        msg = {"role":"assistant","content": m.content}
        if m.tool_calls: msg["tool_calls"] = m.tool_calls
        out.append(msg)
        results_by_id = {tr["tool_call_id"]: tr for tr in (m.tool_results or [])}
        for tc in (m.tool_calls or []):
            tr = results_by_id.get(tc["id"])
            content = json.dumps(tr["result"]) if tr else \
                      json.dumps({"error": "tool result unavailable"})
            out.append({"role":"tool","tool_call_id": tc["id"], "content": content})
    elif m.role == "tool":
        out.append({"role":"tool", ...})       # persisted tool rows exist in the
                                               # schema but not in practice 🟡
return out
```

### F5 — `_sanitize_error` 🟢

```
text = str(exc)
if settings.COPILOT_API_KEY:
    text = text.replace(settings.COPILOT_API_KEY.get_secret_value(), "[REDACTED]")
low = text.lower()
if any(m in low for m in ("auth","key","token","secret","credential")):
    return f"{type(exc).__name__}: authentication or configuration error"
if any(m in low for m in ("connect","timeout","refused","unreachable", ...)):
    return f"{type(exc).__name__}: hub connection error"
return text
```

The redaction runs **first**, so even the fall-through branch cannot emit the
key. 🟢

## Alternative Flows

- **Hub 401/403:** `error` event with the auth category message. 🟢
- **Hub unreachable:** `error` event with the connection category message. 🟢
- **`finish_reason == "length"` with no tool calls:** treated as completion
  (second termination case) — the turn ends with whatever text arrived. 🟡
- **Tool raises:** result becomes `{"error": …}`; the loop continues and the
  model usually retries with corrected arguments. 🟢
- **Tool arguments truncated:** `args = {}`; a write tool would then be invoked
  with **no ops**. 🟡 (`Q-CO-2`)
- **Assistant persistence fails:** logged; `done` still emitted; the turn is
  visually complete but absent from the reloaded history. 🟢 Fixed by `Q-CO-4`.
- **Client disconnects:** the generator is abandoned; nothing is persisted and
  nothing is committed. 🟢 Fixed by `Q-CO-4`.
- **Six iterations exhausted:** `done {truncated: true}`; the partial work
  performed by the tools (including a proposal branch) **remains**. 🟡

## Dependencies

- `copilot_history_service` — append / get.
- `copilot_tools.list_schemas()` and `.execute(...)`.
- `openai.AsyncOpenAI` via `_make_openai_client`.
- `app/core/config.settings` — `COPILOT_MODEL`, `COPILOT_API_KEY`.
- `get_db()` — the session is injected and held for the whole stream (ADR 0009).

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| Persist the user message before opening the stream so id errors stay HTTP | `copilot_stream.py:94-119` | 🟢 |
| Persist the turn as one assistant row and reconstruct the pairing on replay | gh-922, `_history_to_openai` | 🟢 |
| Dispatch tools off-loop so they may run their own event loop | `:609-612` comment | 🟢 |
| A tool error is data, not an exception | BR-46 | 🟢 |
| Two independent sanitisation layers | `_sanitize_error` + the endpoint catch-all | 🟢 |
| The `done` wire payload is deliberately minimal (`status`, optional `truncated`) | `copilot_stream.py:153-159` | 🟢 |
| Iteration cap of 6 rather than a token or time budget | `MAX_LOOP_ITERATIONS` | 🟢 |

## Internal State

| State | Where | Lifetime |
|---|---|---|
| `messages` | in `run_turn` | one turn; discarded afterwards — the DB row is the record |
| `calls_by_index` | per iteration | reassembly buffer for fragmented tool-call deltas |
| `accumulated_tool_calls/_results`, `final_text` | in `_generate` | committed at `done` in their own session (`Q-CO-4`) 🟢 |
| the request-scoped `Session` | `get_db()` | the entire turn — minutes in the worst case 🟡 |

## Observability

- `logger.error("Failed to persist assistant message: %s", …)`. 🟢
- `logger.exception("Unhandled error in copilot stream generator")`. 🟢
- 🔴 **Not addressed by the validation interview**; at single-user scale (ADR 0024) metrics have no consumer. Left open. Nothing logs turn start/end, iteration count, tool names, latency, token
  usage or truncation frequency — the three numbers needed to tune
  `MAX_LOOP_ITERATIONS` are all unrecorded.

## Risks and Gaps

- 🟢 A disconnect no longer loses the assistant message: it is committed in its own session at `done` (`Q-CO-4`). The side-effect/message asymmetry is what mattered.
- 🟡 Malformed tool arguments silently become `{}` — the call must not proceed (`Q-CO-2`, derived from `P-WARN-0`).
- 🟢 **No heartbeat, deliberately** (`Q-CO-4`): rejected as hardening against a deployment this project does not have (ADR 0024). A 60 s `run_analysis` streams nothing, and an intermediary
  may time the connection out.
- 🟡 The session is held for the entire turn, so a slow turn occupies a
  connection and (on SQLite) can contend with the recompute writer.
- 🟢 Resolved by committing the assistant row at `done` (`Q-CO-4`): a proposal branch can no longer exist
  with no assistant message explaining it.
- 🟡 `role="tool"` rows are supported by the schema but never written; the
  replay branch for them is effectively dead.
