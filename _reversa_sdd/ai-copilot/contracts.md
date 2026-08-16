# ai-copilot — External Contracts

> Two contracts live here: the **HTTP surface** (one SSE route + four history
> routes) read from `app/api/v2/endpoints/aeroplane/copilot_stream.py` and
> `…/copilot_history.py`, and the **tool surface** the model sees, read from
> `app/services/copilot_tools.py`. 🟢
> Both routers are mounted through `aeroplane/__init__.py` with `prefix=""`
> (`app/main.py:211`), so there is no `/api/v2` segment. 🟢
>
> **Id duality.** The HTTP surface addresses aeroplanes by **UUID**; the tool
> surface receives the **integer PK**, resolved once by the endpoint
> (`copilot_stream.py:117`). The `versioning` routes the copilot ultimately
> drives are integer-PK too. 🟡

## Error contract 🟢

`copilot_history.py` defines its own `_raise_http` / `_call` pair, so its bodies
are FastAPI's bare `{"detail": …}` — **not** the
`{"error": {code, message, details}}` envelope of the global handlers. 🟢 One envelope everywhere; the per-module mappers are deleted (`Q-CC-3`, maintainer-answered).

| Service exception | HTTP | Note |
|---|---|---|
| `NotFoundError` | 404 | unknown aeroplane or message |
| `ValidationError` / `ValidationDomainError` | 422 | |
| `ConflictError` | 409 | not produced by this module today 🟡 |
| any other `ServiceException` | 500 | `{"detail": exc.message}` |
| anything else | 500 | 🟢 folds into the single `{"error": …}` envelope (`Q-CC-3`) |

The **stream** route is different: it maps errors to HTTP only *before* the
stream opens. Once the `StreamingResponse` has started, the status is already
200 and every failure is an in-band `error` **event**. 🟢

---

## `POST /aeroplanes/{aeroplane_id}/copilot/stream` 🟢

| | |
|---|---|
| `operation_id` | `copilot_stream` |
| Tag | `copilot` |
| Path | `aeroplane_id: UUID4` |
| Request | `CopilotStreamRequest` |
| Response | `StreamingResponse`, `media_type=text/event-stream` |
| Status | **200** (stream) · 404 (unknown aeroplane) · 422 (body) · 500 |
| Headers | `Cache-Control: no-cache`, `X-Accel-Buffering: no` |

`CopilotStreamRequest`:

| Field | Type | Req. | Default | Note |
|---|---|---|---|---|
| `message` | string | yes | — | the user turn |
| `context_hint` | string | no | `""` | interpolated into `{context_hint}` in the system prompt, e.g. `"Active tab: Wing Editor · Aircraft: MyGlider"` |

### Ordering guarantees 🟢

1. The **user message is persisted first**. A `NotFoundError` here becomes a
   real **404** before a single SSE byte is written — this is why the client can
   distinguish "unknown aircraft" from "the model failed".
2. The full history (including that message) is loaded.
3. The integer PK is resolved; a missing row is a second **404** guard.
4. Only then is the `StreamingResponse` returned.
5. On the `done` event the **assistant message is persisted** — inside its own
   `try/except` that only logs, so a persistence failure never breaks the
   stream.

### SSE event envelope 🟢

`_sse_format(event_type, data)` emits exactly:

```
event: <type>\n
data: <compact json, separators=(',',':')>\n
\n
```

| Event | Payload | Meaning |
|---|---|---|
| `token` | `{"text": str}` | assistant text delta |
| `tool_call` | `{"name": str, "args": object}` | a tool is about to run |
| `tool_result` | `{"name": str, "summary": object}` | the **full** tool return value |
| `done` | `{"status": "ok"}` · `{"status": "ok", "truncated": true}` | turn complete; `truncated` only when `MAX_LOOP_ITERATIONS = 6` was exhausted |
| `error` | `{"message": str}` | always sanitised — the category message from `_sanitize_error`, or the flat literal `"Internal server error"` from the endpoint's catch-all |

There is **no** `event: end`, no keep-alive/heartbeat comment frame and no
retry directive. The client detects completion from the `done` event or from
stream closure. 🟡

🟢 **A disconnect mid-stream no longer loses the turn** (`Q-CO-4`, maintainer-answered): the assistant row is committed in its own session as soon as the `done` event is produced, so a proposal branch can no longer exist with nothing recording why. No heartbeat and no resumable stream — that was explicitly rejected as hardening against a deployment this project does not have (ADR 0024). Previously: The generator is abandoned, the
`done` branch never runs, and `get_db()`'s commit — which happens only after the
response is fully consumed — never fires.

