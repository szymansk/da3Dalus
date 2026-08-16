# versioning — External Contracts

> REST contract read from `app/api/v2/endpoints/versioning.py` and
> `app/schemas/versioning.py`, cross-checked against `code-analysis.md`
> §Module: versioning. 🟢
> The router is mounted with `prefix=""` (`app/main.py:210`), so there is no
> `/api/v2` segment. 🟢
>
> **Id duality.** Every route in this module takes an **integer PK**, while the
> rest of the v2 API addresses aeroplanes by **UUID**. `_get_node_by_uuid`
> exists in the service and has no caller. 🔴

## Error contract 🟢

`_raise_http` (`versioning.py:49-60`) maps domain exceptions; the body is
FastAPI's bare `{"detail": exc.message}`, **not** the
`{"error": {code, message, details}}` envelope — 🟢 one envelope everywhere (`Q-CC-3`).

| Service exception | HTTP | Raised by |
|---|---|---|
| `NotFoundError` | 404 | unknown node or branch id |
| `ValidationError` | 422 | snapshot of an immutable node; restore from a mutable node; empty branch name |
| `ConflictError` | 409 | adopt an already-main branch; discard the main branch; discard the only branch; rename to a name used in the lineage |
| anything else | 500 | `_call`'s defensive fallback, `{"detail": "Unexpected error: …"}` |

`_call` does **not** log the catch-all branch. 🔴

## `POST /aeroplanes/{aeroplane_id}/snapshot` 🟢

| | |
|---|---|
| `operation_id` | `snapshot_aeroplane` |
| Path | `aeroplane_id: int` — the **integer PK** of the head node |
| Request | `SnapshotRequest` (`extra="forbid"`) |
| Response | `VersionNode` — the **new snapshot**, not the head |
| Status | **201** · 404 · 409 · 422 |

`SnapshotRequest`:

| Field | Type | Req. | Note |
|---|---|---|---|
| `label` | string | yes | `min_length=1`; e.g. `"Before spar insert"` |
| `note` | string \| null | no | why the snapshot was taken |
| `provenance_message_id` | int \| null | no | FK → `copilot_messages.id`; the AI cursor. **Write-only** 🟡 |

Semantics: the snapshot is inserted as the head's **predecessor**; the head
keeps its id, uuid and every inbound reference (BR-38). `created_by` on the
snapshot node is hard-coded `"human"` regardless of the caller. 🔴
422 when the target node is already immutable.

## `POST /aeroplanes/{aeroplane_id}/branch` 🟢

| | |
|---|---|
| `operation_id` | `create_branch` |
| Path | `aeroplane_id: int` — the source node; may be a **head or a snapshot** |
| Request | `BranchRequest` (`extra="forbid"`) |
| Response | `BranchOut` |
| Status | **201** · 404 · 422 |

`BranchRequest`: `name: string (min_length=1)`,
`created_by: string? = "human"` — the schema documents `'human' | 'ai'`, while
the copilot writes `"copilot"`. 🔴

Side effects: clones the source into a **mutable** head
(`predecessor_id = source.id`), creates the `BranchModel` row with
`is_main=False`, and back-fills the head's `branch_id`.
**No name-collision check** — duplicates within a lineage are reachable here and
only rejected by `PATCH`. 🔴

## `POST /branches/{branch_id}/adopt` 🟢

| | |
|---|---|
| `operation_id` | `adopt_branch` |
| Path | `branch_id: int` |
| Request | — |
| Response | `BranchOut` (the promoted branch) |
| Status | 200 · 404 · **409 when already main** |

Side effects: demotes the lineage's current main **first**, flushes, then
promotes — so the partial unique index never sees two `is_main=True`
(BR-VR7). The old main branch is kept, not deleted.

## `POST /aeroplanes/{snapshot_id}/restore` 🟢

| | |
|---|---|
| `operation_id` | `restore_snapshot` |
| Path | `snapshot_id: int` — must be an **immutable** node |
| Request | `BranchRequest` |
| Response | `BranchOut` |
| Status | **201** · 404 · **422 when the node is not immutable** |

The branch name defaults to `restore/<version_label>`, falling back to
`restore/<snapshot_id>` when the snapshot carries no label. Functionally
`create_branch` with an immutability requirement.

## `PATCH /branches/{branch_id}` 🟢

| | |
|---|---|
| `operation_id` | `rename_branch` |
| Request | `BranchRenameRequest{name: string (min_length=1)}` (`extra="forbid"`) |
| Response | `BranchOut` |
| Status | 200 · 404 · **409 on a per-lineage name collision** · 422 on an empty name after stripping |

The name is stripped of surrounding whitespace before both checks. Uniqueness is
**application-level only** — there is no DB constraint (BR-42).

## `DELETE /branches/{branch_id}` 🟢

| | |
|---|---|
| `operation_id` | `discard_branch` |
| Response | none — **204 No Content** |
| Status | **204** · 404 · **409 on the main branch or the only branch** |

Side effects, in this exact order (BR-VR9): null every inbound
`predecessor_id` pointing into the branch's nodes → delete the **branch row
first** → delete each node, letting the ORM cascade remove its owned subgraph.

🟡 Re-point predecessors instead of truncating (`Q-VS-6`). Today nodes are selected by `branch_id` alone; a surviving node whose
`predecessor_id` pointed into the discarded set keeps existing with a `NULL`
predecessor, silently truncating its lineage.

