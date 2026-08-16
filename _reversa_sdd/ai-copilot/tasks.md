# ai-copilot — Implementation Tasks

> Executable sequence to re-implement the module from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker.
> Use-case task lists: [`copilot-turn-loop`](copilot-turn-loop/tasks.md) ·
> [`copilot-tools`](copilot-tools/tasks.md) ·
> [`proposal-adopt-discard`](proposal-adopt-discard/tasks.md).

## Prerequisites

- [ ] The `versioning` module: `create_branch`, `discard_branch` and
      `_metrics_payload` (`app/services/aeroplane_version_service.py`).
- [ ] The `wing-design` write path `put_wing_as_wingconfig(db, uuid, wing, cfg,
      scale=0.001)` and the persisted `WingXSecModel.xyz_le` (metres).
- [ ] `aero-analysis`: an AeroBuildup polar coroutine and a stability summary.
- [ ] `mission-and-sizing`: `design_assumptions_service`,
      `recompute_assumptions`, and `assumption_computation_context` carrying
      `x_np_m`, `aspect_ratio`, `e_oswald`, `v_cruise_mps`, `mac`, `cg_x`.
- [ ] `get_db()` request-scoped session owning the transaction (ADR 0009).
- [ ] `app/core/exceptions.py` with `NotFoundError` / `ServiceException`.
- [ ] The four `COPILOT_*` settings in `app/core/config.py` (+ `.env.example`).
- [ ] The `openai` package (`AsyncOpenAI`) — reachable but **never called in
      CI**.

## Tasks

- [ ] **T-01 — `copilot_messages` table + model.**
  `aeroplane_id` FK `ON DELETE CASCADE` (indexed), `sort_index` (Integer, def.
  `0`), `role` (String, no DB enum), `content` (String, def. `""`),
  `tool_calls` / `tool_results` (JSON, nullable), `parent_id` (plain Integer,
  **not** an FK), `created_at`. Relationship
  `AeroplaneModel.copilot_messages` ↔ `CopilotMessageModel.aeroplane`.
  - Legacy origin: `app/models/aeroplanemodel.py:818-844`,
    `alembic/versions/705e8e49ef47_add_copilot_messages_table.py`
  - Definition of done: the table is registered in the clone registry's
    `EXCLUDED_TABLES` with the reason *"provenance captured via note + cursor"*,
    and `test_aeroplane_clone_coverage` passes.
  - Confidence: 🟢

- [ ] **T-02 — `copilot_history_service`.**
  `append_message` (next `sort_index` = `COUNT(*)` for the aeroplane),
  `get_history` (ordered by `sort_index`), `clear_history` (iterating
  `list(aeroplane.copilot_messages)`), `delete_message`.
  - Legacy origin: `app/services/copilot_history_service.py` (99 l.)
  - Definition of done: reproduce the `COUNT(*)` index **and record it as a
    gap** — it is neither concurrency- nor delete-safe. The `list()` in
    `clear_history` is required (mutation during iteration) and must carry the
    comment.
  - Confidence: 🟢

- [ ] **T-03 — The provider factory.**
  `_make_openai_client()` returning `AsyncOpenAI`, using `COPILOT_BASE_URL` and
  `COPILOT_API_KEY.get_secret_value()` when set, and the literal `"no-key"`
  otherwise.
  - Legacy origin: `app/services/copilot_service.py:366`
  - Definition of done: importing the module with **no** configuration must not
    raise. The docstring states that tests monkeypatch this symbol and that no
    real API call is ever made in CI — carry it verbatim; it is the whole test
    strategy.
  - Confidence: 🟢

- [ ] **T-04 — `_sanitize_error`.**
  Replace every literal occurrence of the configured key with `[REDACTED]`;
  substitute `"<Type>: authentication or configuration error"` when the text
  mentions auth/key/token/secret/credential, and `"<Type>: hub connection
  error"` on connectivity markers; otherwise return the redacted raw text.
  - Legacy origin: `app/services/copilot_service.py:44`
  - Definition of done: a test raising an exception whose message *contains* the
    configured key produces an `error` event containing neither the key nor the
    raw text.
  - Confidence: 🟢

