# ai-copilot

> Module-level specification. Focuses on WHAT the module does, not how.
> Confidence markers: 🟢 CONFIRMED (read from code) · 🟡 INFERRED · 🔴 GAP.
> Source artifacts: `_reversa_sdd/code-analysis.md` §Module: ai-copilot,
> `_reversa_sdd/data-dictionary.md` §Module: ai-copilot,
> `_reversa_sdd/domain.md` §2.7, `_reversa_sdd/state-machines.md` §4,
> `_reversa_sdd/permissions.md` §3, ADR 0004, ADR 0007, ADR 0009, ADR 0016.

## Overview

`ai-copilot` is the **in-app design assistant**: a streaming tool-calling loop
against an OpenAI-compatible LiteLLM hub, a persisted per-aeroplane chat thread,
a curated **6-tool** registry that computes every number in Python, and an apply
engine that writes design changes **only** to a disposable proposal branch. 🟢

It is deliberately the *least* capable actor in the system. It cannot adopt a
branch, delete anything, upload a file, run a construction plan or touch another
aeroplane — and the restriction is **structural** (there is no such tool), not
policy text. 🟢 (ADR 0007, `permissions.md` §3)

The module has **no dedicated persistence beyond `copilot_messages`**: every
design mutation it performs flows through the `versioning` module's branch
primitives, and every number it reports comes from `aero-analysis` or the
gh-924 computation context. 🟢

## Responsibilities

- Own `copilot_messages` — one flat, ordered chat thread per aeroplane. 🟢
- Run one **turn**: stream a completion, execute tools, loop, persist. 🟢
- Own the ~270-line `SYSTEM_PROMPT` that encodes the advisory policy. 🟢
- Own the **6-tool registry** and its `fn(db, aeroplane_id, **kwargs) -> dict`
  contract. 🟢
- Compute every reported number **server-side** (drag split, polar points,
  static margin). 🟢
- Own the 7-op **edit DSL** and the apply engine (`apply_edits`). 🟢
- Own the `copilot-proposal` branch lifecycle (open / reuse / discard). 🟢
- **Sanitise** every hub error before it can reach the browser. 🟢

**Explicitly NOT this module's responsibility:** branch/snapshot mechanics
(→ `versioning`), the solver itself (→ `aero-analysis`), wing-config
persistence (→ `wing-design`), the MCP tool surface (→ `mcp-server`), and
**adoption of a proposal**, which is a human-only action in the Versions panel
(ADR 0007).

## Business Rules

> `BR-43`…`BR-49` and `BR-78` are global ids reused verbatim from
> [`../domain.md`](../domain.md). `BR-CO*` are module-local.

### The provider boundary

- **BR-CO1 — The entire model-provider dependency is one factory function.** 🟢
  `_make_openai_client()` (`copilot_service.py:366`) builds an `AsyncOpenAI`
  client from `COPILOT_BASE_URL` / `COPILOT_API_KEY`, falling back to the
  literal `api_key="no-key"` so the module stays **import-safe** with no
  configuration. Its docstring is the contract: *"Tests monkeypatch
  `app.services.copilot_service._make_openai_client` … no real API call is ever
  made in CI."*
- **BR-CO2 — The wire protocol is plain OpenAI chat-completions with function
  calling.** 🟢 `client.chat.completions.create(model=settings.COPILOT_MODEL,
  messages=…, tools=…, tool_choice="auto", stream=True)`. The hub can therefore
  route to Claude, GPT, Gemini or a sovereign Qwen with **no code change**;
  `COPILOT_MODEL` defaults to `"claude-sonnet-4-6"`.
- **BR-48 — Secrets never reach the browser.** 🟢 `_sanitize_error`
  (`copilot_service.py:44`) replaces every literal occurrence of the configured
  API key with `[REDACTED]`, then substitutes a **category** message when the
  text mentions auth/key/token/secret/credential
  (`"<Type>: authentication or configuration error"`) or connectivity
  (`"<Type>: hub connection error"`). The endpoint's own catch-all is stricter
  still: the flat string `"Internal server error"`.

### The turn

- **BR-CO3 — `MAX_LOOP_ITERATIONS = 6`.** 🟢 Per iteration one completion is
  streamed; `finish_reason == "tool_calls"` executes the calls and continues,
  anything else ends the turn. Exhausting all six while the model still wants
  tools yields `done` with `truncated: true`.
- **BR-CO4 — Tool execution is off-loop.** 🟢
  `await asyncio.to_thread(copilot_tools.execute, …)`. The comment at l.609-612
  gives the reason: inside the worker thread there is **no running event loop**,
  which is exactly what lets `_run_analysis` call `asyncio.run(...)` for the
  async AeroSandbox coroutine.
- **BR-46 — A tool error is a return value, not an exception.** 🟢 Any exception
  from a tool becomes `{"error": str(exc)}` and the loop continues; the model
  self-corrects.
- **BR-49 — History replay must preserve tool-call pairing.** 🟢 (gh-922) A turn
  is persisted as **one** assistant row carrying both `tool_calls` and
  `tool_results`; `_history_to_openai` (`:396`) *reconstructs* the interleaved
  `tool` messages, emitting `{"error": "tool result unavailable"}` as a
  placeholder rather than dropping one — an orphaned `tool_use` makes the hub
  **400 on every turn after the first tool use**.
