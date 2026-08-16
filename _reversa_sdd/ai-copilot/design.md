# ai-copilot — Technical Design

> Module-level design. Focuses on HOW the module is built, derived from the
> legacy code. Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Endpoint contract: [`contracts.md`](contracts.md).
> Use cases: [`copilot-turn-loop`](copilot-turn-loop/design.md) ·
> [`copilot-tools`](copilot-tools/design.md) ·
> [`proposal-adopt-discard`](proposal-adopt-discard/design.md).

## Interface

### Persistence 🟢

**`copilot_messages`** (`app/models/aeroplanemodel.py:818`)

| Column | Type | Req. | Default | Note |
|---|---|---|---|---|
| `id` | Integer PK | yes | autoincrement | indexed |
| `aeroplane_id` | Integer FK → `aeroplanes.id` `ON DELETE CASCADE` | yes | — | indexed |
| `sort_index` | Integer | yes | `0` | assigned as `COUNT(*)` at append time — 🟢 moves to `created_at` + `id` (`Q-CO-5`) |
| `role` | String | yes | — | `user` \| `assistant` \| `tool` — **no DB enum** |
| `content` | String | yes | `""` | |
| `tool_calls` | JSON | no | `NULL` | `[{id, type:"function", function:{name, arguments}}]` |
| `tool_results` | JSON | no | `NULL` | `[{tool_call_id, name, result}]` — **same row** as the calls |
| `parent_id` | Integer | no | `NULL` | 🟢 becomes a real FK; conversation branching stays planned (`Q-CO-5`) |
| `created_at` | DateTime(tz) | yes | `func.now()` | |

Referenced by `aeroplanes.provenance_message_id`
(FK `fk_aeroplanes_provenance_msg`, `use_alter`). Listed in `EXCLUDED_TABLES` of
the clone registry — a branch or snapshot never copies the conversation. 🟢

### Services 🟢

| Module | Symbol | Signature / note |
|---|---|---|
| `copilot_service` | `run_turn(db, aeroplane_id, history, context_hint)` | `AsyncGenerator[dict, None]` |
| | `_make_openai_client()` | the **only** provider dependency (`:366`) |
| | `_history_to_openai(history)` | reconstructs `tool` messages (`:396`) |
| | `_sanitize_error(exc)` | key redaction + category substitution (`:44`) |
| | `SYSTEM_PROMPT`, `MAX_LOOP_ITERATIONS = 6` | |
| `copilot_tools` | `execute(name, db, aeroplane_id, **kwargs) -> dict` | `:866`, resolves the effective target id |
| | `list_schemas() -> list[dict]` | OpenAI function-calling schemas |
| | `TOOL_REGISTRY: dict[str, ToolEntry]` | 6 entries (`:828`) |
| | `_drag_breakdown(cl, cd_total, ar, e)` | `:242` |
| | `_run_polar_async`, `_run_stability_async` | AeroBuildup / stability |
| | `DEFAULT_ANALYSIS_TIMEOUT_S = 60.0` | |
| `copilot_apply_service` | `get_or_open_proposal(db, live_id, message_id=None) -> BranchModel` | `:107` |
| | `apply_edits(db, proposal_uuid, ops) -> dict` | `:248` |
| | `discard_open_proposal(db, live_id) -> bool` | |
| | `compute_metrics_diff(before, after) -> dict` | over `_DIFF_KEYS` (13) |
| | `_COPILOT_BRANCH_PREFIX = "copilot-proposal"` | |
| `copilot_history_service` | `append_message`, `get_history`, `clear_history`, `delete_message` | 99 l. |

### REST 🟢

1 SSE route + 4 history routes — see [`contracts.md`](contracts.md).

## Main Flow

### F1 — One turn, end to end 🟢