🟡 **The session is held for the whole turn**, which can be minutes when the
model calls `run_analysis` twice (60 s cap each).

---

## `GET /aeroplanes/{aeroplane_id}/copilot-history` 🟢

| | |
|---|---|
| `operation_id` | `get_copilot_history` |
| Path | `aeroplane_id: UUID4` |
| Response | `CopilotHistory{messages: CopilotMessageRead[]}` |
| Status | 200 · 404 · 409 · 422 · 500 |

Ordered by `sort_index`. 🟢

## `POST /aeroplanes/{aeroplane_id}/copilot-history` 🟢

| | |
|---|---|
| `operation_id` | `append_copilot_message` |
| Request | `CopilotMessageWrite` |
| Response | `CopilotMessageRead` |
| Status | **201** · 404 · 409 · 422 · 500 |

`sort_index` is assigned as `COUNT(*)` for the aeroplane. 🟢 **Fixed regardless of the branching work** (`Q-CO-5`): ordering moves to `created_at` + `id` (or a sequence). Today two concurrent
appends — or an append after a delete — produce duplicate or reused indices.

## `DELETE /aeroplanes/{aeroplane_id}/copilot-history` 🟢

| | |
|---|---|
| `operation_id` | `clear_copilot_history` |
| Response | none — **204 No Content** |
| Status | **204** · 404 · 500 |

Iterates `list(aeroplane.copilot_messages)` — the materialisation is required to
avoid mutating the collection during iteration. 🟢

## `DELETE /aeroplanes/{aeroplane_id}/copilot-history/{message_id}` 🟢

| | |
|---|---|
| `operation_id` | `delete_copilot_message` |
| Path | `aeroplane_id: UUID4`, `message_id: int` |
| Response | none — **204 No Content** |
| Status | **204** · 404 · 500 |

🟢 Deleting a message does **not** renumber `sort_index` — fixed by the same ordering change (`Q-CO-5`). Today the next append
reuses an index already in use.

## Schemas 🟢

| Schema | Fields |
|---|---|
| `CopilotMessageWrite` | `role: Literal["user","assistant","tool"]` (req.), `content: str = ""`, `tool_calls: list[dict] \| None`, `tool_results: list[dict] \| None`, `parent_id: int \| None` |
| `CopilotMessageRead` | `CopilotMessageWrite` + `id: int`, `created_at: datetime` |
| `CopilotHistory` | `messages: list[CopilotMessageRead]` (default `[]`) |

`tool_calls` / `tool_results` are typed `list[dict[str, Any]]` — the OpenAI wire
format is **not** modelled, so nothing validates that a `tool_call_id` in
`tool_results` matches one in `tool_calls`. 🟡
`parent_id` is accepted by the schema and stored, but no writer sets it and no
reader uses it. 🟡

---

# The copilot tool surface

> This is the contract between the module and the **model**, not between the
> module and a network client. `list_schemas()` returns these six OpenAI
> function-calling schemas verbatim; they are sent on every iteration with
> `tool_choice="auto"`. 🟢

## Universal tool contract 🟢

```
fn(db: Session, aeroplane_id: int, **kwargs) -> dict     # JSON-serialisable
```

- **Errors are return values**: `{"error": "<text>"}`. A tool never raises
  (BR-46); anything that escapes is caught by `run_turn` and converted.
- **Units are SI/metres** — with one deliberate exception,
  `get_wing_geometry`, which returns **mm and degrees** to mirror the edit-op
  units.
- **The session is caller-owned**; no tool commits (ADR 0009).
- **The aeroplane is fixed by the endpoint.** The model never chooses an
  aeroplane id, so it can never reach another aircraft.
- An unknown tool name returns
  `{"error": "Unknown tool 'x'. Known tools: apply_design_edits, …"}` — the
  list is included so the model can self-correct. 🟢

## Read-retargeting 🟢

| Tool | Target |
|---|---|
| `get_design_snapshot`, `get_wing_geometry`, `run_analysis` | the open proposal's `branch.head_id` when one exists, else the live id |
| `get_version_tree`, `apply_design_edits`, `discard_proposal` | always the **live** id |

🟡 The lookup is wrapped in `except Exception: pass`, so a retarget failure
silently degrades to the live node.

## `get_design_snapshot` 🟢

| | |
|---|---|
| Parameters | `{}` (none) |
| Returns | `_metrics_payload(node)` — the `versioning` module's dict |

