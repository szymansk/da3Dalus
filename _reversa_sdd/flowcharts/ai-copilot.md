# Flowcharts — ai-copilot

## 1. Layer map — who calls whom

```mermaid
flowchart TD
    UI["Browser — copilot chat panel"]
    SSE["POST /aeroplanes/{uuid}/copilot/stream<br/>copilot_stream.py"]
    HIST["copilot_history_service<br/>(copilot_messages table)"]
    SVC["copilot_service.run_turn<br/>(async generator)"]
    HUB["LiteLLM hub<br/>OpenAI-compatible /v1<br/>COPILOT_BASE_URL"]
    TOOLS["copilot_tools.execute<br/>6-tool registry"]
    APPLY["copilot_apply_service<br/>apply_edits / proposal branch"]
    VER["aeroplane_version_service<br/>create_branch / discard_branch<br/>_metrics_payload"]
    DOM["wing_service · design_assumptions_service<br/>assumption_compute_service · stability_service<br/>analysis_service (AeroBuildup)"]

    UI -->|"message + context_hint"| SSE
    SSE -->|"append user row"| HIST
    SSE -->|"history"| SVC
    SVC <-->|"stream chat.completions"| HUB
    SVC -->|"asyncio.to_thread"| TOOLS
    TOOLS --> APPLY
    TOOLS --> VER
    APPLY --> DOM
    APPLY --> VER
    SVC -->|"done event"| SSE
    SSE -->|"append assistant row<br/>(tool_calls + tool_results)"| HIST
    SSE -->|"text/event-stream"| UI
```

The copilot **never** goes through the REST API of its own service: it calls
the service layer directly, in-process, on the request's own `Session`.
That is the opposite of the MCP server, which re-enters through the FastAPI
endpoint functions.

## 2. The turn loop (`run_turn`, `copilot_service.py:446`)

```mermaid
flowchart TD
    A["run_turn(db, aeroplane_id, history, context_hint)"] --> B["system prompt = SYSTEM_PROMPT.format(context_hint)"]
    B --> C["openai_messages = [system] + _history_to_openai(history)"]
    C --> D["tool_schemas = copilot_tools.list_schemas()"]
    D --> E["client = _make_openai_client()<br/>(monkeypatched in every test)"]
    E --> LOOP{"iteration < MAX_LOOP_ITERATIONS (6)?"}

    LOOP -- no --> TRUNC["done + truncated: true"]
    LOOP -- yes --> F["await client.chat.completions.create(stream=True)"]
    F -- exception --> ERR["yield error<br/>_sanitize_error(exc)"]
    F --> G["async for chunk in stream"]
    G --> H{"delta.content?"}
    H -- yes --> H1["yield token {text}"]
    G --> I{"delta.tool_calls?"}
    I -- yes --> I1["accumulate tool_call_chunks[index]<br/>(id, name, arguments concatenated)"]
    G --> J{"finish_reason"}
    J -- "stop / no tool_calls" --> DONE["turn_complete = True; break"]
    J -- "tool_calls" --> K["append assistant message with tool_calls"]

    K --> L["for each tool call"]
    L --> M["json.loads(arguments) — on JSONDecodeError use {}"]
    M --> N["yield tool_call {name, args}"]
    N --> O["result = await asyncio.to_thread(<br/>copilot_tools.execute, name, db, aeroplane_id, **args)"]
    O --> P["yield tool_result {name, summary}"]
    P --> Q["append role='tool' message (tool_call_id, json result)"]
    Q --> LOOP

    DONE --> R["yield done {tool_calls, tool_results, final_text}"]
    TRUNC --> R
```

Two non-obvious points:

* Tool execution runs in a **worker thread** (`asyncio.to_thread`). Inside that
  thread there is no running event loop, which is exactly what lets
  `copilot_tools._run_analysis` call `asyncio.run(...)` for the async
  AeroSandbox path.
* A failed `json.loads` of the streamed arguments silently degrades to `{}` —
  the tool is still called, just without arguments.

## 3. History replay — the gh-922 orphaned-`tool_use` fix

```mermaid
flowchart LR
    subgraph PERSISTED["copilot_messages (as stored)"]
        U["role=user<br/>content"]
        A["role=assistant<br/>content<br/>tool_calls[]<br/>tool_results[]"]
    end
    subgraph REPLAYED["_history_to_openai output"]
        U2["{role: user}"]
        A2["{role: assistant, tool_calls}"]
        T1["{role: tool, tool_call_id: X, content}"]
        T2["{role: tool, tool_call_id: Y, content}"]
    end
    U --> U2
    A --> A2
    A -->|"one synthetic tool message<br/>per tool_call, matched by id"| T1
    A --> T2
```