```
POST /aeroplanes/{uuid}/copilot/stream
 ├ hist_svc.append_message(user)          ← BEFORE the stream; 404/500 here is a real HTTP status
 ├ history = hist_svc.get_history(uuid)   ← includes the message just appended
 ├ plane   = SELECT aeroplanes WHERE uuid = ?      ← tools need the INTEGER pk
 └ StreamingResponse(_generate(), media_type="text/event-stream",
                     headers={Cache-Control: no-cache, X-Accel-Buffering: no})

_generate():
  async for event in copilot_service.run_turn(db, plane.id, history, context_hint):
      token       -> event: token       {text}
      tool_call   -> event: tool_call   {name, args}
      tool_result -> event: tool_result {name, summary}
      done        -> persist the assistant message, then
                     event: done {status:"ok"[, truncated:true]}
      error       -> event: error {message}
  except Exception:
      logger.exception(...) ; event: error {"message": "Internal server error"}
```

The persistence of the assistant row is wrapped in its own `try/except` that
only `logger.error`s — a persistence failure must not break the stream. 🟢

### F2 — `run_turn` 🟢

```
messages = [system(SYSTEM_PROMPT.format(context_hint))] + _history_to_openai(history)

for iteration in 1..MAX_LOOP_ITERATIONS (6):
    stream = client.chat.completions.create(model=COPILOT_MODEL, messages=messages,
                                            tools=list_schemas(), tool_choice="auto",
                                            stream=True)
    accumulate text deltas          -> yield {"type":"token", ...}
    accumulate tool-call chunks BY INDEX (id / name / arguments arrive fragmented)

    finish_reason == "stop"                       -> turn_complete, break
    no tool-call chunks (any finish_reason)       -> turn_complete, break
    finish_reason == "tool_calls"                 -> execute, append results, continue

execute(one call):
    args = json.loads(accumulated_arguments)  except JSONDecodeError -> args = {}   🟡 (Q-CO-2)
    yield {"type":"tool_call", name, args}
    result = await asyncio.to_thread(copilot_tools.execute, name, db, aeroplane_id, **args)
    #        ^ off-loop ON PURPOSE: no running loop inside the thread, so a tool
    #          may call asyncio.run(...) for the async AeroSandbox coroutine
    except Exception as exc: result = {"error": str(exc)}
    yield {"type":"tool_result", name, summary=result}

after the loop:
    yield {"type":"done", final_text, tool_calls[], tool_results[],
           truncated: iterations exhausted while the model still wanted tools}
```

Detail in [`copilot-turn-loop`](copilot-turn-loop/design.md). 🟢

### F3 — History replay (gh-922) 🟢

```
for m in history.messages:
    role == "user"       -> {"role":"user", "content": m.content}
    role == "assistant"  -> {"role":"assistant", "content": m.content,
                             "tool_calls": m.tool_calls}          (when present)
                            results_by_id = {tr["tool_call_id"]: tr for tr in m.tool_results or []}
                            for tc in m.tool_calls:
                                content = json.dumps(results_by_id[tc["id"]]["result"])
                                          if present else
                                          json.dumps({"error": "tool result unavailable"})
                                emit {"role":"tool", "tool_call_id": tc["id"], "content": content}
```

Both the OpenAI and the Anthropic tool protocols require every assistant
`tool_call` to be **immediately followed** by a matching `tool` message. A turn
is stored as one row, so the interleaving has to be *reconstructed*; the
placeholder error object is deliberate — dropping the message would break the
pairing again. 🟢

### F4 — Error sanitisation 🟢

```
_sanitize_error(exc):
    text = str(exc)
    if COPILOT_API_KEY: text = text.replace(key, "[REDACTED]")
    if any of {auth, key, token, secret, credential} in text.lower():
        return f"{type(exc).__name__}: authentication or configuration error"
    if any connectivity marker in text.lower():
        return f"{type(exc).__name__}: hub connection error"
    return text                      # redacted raw text
```

The endpoint's outer `except` is stricter still and emits the flat string
`"Internal server error"` — so even a sanitiser bug cannot leak. 🟢

### F5 — The 6 tools 🟢

| Tool | Kind | Retargeted | Returns |
|---|---|---|---|
| `get_design_snapshot` | read | **yes** | `_metrics_payload(node)` — the `versioning` dict |
| `get_wing_geometry(wing?)` | read | **yes** | `editable` + `derived` blocks, **mm + degrees** |
| `run_analysis(kind)` | read | **yes** | polar or stability summary, SI |
| `get_version_tree` | read | no | nodes + branches of the **live** lineage |
| `apply_design_edits(ops)` | write | no | `branch_id`, `applied`, `rejected`, diff |
| `discard_proposal` | write | no | `{"discarded": bool}` |