- **BR-CO5 — A malformed tool-argument payload is a protocol error, not an
  empty call.** 🟢 (Q-CO-2) A `json.JSONDecodeError` on the accumulated
  `arguments` string no longer sets `args = {}` with the tool **still
  invoked** — the tool implementation is not called at all. The loop reports
  `{"error": "Malformed tool call arguments: <decode error>"}` as the tool
  result and continues, so the model sees the call failed and can retry with
  valid JSON instead of a write tool silently running with no ops.

### The tools

- **BR-47 — The advisory tool surface is curated, not the full API.** 🟢
  `TOOL_REGISTRY` (`copilot_tools.py:828`) holds **6** entries — not the 76-tool
  MCP surface and not the ~230-route REST surface. The module header states the
  rule: *"only the tools that are safe, fast, and meaningful for an advisory
  interaction"*.
- **BR-CO6 — Tool contract.** 🟢 `fn(db, aeroplane_id, **kwargs) -> dict`,
  JSON-serialisable, errors returned as `{"error": …}`, **never raised**. Units
  are SI/metres — **except `get_wing_geometry`**, an intentional exception
  returning mm/degrees to mirror the edit-op units. 🟢 (Q-CO-11) The exception
  is no longer a docstring-and-`note` footnote: the tool's own schema carries
  an explicit unit field, so the mm-vs-SI split is declared in the contract
  itself, not left for an agent to miss (ADR 0019 — an implementation detail
  must not leak as an undocumented trap).
- **BR-CO7 — Read-retargeting (gh-938).** 🟢 `execute` resolves an *effective*
  target id before dispatch: for `{get_design_snapshot, get_wing_geometry,
  run_analysis}` it substitutes the open proposal's `branch.head_id`, so the
  copilot reads **its own edits** while iterating. `get_version_tree` and both
  write tools always receive the live id. 🟢 (Q-CO-3) A retarget-lookup
  failure is now **reported in the tool result** rather than swallowed —
  `except Exception: pass` is removed — and the failure is distinguishable
  from the legitimate "no proposal open" case, which still resolves to the
  live id without an error.
- **BR-45 / ADR 0004 — Numbers are computed in Python, never by the model.** 🟢
  `_drag_breakdown(cl, cd_total, ar, e)` computes
  `CD_i = CL²/(π·AR·e)` and `CD_parasite = CD_total − CD_i` because *"the LLM is
  unreliable at this arithmetic (it has produced both physically-impossible
  splits and 10x errors)"*.
- **BR-CO8 — An impossible split is reported, not fudged.** 🟢 (ADR 0012)
  `_drag_breakdown` returns `None` when an input is missing or
  `AR ≤ 0 / e ≤ 0 / CD_total ≤ 0`, and a **`note`-carrying dict with the raw
  inputs** when `cd_i < 0`, `cd_par < 0` or `cd_i > cd_total`.
- **BR-CO9 — One op-point, one neutral point (gh-924).** 🟢
  `_run_stability_async` evaluates at the **cruise design point**
  (α = 0, `v_cruise_mps` from the context, fallback 20 m/s) and then
  **overrides** the freshly computed neutral point with `ctx["x_np_m"]`,
  recomputing `SM = (x_np − cg_x)/MAC × 100` — because the two stability paths
  normalise `x_np` against different reference chords and a fresh run would
  surface a second divergent value (0.109 m vs the dashboard's 0.080 m). 🟢
  (Q-CO-11) When `x_np_m` is **absent** from the context, the tool no longer
  silently falls through to the solver's own neutral point — the single-source
  guarantee's own failure mode. It now emits a `DesignWarning`
  (`ASSUMPTION_KEY_MISSING`, category `input_missing`, severity `error`) per
  **P-WARN-0**, precisely the divergence gh-924 exists to prevent.
- **BR-CO10 — Analysis is time-boxed, and a timeout is a result.** 🟢
  `run_analysis` is wrapped in `asyncio.wait_for(…, DEFAULT_ANALYSIS_TIMEOUT_S =
  60.0)`; on expiry it returns `{"status": "timeout", "note": …}` so the model
  can tell the user to check the Analysis tab instead of erroring out.
- **BR-CO11 — `get_wing_geometry` reads the persisted frame, not a re-walk.** 🟢
  (gh-958) The `derived` block comes from `WingXSecModel.xyz_le` (metres × 1000)
  rather than being re-derived from the segments, which is what keeps it from
  diverging from the canonical `cad_designer` frame (that frame seeds the
  dihedral accumulator with the **root-airfoil** dihedral). Accumulated cant is
  recovered from the geometry itself as `atan2(Δz, Δy)` between consecutive LE
  points. Its `note` field carries a warning the schema cannot express:
  `chord_root_mm` is **read-only** — a segment's root chord follows the previous
  segment's tip chord, so tapering means setting `chord_tip_mm`.

### The edits

- **BR-CO12 — The edit DSL is a 7-member discriminated union on `type`.** 🟢
  `SetAssumption`, `SetXsec`, `SetSegment`, `AddXsec`, `RemoveXsec`,
  `SetWingParam`, `ReplaceWingConfig`. All chord/span fields are
  **millimetres**; angles are degrees.
- **BR-CO13 — The op schemas are inlined by hand.** 🟢 (gh-938)
  `edit_ops_array_schema()` builds an `anyOf` of every op's
  `model_json_schema()` because *"without them it guesses field names (span_mm,
  cant_deg, wing_index, …) and the ops get rejected"*. The op models are
  deliberately **flat** (no nested `BaseModel`) so each schema inlines without
  `$ref`s.