- [ ] **T-05 — `_history_to_openai` (gh-922).**
  For each assistant row carrying `tool_calls`, emit the assistant message and
  then **one `tool` message per call**, resolving content from
  `results_by_id[tc["id"]]["result"]` or the placeholder
  `{"error": "tool result unavailable"}`.
  - Legacy origin: `app/services/copilot_service.py:396`
  - Definition of done: a two-turn test where the first turn used a tool must
    produce a message list in which **every** assistant `tool_call` is
    immediately followed by a matching `tool` message — without this the hub
    400s on every turn after the first tool use.
  - Confidence: 🟢

- [ ] **T-06 — `run_turn`.**
  `AsyncGenerator[dict, None]`, `MAX_LOOP_ITERATIONS = 6`. Per iteration: stream
  one completion; accumulate text deltas and tool-call chunks **by `index`**;
  branch on `finish_reason` (`"stop"` or no tool-call chunks ⇒ complete;
  `"tool_calls"` ⇒ execute and continue). Yield `token`, `tool_call`,
  `tool_result`, `done`, `error`.
  - Legacy origin: `app/services/copilot_service.py:446`
  - Definition of done: a fake client that always requests a tool ends with
    `done {truncated: true}` after exactly 6 iterations; a plain text answer
    ends after 1.
  - Confidence: 🟢

- [ ] **T-07 — Off-loop tool dispatch.**
  `await asyncio.to_thread(copilot_tools.execute, name, db, aeroplane_id,
  **args)`; a tool exception becomes `{"error": str(exc)}` and the loop
  continues.
  - Legacy origin: `app/services/copilot_service.py:602-612`
  - Definition of done: a tool that calls `asyncio.run(...)` internally does
    **not** raise "asyncio.run() cannot be called from a running event loop" —
    carry the explanatory comment, it is the reason for the design.
    Reproduce the `json.JSONDecodeError → args = {}` fallback **and record it as
    a gap**: a truncated stream can call a write tool with no ops.
  - Confidence: 🟢

- [ ] **T-08 — `SYSTEM_PROMPT`.**
  ~270 lines with a `{context_hint}` placeholder. It encodes: propose-never-
  mutate; fresh before/after for performance numbers; physics direction checks
  (V ∝ √(W/S)); never mix data sources; static margin from one source with CG
  derived; audience/glossing rules; the proactive design warnings; the
  provisional knowledge tables labelled *"until RAG is available"*; and the
  language rule.
  - Legacy origin: `app/services/copilot_service.py` (`SYSTEM_PROMPT`)
  - Definition of done: the prompt is treated as **executable policy with no
    code enforcement** — every rule in it is listed in `requirements.md` as 🟡
    so a re-implementer knows which guarantees are prose only.
  - Confidence: 🟡

- [ ] **T-09 — `_drag_breakdown` and the polar helpers.**
  `CD_i = CL²/(π·AR·e)`, `CD_parasite = CD_total − CD_i`; `None` on a missing
  input or `AR ≤ 0 / e ≤ 0 / CD_total ≤ 0`; a **`note`-carrying dict with the
  raw inputs** on an impossible split. `_polar_drag_breakdown` picks the max-L/D
  point via `nanargmax(CL/CD)` and reads `aspect_ratio` / `e_oswald` from
  `assumption_computation_context`.
  - Legacy origin: `app/services/copilot_tools.py:242`
  - Definition of done: three tests — a correct split, a `None` case, and an
    impossible split that returns the note dict. Carry the comment explaining
    *why* (the LLM produced physically-impossible splits and 10× errors).
  - Confidence: 🟢