```
execute(name, db, aeroplane_id, **kwargs):
    entry = TOOL_REGISTRY.get(name) or return {"error": "Unknown tool ... Known tools: ..."}
    _READ_RETARGETED_TOOLS = {get_design_snapshot, get_wing_geometry, run_analysis}
    effective_id = _effective_target_id(db, aeroplane_id) if name in that set else aeroplane_id
    return entry.impl(db, effective_id, **kwargs)

_effective_target_id: find the open proposal branch, return branch.head_id
                      except Exception: pass  -> falls back to the live id   🟡 (Q-CO-3)
```

Detail in [`copilot-tools`](copilot-tools/design.md). 🟢

### F6 — Deterministic arithmetic 🟢

```
_drag_breakdown(cl, cd_total, ar, e):
    if any input is None            -> None
    if ar <= 0 or e <= 0 or cd_total <= 0 -> None
    cd_i   = cl**2 / (pi * ar * e)                  # lifting-line
    cd_par = cd_total - cd_i                        # ONE source; never mix snapshot cd0
    if cd_i < 0 or cd_par < 0 or cd_i > cd_total:
        return {"note": <why>, "cl": cl, "cd_total": cd_total, "aspect_ratio": ar, "e": e}
    return {"cd_induced": cd_i, "cd_parasite": cd_par, ...}

_polar_drag_breakdown: picks the max-L/D point via nanargmax(CL/CD) and pulls
                       aspect_ratio / e_oswald from assumption_computation_context
                       — the SAME source the polar's e came from.

_run_polar_async:      AeroBuildup over alpha in [-10, +15], 26 points, V = 20 m/s, h = 0.
                       Reports cl_max, cl_min, cd_min, cl_cd_max, drag_breakdown and four
                       characteristic points renamed for the model:
                       best_glide, min_drag, cl_max_point, stall.

_run_stability_async:  evaluates at the CRUISE design point (alpha = 0,
                       v_cruise_mps from the context, fallback 20 m/s), then
                       OVERRIDES the fresh neutral point with ctx["x_np_m"] and
                       recomputes SM = (x_np - cg_x) / MAC * 100.
```