| Key | Type | Note |
|---|---|---|
| `id`, `uuid`, `name`, `total_mass_kg` | int, str, str, float? | the node row |
| `assumption_computation_context` | object | **only when non-empty** — the whole gh-924 dict |
| `wing_count` | int | |
| `wing_names` | string[] | gh-938 — so the model targets a wing by **name** |
| `wings` | `[{name, n_xsecs}]` | gh-938 Bug A — `at_index = n_xsecs` appends at the tip |
| `fuselage_count` | int | |
| `stability` | `{static_margin_pct, is_statically_stable, neutral_point_x, mac}` | from `stability_results[-1]` — the **last inserted** row, not the newest by timestamp 🔴; absent when there are none |

## `get_wing_geometry` 🟢 (gh-958)

| | |
|---|---|
| Parameters | `{"wing": string}` — optional; defaults to the aircraft's single/main wing |
| Returns | `{editable: [...], derived: [...], projected_semi_span_mm, tip_xyz_le_mm, note}` |
| Units | **millimetres and degrees** (the documented exception) |

| Block | Per element | Fields |
|---|---|---|
| `editable` | one per **segment** | `chord_root_mm`, `chord_tip_mm`, `length_mm`, `sweep_mm`, `dihedral_rel_deg`, `incidence_deg`, `airfoil` — from the validated `WingConfig` |
| `derived` | one per **station** | `xyz_le_mm`, `chord_mm`, `twist_deg`, `accumulated_dihedral_deg`, `te_x_mm = LE_x + chord` — from the **persisted** `WingXSecModel.xyz_le` (m × 1000) |

The derived block is read from persisted geometry rather than re-walked from the
segments, which is what keeps it aligned with the canonical `cad_designer` frame
(that frame seeds the dihedral accumulator with the root-airfoil dihedral).
Accumulated cant is recovered as `atan2(Δz, Δy)` between consecutive LE points.

`note` carries a rule the schema cannot express: **`chord_root_mm` is
read-only** — a segment's root chord follows the previous segment's tip chord
(continuity), so tapering means setting `chord_tip_mm`.

## `run_analysis` 🟢

| | |
|---|---|
| Parameters | `{"kind": "polar" \| "stability"}` — **required**, `enum` |
| Timeout | `asyncio.wait_for(…, 60.0)`; on expiry returns `{"status": "timeout", "note": …}` |

`kind = "polar"` — AeroBuildup over α ∈ [−10°, +15°], **26 points**, V = 20 m/s,
h = 0. Returns `cl_max`, `cl_min`, `cd_min`, `cl_cd_max`, `drag_breakdown`, and
four characteristic points renamed for the model: `best_glide`, `min_drag`,
`cl_max_point`, `stall`.

`drag_breakdown` (from `_drag_breakdown`, computed in Python):

| Case | Result |
|---|---|
| all inputs present and `AR > 0`, `e > 0`, `CD_total > 0` | `{cd_induced, cd_parasite, …}` with `CD_i = CL²/(π·AR·e)`, `CD_parasite = CD_total − CD_i` |
| any input missing, or a degenerate `AR`/`e`/`CD_total` | `None` |
| physically impossible split (`cd_i < 0`, `cd_par < 0`, `cd_i > cd_total`) | a **`note`-carrying dict with the raw inputs** — never a wrong split |

`kind = "stability"` — evaluated at the **cruise design point** (α = 0,
`v_cruise_mps` from `assumption_computation_context`, fallback 20 m/s). The
freshly computed neutral point is **overridden** with `ctx["x_np_m"]` and the
static margin recomputed as `(x_np − cg_x)/MAC × 100`, so the app never shows
two divergent neutral points (gh-924, ADR 0004).

## `get_version_tree` 🟢

| | |
|---|---|
| Parameters | `{}` |
| Returns | nodes + branches for the **live** lineage (never retargeted) |

## `apply_design_edits` 🟢 — the only geometry write

| | |
|---|---|
| Parameters | `{"ops": [<7-member anyOf>]}` — **required** |
| Returns | `{branch_id, branch_uuid, applied[], rejected[], diff_proposal_branch, diff_vs_live}` |

The `ops` schema is built by `edit_ops_array_schema()` as an `anyOf` of every
op model's `model_json_schema()`, inlined without `$ref`s — because without the
explicit per-op fields *"it guesses field names (span_mm, cant_deg, wing_index,
…) and the ops get rejected"* (gh-938). 🟢

All chord/span fields are **millimetres**; angles are **degrees**.