## `GET /lineages/{root_id}/tree` 🟢

| | |
|---|---|
| `operation_id` | `get_lineage_tree` |
| Path | `root_id: int` — the integer PK of the lineage-root aeroplane |
| Response | `TreeOut{root_id, nodes: TreeNodeOut[], branches: BranchOut[]}` |
| Status | 200 · 404 |

Nodes are `id == root_id OR root_id == root_id`, ordered by `id`; branches are
`root_id == root_id`, ordered by `id`. The endpoint computes
`is_head = node.id in {b.head_id for b in branches}`. 🟢

🟡 Orphaned `root_id` values are backfilled (`Q-VS-6`). Today a node whose `root_id` is `NULL` is invisible here even though it exists.

## `GET /aeroplanes/compare?a=&b=` 🟢

| | |
|---|---|
| `operation_id` | `compare_aeroplane_nodes` |
| Query | `a: int`, `b: int` — both **integer PKs**, both required |
| Response | `CompareOut{node_a, node_b, metrics_a, metrics_b}` |
| Status | 200 · 404 when either node is missing |

🟢 **One server-side diff engine serves both this endpoint and the copilot** (`R2-05`, ADR 0022). `Q-CO-6` commits to building a real live-vs-proposal diff; building it twice would give two answers to *"what changed?"*. The engine must know what `Q-VS-5` excludes (`construction_parts` are not cloned) so their absence is not reported as a change. Previously read-only: two payloads, no server-side diff.
Nothing requires `a` and `b` to share a lineage. 🟡

## Schemas 🟢

| Schema | Fields |
|---|---|
| `VersionNode` | `id`, `uuid`, `name`, `branch_id?`, `predecessor_id?`, `root_id?`, `is_immutable`, `version_label?`, `version_note?`, `created_by?`, `provenance_message_id?`, `preview_png?`, `created_at`, `updated_at` (`from_attributes=True`) |
| `TreeNodeOut` | `VersionNode` minus `preview_png` / `updated_at` / `provenance_message_id`, **plus `is_head: bool`** — bandwidth-trimmed for the tree view |
| `BranchOut` | `id`, `root_id`, `head_id`, `name`, `is_main`, `created_by?`, `created_at` |
| `TreeOut` | `root_id`, `nodes[]`, `branches[]` |
| `CompareOut` | `node_a`, `node_b`, `metrics_a?`, `metrics_b?` — free-form dicts |

### `_metrics_payload` — the comparison contract 🟢

A plain dict (`aeroplane_version_service.py:74`), not a Pydantic schema. It is
also imported by `copilot_apply_service` and `copilot_tools` despite its
`_` prefix.

| Key | Type | Source |
|---|---|---|
| `id`, `uuid`, `name`, `total_mass_kg` | int, str, str, float? | the node row |
| `assumption_computation_context` | dict | **only present when non-empty** — the whole gh-924 dict |
| `wing_count` | int | `len(node.wings)` |
| `wing_names` | list[str] | gh-938 — so the copilot targets a wing by **name** |
| `wings` | list[{`name`, `n_xsecs`}] | gh-938 Bug A — `at_index = n_xsecs` (1-based) appends at the tip |
| `fuselage_count` | int | `len(node.fuselages)` |
| `stability` | {`static_margin_pct`, `is_statically_stable`, `neutral_point_x`, `mac`} | `stability_results[-1]` — the **last** row, not the newest by timestamp 🔴; absent when there are no results |

## Related surface owned elsewhere 🟢

| Route | Owner | Note |
|---|---|---|
| `GET /aeroplanes?heads_only=true` | `aeroplane-core` | uses `list_aeroplanes_heads_only`; returns branch heads **plus** legacy `branch_id IS NULL` rows, enriched with `branch_name` and `is_main_branch` |
| `POST /aeroplanes` | `aeroplane-core` | bootstraps the lineage: `root_id = self`, a `main` branch, `created_by="human"` |
| `POST …/spar-insert` (commit) | `wing-design` | takes an automatic immutable snapshot labelled `"Before spar insert"` and **aborts the commit if it fails** (gh-1058); returns the snapshot id |
| copilot write tools | `ai-copilot` | operate exclusively on a `copilot-proposal` branch (ADR 0007) |

## Retired / dead surface 🟢 (removed — `Q-VS-3`, `P-DEAD-0`)

`/aeroplanes/{id}/design-versions` — five routes (`GET`, `POST`, `GET /{v}`,
`DELETE /{v}`, `diff`) are still registered
(`app/api/v2/endpoints/aeroplane/__init__.py:41`) and every one calls a
`design_version_service` stub that unconditionally raises `NotFoundError`. The
service header says *"TODO(gh-905): replace all functions below"*, but gh-905
shipped this `/lineages` + `/branches` surface instead. Callers receive a
plausible **404** rather than a 410 or 501. The
`DesignVersionCreate/Summary/Read/Diff` schemas survive in
`app/schemas/design_version.py` for import compatibility.

## Not part of this contract

- The meaning of the cloned data — wings, assumptions, stability results and the
  component tree belong to their owning modules.
- The copilot's proposal lifecycle beyond the branch primitives → `ai-copilot`.
- The lineage bootstrap on aeroplane creation → `aeroplane-core`.
</content>