The override exists because the two stability paths normalise `x_np` against
different reference chords; a fresh run would surface a second divergent value
(0.109 m vs the dashboard's 0.080 m). *One op-point → one neutral point*
(gh-924, ADR 0004). 🟢

### F7 — `apply_edits` 🟢

```
wing_config_cache: dict[str, dict]      # per-wing, MILLIMETRES
applied, rejected = [], []

for op in ops:
    SetAssumption      -> design_assumptions_service write (SI / degrees)
    SetXsec            -> station op: touches BOTH neighbouring segments
    SetSegment         -> segment op: touches only its tip airfoil
    AddXsec            -> tip append only; at_index must be n_xsecs
                          strips tip_type from EVERY trailing segment (:517-520)
    RemoveXsec         -> interior only (1 .. n-2); merges seg[i-1] + seg[i]
                          lengths added, SWEEPS ADDED (comment is wrong, sum is right — Q-CO-7) 🟢
    SetWingParam       -> applies sweep_mm / dihedral to EVERY segment
    ReplaceWingConfig  -> validates + writes IMMEDIATELY, evicts the cache entry,
                          db.expire_all()
    on failure: rejected.append({"op": ..., "error": str(exc)}) and continue

for wing, cfg in wing_config_cache.items():
    put_wing_as_wingconfig(db, uuid, wing, cfg, scale=0.001)     # mm -> m
db.expire_all()          # put_* deletes-then-reinserts; stale identities would
                         # make the metrics payload read PRE-edit geometry
recompute_assumptions(db, proposal_uuid)   # non-fatal: logger.warning, continue
return {"applied": [...], "rejected": [...], "metrics": _metrics_payload(node)}
```

### F8 — The proposal branch 🟢

```
get_or_open_proposal(db, live_id, message_id=None):
    node    = aeroplanes[live_id]
    root_id = node.root_id or node.id
    branch  = newest branch WHERE root_id = ? AND is_main = False
                              AND created_by = 'copilot'
                              AND name LIKE 'copilot-proposal%'      ORDER BY id DESC
    if branch: return branch                                          # reuse
    return create_branch(db, from_node_id=live_id,
                         name=f"copilot-proposal{'-'+str(message_id) if message_id else ''}",
                         created_by="copilot")

discard_open_proposal(db, live_id):
    db.flush() ; db.expunge_all() ; re-resolve the branch ; discard_branch(db, branch.id)
```

The `expunge_all()` is named in the docstring with the exact error it prevents:
`InvalidRequestError: Can't attach instance <WingXSecSpareModel …>; another
instance with key (…) is already present in this session`. 🟢

Detail in [`proposal-adopt-discard`](proposal-adopt-discard/design.md).

### F9 — `compute_metrics_diff` 🟢

Pure helper over 13 hard-coded dot-paths (`_DIFF_KEYS`, `:44`):
`mass_kg ← total_mass_kg`; then `span_m`, `aspect_ratio`, `cd0`, `e_oswald`,
`ld_max`, `x_np_m`, `static_margin_pct`, `v_stall_mps`, `v_min_sink_mps`,
`v_cruise_mps`, `cl_max`, `wing_area_m2` navigated into
`assumption_computation_context`. Unchanged and both-missing keys are omitted;
output is `{label: {before, after, delta}}` rounded to 6 decimals.

`_apply_design_edits` compares the **proposal's pre-edit** payload (captured
right after `get_or_open_proposal`) with the post-edit one — both fresh from the
branch — so recompute drift on the live node cannot pollute the diff. It is
returned twice: `diff_proposal_branch`, and `diff_vs_live` as a
backward-compatible alias whose name is now **wrong**. 🟢 A real live-vs-proposal diff replaces it (`Q-CO-6`).

## Alternative Flows

- **Unknown aeroplane UUID:** 404 raised *before* the stream opens. 🟢
- **`ServiceException` while persisting the user message:** 500 before the
  stream opens. 🟢
- **Assistant-message persistence fails after `done`:** logged at ERROR; the
  `done` event is still emitted and the stream ends normally. 🟢
- **Hub authentication failure:** `error` event carrying the *category* message;
  the key is never present. 🟢
- **Any unhandled generator exception:** `error` event with the flat string
  `"Internal server error"`. 🟢
- **Model requests an unknown tool:** `{"error": "Unknown tool 'x'. Known
  tools: …"}` — the model can self-correct from the list. 🟢
- **Malformed tool arguments:** `args = {}` and the tool is **still called**. 🟡 The call must not proceed on an undecodable payload (`Q-CO-2`, derived from `P-WARN-0`).
- **`_effective_target_id` raises:** swallowed; the read silently targets the
  **live** node while the model believes it reads its proposal. 🟡 The failure must surface in the tool result (`Q-CO-3`, derived).
- **`run_analysis` exceeds 60 s:** `{"status": "timeout", "note": …}` — not an
  error. 🟢
- **Impossible drag split:** a `note`-carrying dict with the raw inputs. 🟢
- **Op names a non-existent wing / bad index:** that op lands in `rejected`; the
  rest still apply. 🟢
- **Interior `AddXsec`:** rejected with a message steering the model to a
  tip-append — mid-wing insertion is implemented (`Q-CO-8`). 🟢
- **`discard_proposal` with no proposal:** `{"discarded": false}`. 🟢
- **Two proposal branches exist:** the newest wins; the older is silently
  orphaned — impossible once the partial unique index lands (`Q-CO-12`). 🟢
- **A human renames the proposal branch:** the `LIKE 'copilot-proposal%'` reuse
  query is replaced by a typed `branch_kind` column, so a rename is harmless (`Q-CO-12`). 🟢
- **Client disconnects mid-stream:** the generator is abandoned, the `done`
  branch never runs, the assistant message is **not** persisted and the
  `get_db()` commit never happens — the assistant row is committed in its own session at `done` (`Q-CO-4`). 🟢