- **BR-CO14 — Station↔segment indexing.** 🟢
  ```
  n segments  ⇒  n + 1 cross-sections (stations)
  station 0        = root of seg[0]
  station i (0<i<n)= tip of seg[i-1] AND root of seg[i]   ← BOTH are written
  station n        = tip of seg[n-1]
  ```
  `SetXsec` addresses a **station** and touches both neighbours; `SetSegment`
  addresses a **segment** and touches only its tip airfoil.
- **BR-CO39 — `AddXsec` supports mid-wing insertion, not tip-append only.** 🟢
  (Q-CO-8) This is not a convenience: a trailing-edge device is defined over a
  **segment**, so a wing built without control surfaces has no segment
  boundary where one is wanted, and inserting a section mid-span is the only
  way to create one — steering the model to a tip-append cannot produce it.
  The inserted station becomes the **tip of the preceding segment and the
  root of the following one**, honouring the invariant that a new segment's
  root adopts the previous segment's tip. Chord, twist, airfoil and dihedral
  at the insertion station are **interpolated from the two neighbours** when
  not given, so inserting a section with no further arguments is geometrically
  a no-op that only adds a segment boundary. The tool description states this
  capability up front — the model no longer discovers the shape of the API
  through a rejection.
- **BR-CO15 — `RemoveXsec` accepts only interior stations** (`1 … n_xsecs−2`)
  and merges `seg[i-1]` with `seg[i]`: lengths added, **sweeps added**. 🟢
  (Q-CO-7) The sum is *correct*, not a bug — sweep is a chordwise **distance**
  along an invariant `xDir` (`app/schemas/wing.py:200-202`,
  `cad_designer/cq_plugins/wing/wing_segment.py:25-29`), so per-segment
  offsets are collinear and simply add: `sweep_merged = sweep_before +
  sweep_after`. The old "weighted avg" comment was wrong (that shape applies
  only if sweep were an *angle*, which it is not) and is replaced with the
  distance-invariant explanation, plus a `40 + 80 = 120 mm` regression test so
  it can never be "corrected" back to an average. The length sum
  (`length_merged = length_before + length_after`) is an approximation, exact
  only when the two segments share a dihedral: merging segments whose
  dihedral differs by **> 2°** now emits a `DesignWarning`
  (`geometry_simplified`, severity `notice`), escalating to `severity=warning`
  when the resulting span error exceeds 0.5 % (Δφ ≳ 11.5° for equal-length
  segments) — per **P-WARN-0**.
- **BR-CO16 — A bad op is rejected, not raised.** 🟢 `apply_edits` collects
  `applied: list[str]` and `rejected: list[{op, error}]` and never aborts the
  batch.
- **BR-CO17 — Geometry ops compose through a per-wing in-memory cache.** 🟢
  Ops mutate `wing_config_cache[wing]` (a mm dict) and the wing is written
  **exactly once** after the loop via `put_wing_as_wingconfig(…, scale=0.001)`.
  `ReplaceWingConfig` deliberately breaks the pattern: it validates and writes
  immediately, evicts the cache entry and calls `db.expire_all()`.
- **BR-CO18 — Two session-hygiene calls are load-bearing.** 🟢
  `db.expire_all()` after the wing writes, because `put_wing_as_wingconfig`
  deletes-then-reinserts and stale `WingModel` identities would make the metrics
  payload (and a same-turn `get_wing_geometry`) read **pre-edit** geometry;
  `db.expunge_all()` in `discard_open_proposal`, whose docstring names the exact
  failure it prevents — `InvalidRequestError: Can't attach instance
  <WingXSecSpareModel …>; another instance with key (…) is already present`.
- **BR-CO19 — A tip-append strips `tip_type` from every trailing segment.** 🟢
  (`copilot_apply_service.py:517-520`) `create_wing_configuration()` splits
  segments into a middle pass (`tip_type is None`) and a tip pass; leaving
  `tip_type="flat"` on the old last segment would process the new winglet first
  and **physically reorder the cross-sections**.
- **BR-CO20 — Recompute after apply is non-fatal.** 🟢
  `recompute_assumptions(db, proposal_uuid)` runs synchronously at the end and
  only `logger.warning`s on failure.

### The proposal

- **BR-43 / ADR 0007 — The copilot proposes; only a human adopts.** 🟢
  Write tools operate exclusively on a `copilot-proposal` branch. There is
  deliberately **no adopt tool**.