One DB row carries *both* the tool calls and their results. The strict
OpenAI/Anthropic tool protocol requires each `tool_call` to be followed by a
matching `tool` message, so `_history_to_openai` **reconstructs** them. A
tool call whose result is missing gets the literal
`{"error": "tool result unavailable"}` placeholder rather than being dropped —
dropping it would 400 the hub on every subsequent turn.

## 4. Tool dispatch and read-retargeting (`copilot_tools.execute`)

```mermaid
flowchart TD
    A["execute(name, db, live_aeroplane_id, **kwargs)"] --> B{"name in TOOL_REGISTRY?"}
    B -- no --> ERR["error: Unknown tool 'name'.<br/>Known tools: ..."]
    B -- yes --> C{"name in READ_RETARGETED_TOOLS<br/>{get_design_snapshot,<br/>get_wing_geometry, run_analysis}?"}
    C -- no --> D["effective_id = live_aeroplane_id"]
    C -- yes --> E["_effective_target_id()"]
    E --> F["root_id = _get_lineage_root_id(live_id)"]
    F --> G["proposal = _find_open_proposal(root_id)"]
    G -- found --> H["effective_id = proposal.head_id"]
    G -- none / any exception --> D
    H --> I["entry.impl(db, effective_id, **kwargs)"]
    D --> I
```

`get_version_tree` is deliberately **not** retargeted (it must show the live
lineage), and the write tools always receive the live id so they can find or
open the proposal branch. Any exception inside `_effective_target_id` is
swallowed and falls back to the live id.

## 5. The agentic apply cycle — propose, never mutate

```mermaid
sequenceDiagram
    autonumber
    participant LLM
    participant T as copilot_tools
    participant AP as copilot_apply_service
    participant V as aeroplane_version_service
    participant D as domain services

    LLM->>T: get_design_snapshot()
    T->>V: _metrics_payload(live head)
    LLM->>T: run_analysis(kind='polar')   %% fresh BEFORE baseline
    LLM->>T: apply_design_edits(ops=[…])
    T->>T: TypeAdapter(list[EditOp]).validate_python(ops)
    T->>AP: get_or_open_proposal(db, live_id)
    alt open 'copilot-proposal%' branch exists
        AP-->>T: reuse it (ONE open proposal per lineage)
    else none
        AP->>V: create_branch(from live head, created_by='copilot')
        V-->>AP: BranchModel
    end
    T->>V: _metrics_payload(proposal head)  %% pre-edit baseline
    T->>AP: apply_edits(db, proposal_uuid, ops)
    AP->>D: wing_service.put_wing_as_wingconfig / update_assumption
    AP->>D: recompute_assumptions(proposal_uuid)
    AP-->>T: {applied, rejected, metrics}
    T->>T: compute_metrics_diff(pre, post)
    T-->>LLM: {branch_id, applied, rejected, diff_proposal_branch}
    LLM->>T: run_analysis(kind='polar')     %% auto-retargets to the PROPOSAL
    Note over LLM: presents diff + "adopt or discard in the Versions panel"
    Note over LLM,V: There is NO adopt tool — only the human adopts.
```

## 6. `apply_edits` — op dispatch and the deferred wing write

```mermaid
flowchart TD
    A["apply_edits(db, proposal_uuid, ops)"] --> B["applied=[] · rejected=[] · wing_config_cache={}"]
    B --> C{"for op in ops"}

    C --> S1["SetAssumption → update_assumption(param, value)"]
    C --> S2["SetXsec → _load_wing → mutate STATION<br/>(root of seg[i] AND tip of seg[i-1])"]
    C --> S3["SetSegment → _load_wing → mutate ONE segment<br/>(length, sweep, chord_tip, dihedral_rel, incidence)"]
    C --> S4["AddXsec → tip-append only"]
    C --> S5["RemoveXsec → merge seg[i-1] and seg[i]"]
    C --> S6["SetWingParam → sweep/dihedral on EVERY segment"]
    C --> S7["ReplaceWingConfig → validate + put immediately<br/>+ cache evict + db.expire_all()"]
    C --> S8["unknown type → rejected"]

    S2 --> CACHE["wing_config_cache[wing] = wc (in-memory, mm)"]
    S3 --> CACHE
    S4 --> CACHE
    S5 --> CACHE
    S6 --> CACHE

    C -->|"any exception"| REJ["rejected.append({op, error}) — never raises"]

    CACHE --> W["after the loop: for each cached wing<br/>WingConfigurationSchema.model_validate → put_wing_as_wingconfig(scale=0.001)"]
    W -->|"failure"| REJ2["rejected.append({op:'WingWrite', wing})"]
    W --> EXP["db.expire_all() — flush stale WingModel identities"]
    EXP --> RC["recompute_assumptions(proposal_uuid) — non-fatal on failure"]
    RC --> OUT["{applied, rejected, metrics=_metrics_payload(node)}"]
```