## Dependencies

- **`versioning`** — `create_branch` / `discard_branch` for the proposal, and
  the private `_metrics_payload` (imported by both `copilot_apply_service` and
  `copilot_tools` despite its `_` prefix 🟡).
- **`wing-design`** — `put_wing_as_wingconfig(scale=0.001)` is the only geometry
  write path; `WingXSecModel.xyz_le` is the read source for the derived block.
- **`aero-analysis`** — AeroBuildup polar and the stability summary behind
  `run_analysis`.
- **`mission-and-sizing`** — `design_assumptions_service` for `SetAssumption`,
  `recompute_assumptions` after an apply, and
  `assumption_computation_context` as the single source of `x_np_m`,
  `aspect_ratio` and `e_oswald` (gh-924).
- **`platform-core`** — `get_db()` owns the transaction (ADR 0009); the four
  `COPILOT_*` settings live in `app/core/config.py`.
- **`openai` (AsyncOpenAI)** — the only third-party client, reached through one
  factory function.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The provider dependency is a single monkeypatchable factory | `_make_openai_client:366` + its docstring | 🟢 |
| Plain OpenAI chat-completions + function calling, so any hub model works | `run_turn` call site | 🟢 |
| A turn is one persisted assistant row; the `tool` messages are reconstructed on replay | `_history_to_openai:396` (gh-922) | 🟢 |
| Tools run off the event loop precisely so they may call `asyncio.run` | `:609-612` comment | 🟢 |
| Errors are return values, never exceptions | BR-46, module docstring | 🟢 |
| The tool surface is curated to 6, not derived from the API | `TOOL_REGISTRY:828` | 🟢 |
| Read tools retarget to the proposal head so the model sees its own edits | `execute:866` (gh-938) | 🟢 |
| Every number is computed in Python; an impossible result is reported, not fudged | `_drag_breakdown:242`; ADR 0004/0012 | 🟢 |
| The neutral point is overridden from the computation context | `_run_stability_async` (gh-924) | 🟢 |
| `get_wing_geometry` returns mm/degrees, breaking the SI convention on purpose | module docstring | 🟢 |
| The derived block reads persisted `xyz_le` rather than re-walking segments | `_get_wing_geometry` docstring (gh-958) | 🟢 |
| Op schemas are inlined by hand because the model guesses field names otherwise | `edit_ops_array_schema:240` (gh-938) | 🟢 |
| Geometry ops compose in a per-wing mm cache written once | `apply_edits:248` | 🟢 |
| `expire_all` / `expunge_all` are correctness requirements, not hygiene | the two docstrings | 🟢 |
| The write surface is one disposable branch, and there is no adopt tool | ADR 0007 | 🟢 |
| `created_by` vocabulary fixed to `human` \| `ai`; reuse keys on `branch_kind` instead | `get_or_open_proposal` | 🟢 (`Q-CC-9`, `Q-CO-12`) |

## Internal State

| State | Where | Lifecycle |
|---|---|---|
| The chat thread | `copilot_messages` | appended per turn; cleared wholesale or per message; **never cloned** |
| `sort_index` | `copilot_messages` | 🟢 moves to `created_at` + `id` (`Q-CO-5`) |
| The open proposal | a `branches` row (`created_by='copilot'`) | opened on first write op, reused, discarded by tool or by the human in the Versions panel |
| Per-turn tool accumulation | in-memory in `run_turn` / the endpoint generator | flushed into the assistant row on `done`; **lost on client disconnect** 🔴 |
| `wing_config_cache` | in-memory in `apply_edits` | one entry per touched wing; written once at the end of the batch |
| `parent_id`, `provenance_message_id` | columns | 🟢 both become live (`Q-CO-5`, `Q-CO-1`) |

## Observability

- `logger.exception` on `get_or_open_proposal` failure, `apply_edits` failure and
  `_discard_proposal` failure — each with the aeroplane id. 🟢
- `logger.error` when the assistant message cannot be persisted. 🟢
- `logger.warning` when the post-apply recompute fails. 🟢
- `logger.exception("Unhandled error in copilot stream generator")` in the
  endpoint's catch-all — the one place where the raw traceback is kept
  server-side while the client sees only `"Internal server error"`. 🟢