| Op | Fields (required in **bold**) |
|---|---|
| `SetAssumption` | **`param`** (a `VALID_PARAMETERS` name — `mass`, `cg_x`, `target_static_margin`, `cd0`, `cl_max`, `g_limit`, …), **`value: float`** (SI or degrees) |
| `SetXsec` | **`wing`**, **`index ≥ 0`** (station), `chord > 0`, `twist`, `airfoil`, `dihedral` |
| `SetSegment` | **`wing`**, **`seg_index ≥ 0`**, `length_mm > 0`, `sweep_mm ≥ 0`, `chord_tip_mm > 0`, `dihedral_rel_deg`, `incidence_deg` |
| `AddXsec` | **`wing`**, **`at_index ≥ 1`**, **`chord > 0`**, **`span > 0`**, `airfoil`, `twist = 0`, `dihedral = 0` |
| `RemoveXsec` | **`wing`**, **`index ≥ 1`** (must be interior) |
| `SetWingParam` | **`wing`**, `sweep_mm`, `dihedral` — applied to **every** segment |
| `ReplaceWingConfig` | **`wing`**, **`wing_config`** (a full `WingConfigurationSchema` payload, mm) |

Index contract (the source of most rejections):

```
n segments  ⇒  n + 1 stations
station 0         = root of seg[0]
station i (0<i<n) = tip of seg[i-1] AND root of seg[i]   ← BOTH written
station n         = tip of seg[n-1]
```

Behaviour:

- The target is **always the proposal branch**, never the live head. The branch
  is opened on demand and reused (`copilot-proposal`, `created_by='copilot'`,
  `is_main=false`).
- A bad op never aborts the batch: it lands in
  `rejected: [{op, error}]` while the rest apply.
- `AddXsec` supports **tip-append only** (`at_index == n_xsecs`); an interior
  index is rejected with a message steering the model to a tip-append. 🟢 **Mid-wing insertion is implemented** (`Q-CO-8`): a control device is defined over a *segment*, so only a mid-span insert can create the segment boundary an aileron needs.
- `RemoveXsec` merges `seg[i-1]` with `seg[i]`: lengths added and **sweeps
  added** — the comment says "weighted avg". 🟢 **The sum is correct; the comment is wrong** (`Q-CO-7`): sweep is a chordwise distance along an invariant `xDir`.
- `diff_proposal_branch` is the proposal's **own** pre-edit vs post-edit over 13
  keys. `diff_vs_live` is a backward-compatible alias with the same value and a
  now-wrong name. 🟢 **A real live-vs-proposal diff replaces the alias** (`Q-CO-6`). Today the tool description instructs the model **not** to
  use either for performance comparisons (L/D, `v_stall`, `v_cruise`,
  `v_min_sink`) and to call `run_analysis` before and after instead.

## `discard_proposal` 🟢

| | |
|---|---|
| Parameters | `{}` |
| Returns | `{"discarded": true}` when a proposal existed, `{"discarded": false}` otherwise |

Internally: `flush()` → `expunge_all()` → re-resolve → `discard_branch`. The
expunge is required or the cascade delete raises
`InvalidRequestError: Can't attach instance <WingXSecSpareModel …>`. 🟢

## What the tool surface deliberately does **not** contain 🟢

No `adopt_branch` / promote / merge. No aeroplane create or delete. No wing or
cross-section delete. No file upload or download. No construction-plan
execution. No operating-point generation. No component/COTS CRUD. No access to
another aeroplane — the id is fixed by the endpoint (ADR 0007,
`permissions.md` §3).

## Configuration surface 🟢

| Setting | Default | Note |
|---|---|---|
| `COPILOT_API_KEY` | `None` | `SecretStr`; absent ⇒ the literal `"no-key"` placeholder keeps the module import-safe |
| `COPILOT_BASE_URL` | `None` | `None` ⇒ the OpenAI default endpoint |
| `COPILOT_MODEL` | `"claude-sonnet-4-6"` | any hub-routable id (`.env.example` lists ~30) |
| `COPILOT_EMBEDDING_MODEL` | `"text-embedding-3-large"` | 🟡 **dead** — belongs to the RAG plan that gh-929 superseded; under the lexical retrieval of `Q-CO-10` no embedding model is needed at all, so ADR 0021 disposes of it. Flagged rather than removed (residual register R2). No embedding/RAG code exists |

## Not part of this contract

- Branch/snapshot semantics, the clone engine and `_metrics_payload` itself →
  `versioning`.
- Wing-config validation and persistence → `wing-design`.
- The solver behind `run_analysis` → `aero-analysis`.
- `assumption_computation_context` and `recompute_assumptions` →
  `mission-and-sizing`.
- The 76-tool external agent surface → `mcp-server` (a different, unrelated tool
  registry).