- [ ] **T-10 — `_run_polar_async` / `_run_stability_async`.**
  Polar: AeroBuildup over α ∈ [−10°, +15°], **26 points**, V = 20 m/s, h = 0;
  report `cl_max`, `cl_min`, `cd_min`, `cl_cd_max`, `drag_breakdown` and the
  four renamed characteristic points. Stability: evaluate at the cruise design
  point and **override** the neutral point with `ctx["x_np_m"]`, recomputing
  `SM = (x_np − cg_x)/MAC × 100`.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: a test asserts the returned neutral point **equals**
    `ctx["x_np_m"]` and not the solver's value — this is gh-924 / ADR 0004 in
    code. Carry the comment naming the 0.109 m vs 0.080 m divergence.
  - Confidence: 🟢

- [ ] **T-11 — `_get_wing_geometry` (gh-958).**
  `editable` per segment (mm/deg from the validated `WingConfig`) + `derived`
  per station from persisted `xyz_le` (m × 1000), plus
  `projected_semi_span_mm`, `tip_xyz_le_mm` and the `note`.
  Accumulated cant from `atan2(Δz, Δy)` between consecutive LE points.
  - Legacy origin: `app/services/copilot_tools.py` (`_get_wing_geometry`)
  - Definition of done: the derived block must **not** be re-walked from the
    segments — a test with a root-airfoil dihedral proves the persisted read
    matches `cad_designer` while a re-walk would not. The `note` states that
    `chord_root_mm` is read-only.
  - Confidence: 🟢

- [ ] **T-12 — `TOOL_REGISTRY`, `list_schemas`, `execute`.**
  Exactly 6 entries; `execute` resolves `_READ_RETARGETED_TOOLS =
  {get_design_snapshot, get_wing_geometry, run_analysis}` through
  `_effective_target_id`, everything else gets the live id; an unknown name
  returns `{"error": "Unknown tool …. Known tools: <sorted>"}`.
  - Legacy origin: `app/services/copilot_tools.py:828`, `:866`
  - Definition of done: `len(TOOL_REGISTRY) == 6`; a retarget test proves a read
    tool returns the **proposal's** numbers while `get_version_tree` returns the
    live lineage. Reproduce the `except Exception: pass` fallback **and record
    it as a gap**.
  - Confidence: 🟢

- [ ] **T-13 — `run_analysis` timeout.**
  `asyncio.wait_for(..., DEFAULT_ANALYSIS_TIMEOUT_S = 60.0)`; on expiry return
  `{"status": "timeout", "note": …}`.
  - Legacy origin: `app/services/copilot_tools.py`
  - Definition of done: a patched slow coroutine yields the timeout **status**,
    not an `{"error": …}` — the model must be able to tell the user to check the
    Analysis tab.
  - Confidence: 🟢

- [ ] **T-14 — The edit-op DSL.**
  Seven flat Pydantic models in a discriminated union on `type`; mm for lengths,
  degrees for angles; `edit_ops_array_schema()` emitting
  `{"type":"array","items":{"anyOf":[<7 inlined schemas>]}}`.
  - Legacy origin: `app/schemas/copilot_edits.py` (+ `:240`)
  - Definition of done: no `$ref` appears anywhere in the emitted schema (the
    models must stay flat — no nested `BaseModel`), and every op's field names
    are present. Carry the gh-938 comment explaining that the model otherwise
    invents `span_mm` / `cant_deg` / `wing_index`.
  - Confidence: 🟢

- [ ] **T-15 — `apply_edits` — the per-wing cache.**
  Mutate `wing_config_cache[wing]` (mm) per op; write each touched wing **once**
  after the loop via `put_wing_as_wingconfig(scale=0.001)`; collect `applied` /
  `rejected: [{op, error}]`; never raise for a single bad op.
  `ReplaceWingConfig` validates and writes immediately, evicts the cache entry
  and calls `db.expire_all()`.
  - Legacy origin: `app/services/copilot_apply_service.py:248`
  - Definition of done: two ops on one wing produce exactly **one**
    `put_wing_as_wingconfig` call; a bad op does not prevent the good ones.
  - Confidence: 🟢