- 🔴 **No AI-activity metrics** and **no cost accounting**. Nothing counts turns,
  tokens, tool calls, proposals opened / discarded / adopted, or hub latency.
  **Not addressed by the validation interview**; per-user attribution is moot
  (there are no users, ADR 0024). Left open rather than assumed away.

## Risks and Gaps

- 🟡 **A JSON-decode failure on tool arguments silently becomes `{}`** and the
  tool is still executed — a truncated stream can call a write tool with no ops.
  `Q-CO-2` derives from `P-WARN-0` that the call must not proceed on an
  undecodable payload. Derived, so INFERRED.
- 🟡 **`_effective_target_id` swallows every exception**, so a retarget failure
  is indistinguishable from "no proposal open" and the model reads the live
  design believing it reads its own edits. `Q-CO-3` derives that the failure must
  surface in the tool result. Derived, so INFERRED.
- 🟢 **The assistant row is committed in its own session at `done`** (`Q-CO-4`,
  maintainer-answered), so a disconnect can no longer leave a proposal branch
  with nothing recording why. The session is still held for the turn; **no
  heartbeat and no resumable stream** — explicitly rejected as hardening against
  a deployment this project does not have.
- 🟢 **`sort_index` moves to `created_at` + `id`** (`Q-CO-5`) — the `COUNT(*)`
  assignment is neither concurrency- nor delete-safe, and this is fixed
  regardless of the branching work.
- 🟢 **`parent_id` becomes a real foreign key** (`Q-CO-5`, maintainer-answered):
  conversation branching **stays planned**, mirroring aeroplane branching, so
  that branching at a snapshot can roll the chat back too.
- 🟢 **The AI audit trail is wired** (`Q-CO-1`): the copilot supplies the message
  id and the version graph resolves back to the conversation turn. Both inert
  halves become live, which is what makes ADR 0007's accountability real.
- 🟢 **`diff_vs_live` gets a real live-vs-proposal diff** (`Q-CO-6`) — the field
  is made to match its name, so the prompt paragraph warning the model off it can
  be deleted.
- 🟢 **`RemoveXsec`'s sum is correct; the comment is wrong** (`Q-CO-7`): sweep is
  a chordwise distance along an invariant `xDir`, so merged segments add sweeps.
- 🟢 **Mid-wing `AddXsec` is implemented** (`Q-CO-8`) — a control device is
  defined over a *segment*, so only a mid-span insert creates the boundary an
  aileron needs; a tip-append cannot.
- 🟡 **`COPILOT_EMBEDDING_MODEL` is dead configuration.** `Q-CO-10` keeps the
  agentic expert panel planned and specifies its knowledge source as **the
  repository's own domain-expert skills** with lexical retrieval — under which no
  embedding model is needed at all, so ADR 0021 disposes of the setting. Flagged
  rather than removed (residual register **R2**).
- 🔴 **No rate limiting, quota or token budget**; nothing bounds a turn beyond
  `MAX_LOOP_ITERATIONS = 6`. `Q-CO-9` derives that a quota is not needed *before
  public exposure*, which has not happened — so the underlying question is
  deferred, not answered. Kept 🔴.
- 🟢 **`created_by` vocabulary is fixed to `human` | `ai`** (`Q-CC-9`,
  maintainer-answered), and reuse no longer keys on it at all — `Q-CO-12`
  replaces the string match with a typed `branch_kind` column.
- 🟢 **Duplicate proposal branches become impossible and a human rename is
  harmless** (`Q-CO-12`): a partial unique index enforces at most one open
  proposal per `root_id`, and the typed column replaces `name LIKE
  'copilot-proposal%'`.
- 🟢 **Prompt rules that protect a number move into the tool** (`Q-CO-11`,
  maintainer-answered): *"whatever protects a number is enforced in the tool, not
  requested in the prompt."* The physics direction checks and the
  never-mix-data-sources rule stop being prose.
- 🟡 **`_metrics_payload` is a `_`-prefixed private function imported by three
  call sites** across two modules; its name promises an instability its callers
  cannot tolerate.