- **BR-44 — At most one open proposal per aeroplane, structurally enforced.**
  🟢 (Q-CO-12) `get_or_open_proposal` reuses the open branch matching
  `root_id=? AND branch_kind='proposal'`; otherwise it calls
  `create_branch(from_node_id=live_id, name="copilot-proposal",
  branch_kind='proposal', created_by='ai', created_by_agent='copilot')`.
  Lookup is by the typed `branch_kind` column (`Q-CC-9`'s enforcement level),
  not by `name LIKE 'copilot-proposal%'` string matching — **a human renaming
  the branch no longer orphans it**. A **partial unique index** on
  `root_id WHERE branch_kind='proposal'` (mirroring the existing "exactly one
  `is_main=true` per `root_id`" index) makes a **second** open proposal
  structurally impossible, replacing the old `id DESC`-takes-first behaviour
  that silently orphaned older proposals and their edits.
- **BR-CO40 — Provenance is wired: the proposal names its turn.** 🟢 (Q-CO-1)
  `get_or_open_proposal(db, live_id, message_id)` is now called **with** the
  id of the user message that triggered the edit; the branch carries it (the
  `-<message_id>` name suffix is no longer dead code) and
  `aeroplanes.provenance_message_id` is written by `snapshot()` as before —
  but now also **read**: a version can be resolved back to the conversation
  turn that produced it ("show me the chat that produced this version"). This
  makes ADR 0007's accountability story a mechanism, not just an intention,
  and stays unambiguous once conversations themselves branch (`Q-CO-5`).
- **BR-CO41 — An empty proposal closes itself; adopt-during-turn opens a new
  one.** 🟢 (Q-CO-12) A fully-rejected op batch (`applied` empty) no longer
  leaves an open branch with no changes — the proposal is auto-discarded, so
  the UI never shows a proposal containing nothing. If the human adopts the
  open proposal to `main` **while a turn is in flight**, a subsequent write
  tool call in that same turn opens a **new** proposal cloned from the
  now-adopted state — this was already the de-facto behaviour once
  `is_main=False` stopped matching; it is now the specified, tested rule
  rather than an accident, preserving the ADR 0007 invariant that the AI never
  writes to `main` directly.
- **BR-CO21 — Two diffs, both real.** 🟢 (Q-CO-6) `compute_metrics_diff` is a
  pure helper over **13 hard-coded dot-paths** (`_DIFF_KEYS`): `mass_kg` from
  `total_mass_kg`, plus `span_m`, `aspect_ratio`, `cd0`, `e_oswald`, `ld_max`,
  `x_np_m`, `static_margin_pct`, `v_stall_mps`, `v_min_sink_mps`,
  `v_cruise_mps`, `cl_max`, `wing_area_m2`. `diff_proposal_branch` remains the
  proposal's **own** before/after, captured right after `get_or_open_proposal`
  so recompute drift on the live node cannot pollute it. `diff_vs_live` is no
  longer an alias of the same value: it is now a **genuine live-vs-proposal
  comparison** — the proposal's current metrics against a **freshly read**
  live-node payload at diff time — answering the question a reviewing human
  actually asks before adopting: *"what changes if I accept this?"* (ADR
  0007). Unchanged and both-missing keys are omitted in both diffs; output is
  `{label: {before, after, delta}}` rounded to 6 decimals. Once the field
  means what it says, the system-prompt paragraph warning the model off it is
  removed, and the diff becomes usable in the adopt/discard UI.
- **BR-CO22 — Provenance class is `'human' | 'ai'`; the specific agent is a
  separate detail field.** 🟢 (Q-CC-9, applied to this module together with
  Q-CO-12) `get_or_open_proposal` now writes `created_by='ai'` +
  `created_by_agent='copilot'` instead of the third vocabulary value
  `'copilot'`, matching the documented `'human' | 'ai'` class and a DB `CHECK`
  constraint. A UI filter on `'ai'` no longer misses copilot branches, and the
  class/detail split survives a second AI writer (e.g. an MCP agent) without
  breaking the filter again. (Cross-reference: `versioning` BR-VR15, which
  owns the `created_by` / `created_by_agent` columns and the backfill of
  legacy `NULL` rows to `'human'`.)

### Persistence

- **BR-CO23 — One flat thread per aeroplane, ordered by `sort_index`.** 🟢
  `append_message` computes the next index as `COUNT(*)` for that aeroplane. 🟢 Replaced by `created_at` + `id` ordering (`Q-CO-5`).
  Not collision-safe: two concurrent appends — or an append after a
  `delete_message` — produce duplicate or reused indices.
- **BR-CO24 — `clear_history` iterates a materialised list.** 🟢
  `list(aeroplane.copilot_messages)` — annotated as required to avoid mutating
  the collection during iteration.
- **BR-CO25 — The conversation is never cloned.** 🟢 `copilot_messages` is in
  `EXCLUDED_TABLES` with the reason *"provenance captured via note + cursor"*,
  so branching an aircraft does not copy its chat.
- **BR-78 / ADR 0009 — `get_db()` owns the transaction.** 🟢 Neither the
  service, the tools nor the apply engine ever commits.

### Rules that exist only in the system prompt 🟡

`SYSTEM_PROMPT` (~270 lines) is **executable policy with no code enforcement**:

| Rule | Enforcement |
|---|---|
| "Propose, never mutate the live design" | partly structural (no adopt tool) |
| Fresh before/after for performance numbers — L/D, `v_stall`, `v_cruise`, `v_min_sink` must come from `run_analysis`, never from a diff | none |
| Physics direction checks — lower mass ⇒ *all* characteristic speeds drop (V ∝ √(W/S)); a speed that rises must be flagged as an artifact | none |
| Never mix data sources — snapshot `cd0`/`e_oswald` must never be combined with the polar's `CD` | none |
| Static margin from one source; CG always derived (`x_CG = x_NP − SM_target × MAC`) | none |
| Audience rules — gloss MAC/AR/Re/Oswald e/SM/NP on first use, translate L/D into a glide ratio, lead with a plain-language takeaway | none |
| Proactive design warnings — winglet below ~2 m span (Re < ~80 000), taper < ~0.4 (tip stall, recommend 1–2° washout), `v_min_sink ≈ v_stall` within ~5 %, cruise < 1.2 × stall | none |
| Provisional knowledge tables — static-margin bands (RC trainer 15–25 %, sport 8–15 %, aerobatic 0–8 %, UAV 5–15 %, light GA 5–15 %), V_H bands, L/D benchmarks, first-flight CG — labelled *"until RAG is available"* | none |
| Reply in the user's language; UI chrome and code comments always English | none |

`{context_hint}` is interpolated per turn from the request body, e.g.
*"Active tab: Wing Editor · Aircraft: MyGlider"*. 🟢

### The context — freshness and compaction (Q-CO-14, Q-CO-15)

- **BR-CO36 — A reserved part of the turn's context is written by the system
  with current, valid aircraft state on every turn.** 🟡 (Q-CO-14 — direction
  set by the maintainer; the design is deferred, residual **R4**) Today the
  message list is `[system prompt] + [replayed history]`
  (`copilot_service.py:485-487`) and nothing re-injects current state: the
  model is not told the design changed and has no reason to suspect it, so it
  will reason and propose against geometry that no longer exists. The fix is
  architectural — one authority (ADR 0022 applied to the model's own context)
  for "what is the current state of this aircraft", rewritten unconditionally
  every turn, rather than relying on the model noticing it should re-fetch.
  What exactly is pinned (geometry summary, mass/CG, the aero context, open
  proposal status) is not decided.
- **BR-CO37 — Replayed history becomes an explicitly historical change
  record, not a state source.** 🟡 (Q-CO-14, residual **R4**) A raw replayed
  `get_wing_geometry` result satisfies neither goal it would need to: it reads
  as current when it is not, and it carries no causal information. What must
  survive replay is *what changed, from what, to what, and what that caused*
  — small, explicitly historical, distinct from the pinned block above.
  "Remove stale state" must **not** be implemented as "remove history": a
  model that cannot see the effect of its own edits (e.g. *"dihedral 3° → 4°;
  spiral margin 0.68 → 1.25"*) loses the trajectory that makes a second
  proposal better than the first. Whether the record derives from the version
  graph (`Q-CO-1`), from `DesignWarning` deltas, or from the aero context is
  not decided.
- **BR-CO38 — The change record is a byproduct of a goal/approval protocol,
  not a summary extracted from prose.** 🟡 (Q-CO-15 — direction recorded,
  design deferred, residual **R5**) Four structured event kinds replace
  generic conversation summarisation: a **quoted, verbatim** design goal
  agreed between the agent and the designer; a **change proposed** (a tool
  call against the proposal branch); an **approved/declined** decision (a
  quoted reason on decline); and a **result** as a diff derived from the
  version graph and the aero context — *"the discussion in between is
  irrelevant to a history."* The raw conversation is archived in full
  alongside the compacted record; compaction is a reduction, never a
  deletion. A goal must be made **measurable** during goal-agreement — the
  agent pushes back on an unquantified goal ("significantly reduce drag") and
  consults the domain-expert skills (`Q-CO-10`) both to offer a defensible
  numeric target and to run a plausibility check **before** a search starts
  (ADR 0023 — RC/UAV scale, not transport-category literature). **Approval
  attaches to the outcome of an autonomous search, not to each step**: the
  search runs on the proposal branch (ADR 0007), so an unapproved intermediate
  step has no live effect to approve. The search trajectory itself is *not*
  persisted — the live chat history already answers "what else did you try"
  while the session is fresh. Which changes require explicit approval versus
  which are self-evident from the proposal diff is deferred to implementation,
  with **approval fatigue** named as the failure mode to avoid.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Stream one copilot turn over SSE | Must | `POST /aeroplanes/{uuid}/copilot/stream` → 200 `text/event-stream` with `token` … `done` |
| RF-02 | Persist the user message **before** opening the stream | Must | A `NotFoundError` on an unknown aeroplane becomes a **404 before** any SSE byte is written |
| RF-03 | Persist the assistant message on `done` | Must | The row carries `content`, `tool_calls` and `tool_results` |
| RF-04 | Loop at most `MAX_LOOP_ITERATIONS = 6` | Must | A model that always requests tools ends with `done {truncated: true}` |
| RF-05 | Execute tools off the event loop | Must | A tool calling `asyncio.run(...)` does not raise "event loop already running" |
| RF-06 | Turn a tool exception into `{"error": …}` and continue | Must | The turn still completes with a `done` event |
| RF-07 | Reconstruct `tool` messages when replaying history | Must | A second turn after a tool use does **not** 400 at the hub |
| RF-08 | Redact the API key and categorise auth/connection errors | Must | No `error` event ever contains the configured key |
| RF-09 | Expose exactly 6 tools | Must | `TOOL_REGISTRY` has 6 entries; `list_schemas()` returns 6 function schemas |
| RF-10 | Retarget the three read tools to the open proposal head | Must | With a proposal open, `get_design_snapshot` returns the proposal's metrics |
| RF-11 | Always target the live node from write tools and `get_version_tree` | Must | `apply_design_edits` finds/opens the proposal from the **live** lineage |
| RF-12 | Compute the induced/parasite drag split in Python | Must | `CD_i = CL²/(π·AR·e)`; `CD_parasite = CD_total − CD_i` |
| RF-13 | Report an impossible split as a note, never as numbers | Must | `cd_i > cd_total` ⇒ a dict with `note` + the raw inputs |
| RF-14 | Evaluate stability at cruise and override `x_np` from the context | Must | The reported neutral point equals `ctx["x_np_m"]` |
| RF-15 | Time-box `run_analysis` at 60 s and return a `timeout` status | Must | On expiry the tool returns `{"status": "timeout", …}`, not an error |
| RF-16 | Return `get_wing_geometry` in mm/degrees with `editable` + `derived` blocks | Must | Both blocks present; `note` warns that `chord_root_mm` is read-only |
| RF-17 | Validate ops against the 7-member discriminated union | Must | An unknown `type` ⇒ `{"error": "Invalid ops payload: …"}` |
| RF-18 | Apply edits to the proposal branch only | Must | The live head's geometry is byte-identical after `apply_design_edits` |
| RF-19 | Collect `applied` / `rejected` per op | Must | One bad op does not prevent the others from applying |
| RF-20 | Compose multiple ops on one wing through the per-wing cache | Must | Two `SetSegment` ops on one wing produce **one** `put_wing_as_wingconfig` call |
| RF-21 | Expire the session after wing writes | Must | A same-turn `get_wing_geometry` reads post-edit geometry |
| RF-22 | Strip `tip_type` from trailing segments on a tip append | Must | The appended winglet is the last cross-section, not the first |
| RF-23 | Open at most one proposal branch per aeroplane and reuse it | Must | A second `apply_design_edits` reuses the same `branch_id` |
| RF-24 | Discard the proposal on request | Must | `discard_proposal` → `{"discarded": true}`; a second call → `{"discarded": false}` |
| RF-25 | Expunge before discarding | Must | The cascade delete does not raise `InvalidRequestError` |
| RF-26 | Compute two 13-key metrics diffs: the proposal's own before/after, and a fresh live-vs-proposal comparison | Must | Unchanged keys are omitted from each; deltas rounded to 6 decimals; the two diffs differ whenever the live node changed since the proposal was opened |
| RF-27 | Expose the chat thread over REST (get/append/clear/delete) | Must | 4 routes; see [`contracts.md`](contracts.md) |
| RF-28 | Never commit inside the service, tools or apply engine | Must | A rollback after a turn leaves no message and no proposal |
| RF-29 | Recompute assumptions after an apply, non-fatally | Should | A recompute failure logs a warning; `applied` is still returned |
| RF-30 | Forward the truncation flag to the client | Should | `done` carries `truncated: true` only when the loop hit its cap |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Security | The configured API key can never appear in a client-visible payload | `copilot_service._sanitize_error:44`; endpoint catch-all `copilot_stream.py:181` | 🟢 |
| Security | The copilot cannot mutate the live design — enforced by the absence of a tool, not by a check | `TOOL_REGISTRY` (6 entries); ADR 0007 | 🟢 |
| Correctness | Every reported number is computed in Python from a single source | `_drag_breakdown:242`, `_run_stability_async` (`x_np` override) | 🟢 |
| Correctness | A physically impossible result is surfaced, never silently replaced by a fallback | `_drag_breakdown` note-dict; ADR 0012 | 🟢 |
| Performance | Analysis is bounded at 60 s per call | `DEFAULT_ANALYSIS_TIMEOUT_S = 60.0` | 🟢 |
| Performance | CPU-bound tool work never blocks the event loop | `asyncio.to_thread(copilot_tools.execute, …)` | 🟢 |
| Reliability | A tool failure degrades the turn, never aborts it | BR-46; `apply_edits` `rejected[]` | 🟢 |
| Reliability | Replayed history is protocol-valid for both the OpenAI and Anthropic tool formats | `_history_to_openai:396` (gh-922) | 🟢 |
| Portability | Swapping the model provider requires no code change | `_make_openai_client` + `COPILOT_BASE_URL` / `COPILOT_MODEL` | 🟢 |
| Testability | No CI run ever calls a real hub | `_make_openai_client` docstring; `scripts/uat_copilot_driver.py` is the *only* real-hub path | 🟢 |
| Scalability | **No** rate limit, quota, token budget or cost accounting beyond `MAX_LOOP_ITERATIONS = 6` — **deliberately out of scope**: da3Dalus is a single-user desktop application (ADR 0024), the ngrok chain is the maintainer's own testing tool rather than a product surface, and the spend is the single user's own. Revisit if and when multi-user arrives. | Q-CO-9 (follows `Q-CC-1`) | 🟢 |
| Availability | The SSE endpoint holds the request-scoped session open for the whole turn (potentially minutes with two 60 s analyses). **Fixed:** the assistant message is now committed from its own session as soon as `done` fires, independent of the request-scoped session's lifetime — a client disconnect mid-stream no longer loses it (side effects, e.g. a proposal branch, already survived). **Deliberately not built:** heartbeat frames, proxy-timeout tolerance, resumable streams — the operating model is one user on one machine, so hardening against an intermediary that does not exist is out of scope; do not harden the software against a specific development state. | `copilot_stream.py:121-190`, `db/session.py:55`, Q-CO-4 | 🟢 |
| Security | No authentication; the tunnel is the trust boundary (ADR 0016) | — | 🟢 |

## Acceptance Criteria

```gherkin
Feature: The turn loop

  Scenario: A plain advisory turn streams text and completes
    Given an aeroplane with a copilot history
    When I POST a message to /aeroplanes/{uuid}/copilot/stream
    Then the response content type is text/event-stream
    And I receive one or more "token" events
    And the last event is "done" with status "ok"
    And an assistant message is persisted with that text

  Scenario: A tool-calling turn emits tool_call and tool_result
    Given the model requests get_design_snapshot
    When the turn runs
    Then a "tool_call" event carries {name, args}
    And a "tool_result" event carries {name, summary}
    And the persisted assistant row holds both tool_calls and tool_results

  Scenario: The loop cap is reported, not hidden
    Given a model that requests a tool on every iteration
    When the turn runs
    Then the "done" event carries truncated true

  Scenario: An unknown aeroplane fails before the stream opens
    When I POST to /aeroplanes/{unknown-uuid}/copilot/stream
    Then the response status is 404
    And no SSE body is produced

  Scenario: The hub key never leaks
    Given the hub raises an authentication error containing the API key
    When the turn runs
    Then the "error" event message contains neither the key nor the word it was embedded in
    And the message is the category text "authentication or configuration error"

  Scenario: A tool exception does not end the turn
    Given run_analysis raises
    When the turn runs
    Then the tool result is {"error": ...}
    And the turn still ends with "done"

  Scenario: Replayed history keeps tool pairing
    Given a persisted assistant row with one tool_call and one tool_result
    When a second turn replays the history
    Then every assistant tool_call is immediately followed by a matching tool message
    And a missing result is replaced by {"error": "tool result unavailable"}

Feature: Deterministic numbers

  Scenario: The drag split is computed, not narrated
    Given CL, CD_total, AR and e
    When _drag_breakdown runs
    Then CD_i equals CL^2 / (pi * AR * e)
    And CD_parasite equals CD_total - CD_i

  Scenario: An impossible split is reported as a note
    Given CD_i computed larger than CD_total
    When _drag_breakdown runs
    Then the result carries a "note" and the raw inputs
    And it carries no induced/parasite split

  Scenario: Degenerate inputs return nothing
    Given e = 0
    When _drag_breakdown runs
    Then the result is None

  Scenario: One neutral point per aircraft
    When run_analysis(kind="stability") runs
    Then the reported neutral point equals assumption_computation_context.x_np_m
    And the static margin is (x_np - cg_x) / MAC * 100

  Scenario: A slow analysis returns a timeout status
    Given the analysis exceeds 60 seconds
    When run_analysis runs
    Then the result is {"status": "timeout", ...}
    And it is not an error

Feature: Propose, never mutate

  Scenario: The first edit opens a proposal branch
    Given an aeroplane with no copilot proposal
    When apply_design_edits is called with a valid op
    Then a branch named "copilot-proposal" exists with branch_kind "proposal", created_by "ai", created_by_agent "copilot", and is_main false
    And the live head's geometry is unchanged

  Scenario: The second edit reuses the same branch
    When apply_design_edits is called again
    Then the returned branch_id is the same

  Scenario: Read tools follow the proposal
    Given an open proposal whose span differs from the live design
    When get_design_snapshot runs
    Then it returns the proposal's span

  Scenario: get_version_tree stays on the live lineage
    Given an open proposal
    When get_version_tree runs
    Then it returns the lineage of the live node

  Scenario: A bad op is rejected, the batch is not
    Given two ops where one names a non-existent wing
    When apply_design_edits runs
    Then "applied" holds the good op
    And "rejected" holds {op, error} for the bad one

  Scenario: Multiple ops on one wing are written once
    Given two SetSegment ops on the same wing
    When apply_design_edits runs
    Then put_wing_as_wingconfig is called exactly once for that wing

  Scenario: Discard removes the proposal
    Given an open proposal
    When discard_proposal runs
    Then the result is {"discarded": true}
    And the branch no longer exists
    When discard_proposal runs again
    Then the result is {"discarded": false}

  Scenario: There is no adopt tool
    When I enumerate TOOL_REGISTRY
    Then no tool adopts, promotes or merges a branch
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| The streaming turn loop with its 6-iteration cap (RF-01…RF-06) | Must | The module's only entry point |
| History replay with reconstructed `tool` messages (RF-07) | Must | Without it the hub 400s on every turn after the first tool use |
| Error sanitisation (RF-08) | Must | The only thing standing between the hub credential and the browser |
| The 6-tool registry and its return-value error contract (RF-09, RF-06) | Must | The curation *is* the security model |
| Read-retargeting (RF-10/RF-11) | Must | Without it the model iterates against data it did not write |
| Deterministic arithmetic (RF-12…RF-14) | Must | ADR 0004; the reason the tools exist at all |
| Proposal-branch confinement (RF-18, RF-23) | Must | ADR 0007 — the structural guarantee |
| Per-op rejection and the per-wing cache (RF-19/RF-20/RF-21) | Must | Composability and post-write correctness |
| The `tip_type` strip on tip append (RF-22) | Must | Otherwise the cross-sections physically reorder |
| The chat-history REST surface (RF-27) | Must | The UI cannot render a thread without it |
| No commit inside the module (RF-28) | Must | ADR 0009 |
| Mid-wing `AddXsec` (BR-CO39) | Must | 🟢 (Q-CO-8) A control surface needs a segment boundary a tip-append cannot create; no longer a "nice to have" |
| The 60 s analysis timeout (RF-15) | Should | Protects the turn; the model degrades gracefully without it |
| The metrics diff (RF-26) | Should | Informational; the system prompt forbids using `diff_proposal_branch` for performance numbers, but `diff_vs_live` is now real enough to inform adoption |
| Non-fatal recompute after apply (RF-29) | Should | Convenience; the next read recomputes anyway |
| Truncation flag (RF-30) | Should | UX only |
| A reserved, system-written "current state" context block (BR-CO36) | Should | 🟡 (Q-CO-14) Direction set, design deferred (residual R4); highest-leverage correctness fix once built |
| Structured goal/action/decision/result compaction (BR-CO38) | Should | 🟡 (Q-CO-15) Direction recorded, design deferred (residual R5) |
| An **adopt** tool | Won't | ADR 0007 — deliberately absent, and must stay absent |
| Embedding-based retrieval | Won't | 🟡 (Q-CO-10) Superseded by lexical retrieval (ripgrep + BM25 + link graph) over the domain-expert skill vaults — the "agentic expert panel" (gh-929) itself **stays planned**; `COPILOT_EMBEDDING_MODEL` is residual **R2**, flagged for the maintainer to drop |
| Message branching (`parent_id`) | Should | 🟡 (Q-CO-5) Stays planned — a version branch taken at a snapshot should let the conversation roll back too; `parent_id` becomes a real FK. Not yet built. |
| Rate limiting / cost accounting | Won't | 🟢 (Q-CO-9) Deliberately out of scope for a single-user desktop app; revisit if multi-user arrives |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/services/copilot_service.py` (652 l.) | `SYSTEM_PROMPT`, `run_turn`, `_history_to_openai`, `_sanitize_error`, `_make_openai_client` | 🟢 |
| `…:44` | `_sanitize_error` | 🟢 |
| `…:366` | `_make_openai_client` | 🟢 |
| `…:396` | `_history_to_openai` (gh-922) | 🟢 |
| `…:446` | `run_turn` (`MAX_LOOP_ITERATIONS = 6`) | 🟢 |
| `…:602-612` | JSON-decode → protocol-error fallback (Q-CO-2) + `asyncio.to_thread` dispatch | 🟢 |
| `app/services/copilot_tools.py` (902 l.) | `TOOL_REGISTRY` (6), `execute`, `list_schemas` | 🟢 |
| `…:242` | `_drag_breakdown` | 🟢 |
| `…:828` | `TOOL_REGISTRY` | 🟢 |
| `…:866` | `execute` + `_READ_RETARGETED_TOOLS` | 🟢 |
| `app/services/copilot_apply_service.py` (731 l.) | `get_or_open_proposal`, `apply_edits`, `discard_open_proposal`, `compute_metrics_diff` | 🟢 |
| `…:44` | `_DIFF_KEYS` (13 paths) | 🟢 |
| `…:107-241` | proposal lifecycle | 🟢 |
| `…:248` | `apply_edits` | 🟢 |
| `…:517-520` | the `tip_type` strip | 🟢 |
| `app/services/copilot_history_service.py` (99 l.) | `append_message`, `get_history`, `clear_history`, `delete_message` | 🟢 |
| `app/api/v2/endpoints/aeroplane/copilot_stream.py` | the SSE endpoint | 🟢 |
| `app/api/v2/endpoints/aeroplane/copilot_history.py` | 4 history routes + `_raise_http` / `_call` | 🟢 |
| `app/schemas/copilot_edits.py` | the 7-op union + `edit_ops_array_schema()` | 🟢 |
| `app/schemas/copilot_history.py` | `CopilotMessageWrite/Read`, `CopilotHistory` | 🟢 |
| `app/models/aeroplanemodel.py:818-844` | `CopilotMessageModel` | 🟢 |
| `alembic/versions/705e8e49ef47_add_copilot_messages_table.py` | the table | 🟢 |
| `app/core/config.py:34-45` | the four `COPILOT_*` settings | 🟢 (`COPILOT_EMBEDDING_MODEL` 🟡 unused — residual R2, belongs to the superseded RAG plan) |
| `scripts/uat_copilot_driver.py` | UAT harness against the **real** hub | 🟢 |
| `app/tests/test_copilot_apply_integration.py` (2 679 l.) + 7 more (5 483 l. total) | the test surface | 🟢 |
| `app/services/aeroplane_version_service.py` | `create_branch` / `discard_branch` / `_metrics_payload` | 🟢 owned by `versioning` |