- [ ] **T-16 — The station↔segment index contract.**
  `SetXsec` writes **both** neighbouring segments of an interior station;
  `SetSegment` touches only its tip airfoil; `AddXsec` is tip-append only
  (`at_index == n_xsecs`), rejecting interior indices with a steering message;
  `RemoveXsec` accepts `1 … n_xsecs−2` and merges lengths **and sweeps by
  addition**.
  - Legacy origin: `app/schemas/copilot_edits.py`,
    `app/services/copilot_apply_service.py`
  - Definition of done: an interior-station `SetXsec` changes two segments; the
    sweep sum in `RemoveXsec` is reproduced **and recorded as a gap** (the
    comment says "weighted avg").
  - Confidence: 🟢

- [ ] **T-17 — The `tip_type` strip on tip append.**
  Before appending, clear `tip_type` from **every** trailing segment.
  - Legacy origin: `app/services/copilot_apply_service.py:517-520`
  - Definition of done: a test appends a winglet to a 3-segment wing and asserts
    the new cross-section is **last**. Without the strip,
    `create_wing_configuration()` processes the tip pass first and physically
    reorders the cross-sections — carry the comment.
  - Confidence: 🟢

- [ ] **T-18 — `db.expire_all()` after the wing writes.**
  - Legacy origin: `app/services/copilot_apply_service.py` (the commented call)
  - Definition of done: a same-turn `get_wing_geometry` after an
    `apply_design_edits` returns **post-edit** geometry. Without the expire,
    `put_wing_as_wingconfig`'s delete-then-reinsert leaves stale `WingModel`
    identities and the metrics payload reads pre-edit values.
  - Confidence: 🟢

- [ ] **T-19 — `get_or_open_proposal` / `_find_open_proposal`.**
  Reuse the newest branch matching `root_id=? AND is_main=False AND
  created_by='copilot' AND name LIKE 'copilot-proposal%'` ordered by
  `id DESC`; otherwise `create_branch(from_node_id=live_id,
  name="copilot-proposal", created_by="copilot")`.
  - Legacy origin: `app/services/copilot_apply_service.py:107-241`
  - Definition of done: two consecutive applies return the same `branch_id`; the
    live head's geometry is byte-identical after both. Reproduce that
    `message_id` is accepted and **never supplied**, and record both that and
    the duplicate-tolerance as gaps.
  - Confidence: 🟢

- [ ] **T-20 — `discard_open_proposal`.**
  `db.flush()` → `db.expunge_all()` → re-resolve the branch → `discard_branch`.
  - Legacy origin: `app/services/copilot_apply_service.py`
  - Definition of done: discarding a proposal that contains spares does **not**
    raise `InvalidRequestError: Can't attach instance <WingXSecSpareModel …>`;
    the docstring naming that exact error is carried over.
  - Confidence: 🟢

- [ ] **T-21 — `compute_metrics_diff` + `_DIFF_KEYS`.**
  13 dot-paths; omit unchanged and both-missing keys; round to 6 decimals;
  output `{label: {before, after, delta}}`.
  - Legacy origin: `app/services/copilot_apply_service.py:44`
  - Definition of done: the **pre-edit** payload is captured right after
    `get_or_open_proposal` (fresh from the clone), never from the live node.
    Both `diff_proposal_branch` and the legacy alias `diff_vs_live` are
    returned, and the misleading alias is recorded as a gap.
  - Confidence: 🟢