The per-wing cache is what makes multiple ops on one wing **composable**: they
all mutate the same in-memory dict and are written exactly once at the end.
`ReplaceWingConfig` is the exception — it writes immediately and then evicts
the cache so later ops re-read the new state.

### `AddXsec` index handling (gh-938 Bug B)

```mermaid
flowchart TD
    A["at_index (1-based), n = len(segments), n_xsecs = n + 1"] --> B{"at_index >= n_xsecs?"}
    B -- yes --> C["clamp: effective = n + 1 (tip-append)"]
    B -- no --> D{"effective < n + 1 (interior)?"}
    D -- yes --> E["REJECT — 'mid-wing insert not supported;<br/>use at_index = n_xsecs for a winglet'"]
    D -- no --> C
    C --> F["strip tip_type from ALL trailing segments"]
    F --> G["append new segment (root = old tip, tip = new xsec)"]
```

The `tip_type` stripping is load-bearing: `create_wing_configuration()`
processes segments in two passes (middle = `tip_type is None`, then tip), so
leaving `tip_type='flat'` on the old last segment would make the new winglet
be processed **before** it and physically reorder the cross-sections.

## 7. `discard_open_proposal` — why `expunge_all()` is mandatory

```mermaid
flowchart TD
    A["discard_open_proposal(db, live_id)"] --> B["db.flush() — persist pending writes"]
    B --> C["db.expunge_all() — CLEAR the identity map"]
    C --> D["root_id = _get_lineage_root_id(live_id)  (re-query)"]
    D --> E["branch = _find_open_proposal(root_id)  (re-query)"]
    E -- none --> F["return False"]
    E -- found --> G["discard_branch(db, branch.id)"]
    G --> H["return True"]

    C -.->|"without expunge"| X["InvalidRequestError: Can't attach instance<br/>&lt;WingXSecSpareModel …&gt; — another instance with<br/>key (…) is already present in this session"]
```

`apply_edits` → `put_wing_as_wingconfig` does delete-then-reinsert inside the
same session, leaving deleted-but-tracked `WingXSecSpareModel` instances in the
identity map. The subsequent cascade delete of the proposal node then collides
with them.

## 8. SSE event contract

```mermaid
sequenceDiagram
    participant B as Browser (EventSource / fetch reader)
    participant E as copilot_stream endpoint
    participant S as run_turn

    B->>E: POST {message, context_hint}
    E->>E: append_message(role='user')   %% BEFORE the stream opens
    Note over E: NotFoundError → HTTP 404, ServiceException → 500<br/>(the only errors delivered as a status code)
    E->>S: run_turn(...)
    loop per event
        S-->>E: {type: token|tool_call|tool_result|error}
        E-->>B: event: token\ndata: {"text": "…"}
        E-->>B: event: tool_call\ndata: {"name","args"}
        E-->>B: event: tool_result\ndata: {"name","summary"}
    end
    S-->>E: {type: done, tool_calls, tool_results, final_text, truncated?}
    E->>E: append_message(role='assistant', tool_calls, tool_results)
    Note over E: a persist failure is logged only —<br/>the client still receives 'done'
    E-->>B: event: done\ndata: {"status":"ok"[, "truncated": true]}
```

Response headers: `Cache-Control: no-cache`, `X-Accel-Buffering: no` (so an
nginx/Caddy hop in front does not buffer the stream).

## 9. Error sanitisation before anything reaches the browser

```mermaid
flowchart TD
    A["_sanitize_error(exc)"] --> B["key = settings.COPILOT_API_KEY.get_secret_value()"]
    B --> C{"key literal present in str(exc)?"}
    C -- yes --> D["replace with '[REDACTED]'"]
    C -- no --> E["raw unchanged"]
    D --> F{"lowercased text contains<br/>auth|key|token|api_key|secret|credential?"}
    E --> F
    F -- yes --> G["'&lt;ExcType&gt;: authentication or configuration error'"]
    F -- no --> H{"contains connect|timeout|network|refused|unreachable?"}
    H -- yes --> I["'&lt;ExcType&gt;: hub connection error'"]
    H -- no --> J["'&lt;ExcType&gt;: &lt;redacted raw text&gt;'"]
```