- [ ] **T-22 — The SSE endpoint.**
  Persist the user message **first** (mapping `NotFoundError` → 404 *before* the
  stream opens), load history, resolve the integer PK, return a
  `StreamingResponse` with `Cache-Control: no-cache` and `X-Accel-Buffering:
  no`. Format events with `_sse_format`. Persist the assistant message on
  `done` inside its own `try/except` that only logs. Catch-all yields
  `error {"message": "Internal server error"}`.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/copilot_stream.py`
  - Definition of done: an unknown UUID returns a real **404 with no SSE body**;
    a hub failure returns 200 with an in-band `error` event.
  - Confidence: 🟢

- [ ] **T-23 — The four history routes.**
  `GET` (200), `POST` (**201**), `DELETE` collection (**204**), `DELETE`
  item (**204**), with the local `_raise_http` / `_call` pair.
  - Legacy origin: `app/api/v2/endpoints/aeroplane/copilot_history.py`
  - Definition of done: every error body is `{"detail": …}`, **not** the
    `{"error": {…}}` envelope — reproduce the divergence and record it as a gap
    (`platform-core`).
  - Confidence: 🟢

- [ ] **T-24 — Wire the settings.**
  `COPILOT_API_KEY` (`SecretStr | None`), `COPILOT_BASE_URL`, `COPILOT_MODEL`
  (`"claude-sonnet-4-6"`), `COPILOT_EMBEDDING_MODEL`.
  - Legacy origin: `app/core/config.py:34-45`
  - Definition of done: `.env.example` documents all four; the embedding model
    is marked **unused** — no embedding, vector store or RAG code exists.
  - Confidence: 🟢 (the embedding setting 🔴)

## Test Tasks

- [ ] **TT-01 — Turn completion:** a plain answer streams `token`* then
      `done {status:"ok"}` and persists one assistant row.
- [ ] **TT-02 — Tool turn:** `tool_call` + `tool_result` events; the assistant
      row carries both `tool_calls` and `tool_results`.
- [ ] **TT-03 — Loop cap:** 6 iterations then `done {truncated: true}`.
- [ ] **TT-04 — Pre-stream 404:** unknown UUID ⇒ 404 and **no** SSE body.
- [ ] **TT-05 — Key redaction:** an auth error containing the key produces the
      category message only.
- [ ] **TT-06 — Catch-all:** an unexpected generator exception produces exactly
      `"Internal server error"`.
- [ ] **TT-07 — History pairing:** every assistant `tool_call` is followed by a
      matching `tool` message; a missing result becomes the placeholder.
- [ ] **TT-08 — Off-loop dispatch:** a tool calling `asyncio.run` succeeds.
- [ ] **TT-09 — Arg decode failure:** malformed arguments ⇒ `args = {}` and the
      tool is still invoked (characterisation of the current behaviour; `Q-CO-2` requires it to stop).
- [ ] **TT-10 — Drag split:** correct split, `None` case, impossible-split note.
- [ ] **TT-11 — Stability override:** the reported `x_np` equals `ctx["x_np_m"]`.
- [ ] **TT-12 — Analysis timeout:** `{"status": "timeout"}`, not an error.
- [ ] **TT-13 — Retargeting:** read tools follow the proposal head;
      `get_version_tree` and both write tools do not.
- [ ] **TT-14 — Wing geometry:** mm/degrees; derived read from persisted
      `xyz_le`; the `note` present.
- [ ] **TT-15 — Op schema:** no `$ref`; all seven ops' field names present.
- [ ] **TT-16 — Proposal isolation:** after an apply the **live** head is
      byte-identical.
- [ ] **TT-17 — Reuse:** two applies return the same `branch_id`.
- [ ] **TT-18 — Partial rejection:** one bad op ⇒ `applied` + `rejected`.
- [ ] **TT-19 — Single write per wing:** two ops on one wing ⇒ one
      `put_wing_as_wingconfig`.
- [ ] **TT-20 — Tip append ordering:** the appended winglet is last.
- [ ] **TT-21 — Expire after write:** a same-turn read sees post-edit geometry.
- [ ] **TT-22 — Discard:** `{"discarded": true}` then `{"discarded": false}`; no
      `InvalidRequestError` with spares present.
- [ ] **TT-23 — Diff:** unchanged keys omitted; 6-decimal rounding; both diff
      fields identical.
- [ ] **TT-24 — No commit:** a rollback after a turn leaves no message and no
      proposal branch.
- [ ] **TT-25 — No adopt tool:** enumerating `TOOL_REGISTRY` finds nothing that
      promotes, adopts or merges a branch (the structural guarantee of
      ADR 0007).
- [ ] **TT-26 — History routes:** 200/201/204/204 and `{"detail": …}` bodies.

## Data Migration Tasks

- [ ] **TM-01 — Create `copilot_messages`** with the FK `ON DELETE CASCADE` and
      both indices (`ix_copilot_messages_id`,
      `ix_copilot_messages_aeroplane_id`).
- [ ] **TM-02 — Add `aeroplanes.provenance_message_id`** as a `use_alter` FK
      (`fk_aeroplanes_provenance_msg`) — owned by the gh-903 versioning
      migration, but it points here.
- [ ] **TM-03 — Register `copilot_messages` in `EXCLUDED_TABLES`** with a
      non-empty reason, or the clone-coverage test fails.

## Suggested Order

1. **T-01 → T-02** the thread first: every other piece reads or writes it, and
   the SSE endpoint's very first action is an append.
2. **T-03 → T-05** the provider boundary and the replay adapter. T-05 before
   T-06: without correct replay, every multi-turn test is meaningless.
3. **T-06 → T-07** the loop and its off-loop dispatch — the dispatch decision
   constrains what a tool may do, so it must exist before the tools.
4. **T-09 → T-13** the read tools, deterministic arithmetic **first**. These are
   pure and testable without a branch, and they are the module's reason to
   exist.
5. **T-14 → T-18** the DSL and the apply engine. T-14 (schema) before T-15
   (engine) before T-16/T-17 (index semantics), because the rejections the
   engine must produce are defined by the schema.
6. **T-19 → T-21** the proposal lifecycle and the diff, which need a working
   apply engine to be observable.
7. **T-12** wire the registry once both read and write tools exist, then
   **T-22 → T-23** the routes, then **T-08** the system prompt — last, because
   it is the only artefact that can be tuned without touching behaviour.
8. **T-24** settings any time; do it before T-03 if you prefer a green import.

## Pending Gaps (🔴)

- **Should a malformed tool-argument payload abort the call** instead of
  invoking the tool with `{}`? A truncated stream can currently call a write
  tool with no ops.
- **Should `_effective_target_id` surface a retarget failure** rather than
  silently reading the live design?
- **Should the turn survive a client disconnect** — persist the assistant
  message from a background task, or accept the loss?
- **How should `sort_index` be assigned** so that concurrent appends and deletes
  cannot collide?
- **Should `parent_id` be implemented or dropped?** The schema advertises
  message branching that nothing implements.
- **Should `provenance_message_id` be populated** by passing `message_id` into
  `get_or_open_proposal`, and should something read it back?
- **Should `diff_vs_live` be removed** now that its name is wrong, or should it
  actually diff against the live node?
- **Is `RemoveXsec`'s sweep behaviour a bug?** The comment says "weighted avg";
  the code sums.
- **Should mid-wing `AddXsec` be implemented**, or should the restriction be
  stated in the tool description instead of discovered through a rejection?
- **What limits a turn?** No rate limit, token budget, quota or cost accounting
  exists.
- **What is the `created_by` vocabulary?** The copilot writes `"copilot"` while
  the schema documents `'human' | 'ai'`.
- **Should duplicate proposal branches be prevented**, and what should happen
  when a human renames one (the `LIKE` reuse query stops matching)?
- **Which system-prompt rules deserve code enforcement?** "Never mix data
  sources" and the physics direction checks are the highest-value candidates.
- **Is `COPILOT_EMBEDDING_MODEL` dropped or implemented?** gh-929 superseded the
  RAG plan with an "agentic expert panel" that does not exist in the repository.
- **Should `_metrics_payload` be promoted to a public, stable contract?** Three
  call sites in two modules import a `_`-prefixed function.
