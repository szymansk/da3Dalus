# copilot-provenance — Technical Design

> Use-case design, nested under the module [`versioning`](../design.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Full endpoint contract: [`../contracts.md`](../contracts.md).

## Interface

### Provenance columns 🟢

| Column | Table | Type | Written by |
|---|---|---|---|
| `created_by` | `branches` | String? | `create_aeroplane` (`"human"`), REST `BranchRequest` (`"human"` default), `copilot_apply_service` (`"copilot"`) |
| `created_by` | `aeroplanes` | String? | `create_branch` (the new head, from its branch), `snapshot` (hard-coded `"human"`) |
| `provenance_message_id` | `aeroplanes` | Integer? FK → `copilot_messages.id` (`use_alter`) | `snapshot` only |

Both columns gain a DB CHECK on the canonical vocabulary (`Q-CC-9`). 🟢

### Functions 🟢

| Symbol | File | Role |
|---|---|---|
| `_metrics_payload(node)` | `aeroplane_version_service.py:74` | the before/after contract; imported by three modules despite its `_` prefix |
| `get_or_open_proposal(db, live_aeroplane_id, message_id)` | `copilot_apply_service.py:107` | reuse-or-create the proposal branch |
| `discard_open_proposal(db, live_aeroplane_id)` | `copilot_apply_service.py` | flush → expunge → re-resolve → discard |

## Main Flow

### F1 — Provenance on creation 🟢

```
create_aeroplane                → BranchModel(name="main", is_main=True,
                                              created_by="human")
POST /aeroplanes/{id}/branch    → create_branch(..., created_by=body.created_by or "human")
                                   → branch.created_by AND new_head.created_by
copilot_apply_service           → create_branch(..., created_by="copilot")
snapshot()                      → snapshot_node.created_by = "human"   (hard-coded)
```

Four writers. `BranchRequest`'s docstring says `'human' | 'ai'`; the value
`'ai'` is written by the copilot path once the provenance link is wired (`Q-CO-1`, `Q-CC-9`). 🟢

### F2 — The proposal lifecycle (`copilot_apply_service.py:107-241`) 🟢

```
get_or_open_proposal(db, live_aeroplane_id, message_id):
    node    = resolve the live aeroplane
    root_id = node.root_id or node.id

    branch = FIRST branch WHERE root_id    = root_id
                            AND is_main    = False
                            AND created_by = 'copilot'
                            AND name    LIKE 'copilot-proposal%'
    if branch: return branch                       # ONE open proposal per lineage

    return create_branch(db,
                         from_node_id = <live head>,
                         name         = 'copilot-proposal[-<message_id>]',
                         created_by   = 'copilot')
```

Three properties worth preserving verbatim:

1. **The live head is the fork source**, never the edit target — ADR 0007's
   safety property in one line.
2. **The reuse query is a `LIKE`**, because the branch name may carry a
   message-id suffix.
3. **"A proposal is open" is derived**, not stored: there is no `is_proposal`
   column, so the four predicates *are* the definition. 🟢

### F3 — Discard (`discard_open_proposal`) 🟢

```
db.flush()
db.expunge_all()          # ← NOT cosmetic
branch = re-resolve the proposal branch
discard_branch(db, branch.id)
```

`apply_edits` calls `put_wing_as_wingconfig`, which performs a
**delete-then-reinsert in the same session**. That leaves stale
`WingXSecSpareModel` instances in SQLAlchemy's identity map; the subsequent
cascade delete inside `discard_branch` then raises

```
InvalidRequestError: Can't attach instance … another instance with key … is
already present in this session
```

`expunge_all()` clears the map, and the branch must be **re-resolved**
afterwards because the previously loaded object is now detached. 🟢

### F4 — Read-tool retargeting 🟢

While a proposal is open, the copilot's read tools resolve `branch.head_id`
instead of the live aeroplane id, so the model observes its own pending edits
rather than the unchanged live design. 🟢

### F5 — `_metrics_payload` (l.74-117) 🟢

```python
payload = {"id", "uuid", "name", "total_mass_kg"}
if node.assumption_computation_context:                 # omitted when empty
    payload["assumption_computation_context"] = ctx
payload["wing_count"]     = len(node.wings or [])
payload["wing_names"]     = [w.name for w in node.wings or []]          # gh-938
payload["wings"]          = [{"name": w.name,
                              "n_xsecs": len(w.x_secs or [])}           # gh-938 Bug A
                             for w in node.wings or []]
payload["fuselage_count"] = len(node.fuselages or [])
if node.stability_results:
    latest = node.stability_results[-1]                 # LAST row, not newest 🔴
    payload["stability"] = {static_margin_pct, is_statically_stable,
                            neutral_point_x, mac}
```

`wing_names` exists because the LLM otherwise guesses wing indices or ids;
`n_xsecs` exists because appending a cross-section at the tip means
`at_index = n_xsecs` (1-based). Both were added by gh-938 in response to
observed model errors. 🟢

## Alternative Flows

- **No open proposal:** one is created from the live head. 🟢
- **An open proposal with a different message-id suffix:** reused, thanks to the
  `LIKE`. 🟢
- **Two proposals somehow exist** (e.g. created out of band): the **first**
  match wins; nothing detects or reports the duplicate. 🟡 `create_branch`
  performs no name-collision check, so this is reachable.
- **A proposal branch renamed by a human** so it no longer starts with
  `copilot-proposal`: it stops being found, and the next AI edit opens a second
  proposal. 🔴
- **`created_by` manually set to `"ai"` through the REST body:** accepted and
  stored; nothing reads it, and the copilot's own reuse query would **not**
  match it. 🔴
- **A snapshot taken by the copilot or by `spar_insert_service`:** recorded as
  `"human"`. 🟢 Canonical vocabulary `human` | `ai` with a CHECK (`Q-CC-9`).
- **`provenance_message_id` pointing at a deleted message:** the FK is
  `use_alter`; nothing reads the value anyway. 🟡
- **Discarding a proposal after a wing replacement without `expunge_all`:**
  `InvalidRequestError`. 🟢 (the reason the call exists)
- **Adopting a proposal:** only through `POST /branches/{id}/adopt`, a human
  action. No copilot code path calls it. 🟢
- **Node with no wings / no stability results:** `wing_names` and `wings` are
  empty lists; `stability` is absent from the payload. 🟢

## Dependencies

- **[`branch-model`](../branch-model/design.md)** — `create_branch` and
  `discard_branch` are the primitives; the proposal is an ordinary branch with a
  naming convention.
- **[`snapshot-immutability`](../snapshot-immutability/design.md)** — the
  `provenance_message_id` cursor is written only by `snapshot`.
- **`ai-copilot`** — owns `copilot_apply_service`, `copilot_tools`,
  `copilot_messages` and the streaming surface. This use case owns only the
  versioning-side contract.
- **`aeroplane-core`** — writes `"human"` on the `main` branch at creation.
- **[`aeroplane-clone-subgraph`](../aeroplane-clone-subgraph/design.md)** —
  excludes `copilot_messages` from the clone *because* the note and cursor are
  meant to carry the provenance instead.
- **ADR 0007** — the propose/adopt separation.

## Identified Design Decisions

| Decision | Evidence | Confidence |
|---|---|---|
| The AI writes only to a branch; adoption is a human act | ADR 0007; `copilot_apply_service` | 🟢 |
| A proposal is a **derived** state (four predicates), not a column | the reuse query | 🟢 |
| Exactly one proposal per lineage, reused across turns | `get_or_open_proposal` | 🟢 |
| The branch name is prefix-matched so a message-id suffix is allowed | `LIKE 'copilot-proposal%'` | 🟢 |
| The identity map is explicitly cleared before the cascade delete | `expunge_all()` + re-resolve | 🟢 |
| 🟢 Conversation history is deliberately not cloned (`R2-10`… `R2-06`): the chat branches **only** on an explicit user action, so a copilot proposal — which clones a full subgraph — does not fork it | `EXCLUDED_TABLES["copilot_messages"]` | 🟢 (the cursor is unreadable 🔴) |
| `_metrics_payload` surfaces wing **names** and cross-section counts for the LLM | gh-938 | 🟢 |
| A private function is imported by three modules rather than promoted to a public contract | the `_` prefix + three importers | 🟢 (a 🟡 smell) |
| 🟢 `created_by` is fixed to the canonical `human` | `ai` vocabulary with a DB CHECK (`Q-CC-9`, maintainer-answered); agent detail moves to a separate field. | BR-VR15 | 🟢 ( gap) |
| A snapshot's author uses the canonical `human` \| `ai` vocabulary with a DB CHECK | `:172` | 🟢 (`Q-CC-9`) |

## Internal State

```
        NoProposal
            │  apply_design_edits → get_or_open_proposal
            │    create_branch(from the LIVE head,
            │                  name='copilot-proposal[-msg]',
            │                  created_by='copilot')
            ▼
          Open  ──────────────────────────────────────┐
            │  apply_design_edits again               │ read tools retarget
            │  → REUSES the matching branch           │ to branch.head_id
            │                                         │
            ├── discard_proposal ─────────────────────┘
            │     flush → expunge_all → re-resolve → discard_branch
            ▼
        NoProposal

        adopt_branch  ← a HUMAN action, never called by the copilot
```

The state lives entirely in the `branches` table; nothing else is persisted, and
there is no session-scoped or in-memory proposal registry. 🟢

## Observability

- `create_branch` and `discard_branch` log the ids, so a proposal's open and
  close both appear in the log — but as **ordinary branch operations**, with
  nothing marking them as AI activity beyond the branch name. 🟡
- `snapshot` logs its label, which for the automatic spar case is
  `"Before spar insert"` — the closest thing to an "automated action" marker in
  the module. 🟡
- Nothing counts AI-created branches, adoption rate, or how often a proposal is
  discarded rather than adopted — the metrics that would tell the maintainer
  whether the copilot is useful. 🔴
- `provenance_message_id` is stored but never queried, so the conversation → design
  link exists in the database and is invisible to every tool. 🔴

## Risks and Gaps

- 🔴 **`created_by` has four writers and three vocabularies.** `'human'` (two
  writers), `'copilot'` (one), `'ai'` (documented in the schema, never written).
  Any UI or query filtering on `'ai'` returns nothing.
- 🔴 **A snapshot's true author is unrecorded.** `snapshot` hard-codes
  `"human"`, so a copilot-triggered or automatic snapshot is
  indistinguishable from a user-taken one — precisely the distinction the
  provenance layer exists to make.
- 🔴 **`provenance_message_id` is write-only.** It is the documented substitute
  for cloning the conversation (`EXCLUDED_TABLES["copilot_messages"]`), yet no
  route, tool or query resolves it. The provenance chain is stored and broken.
- 🔴 **Renaming a proposal branch orphans it.** The reuse query matches on the
  name prefix, so a human rename silently causes the next AI edit to open a
  second proposal.
- 🔴 **Nothing detects duplicate proposals.** `create_branch` has no collision
  check, and `get_or_open_proposal` takes the first match — a second proposal
  would be silently ignored rather than reported.
- 🟡 **`_metrics_payload` is promoted to a public function** (`Q-VS-7`, derived): a `_`-prefixed private function imported by three call sites across two modules promises an instability its callers do not honour. Previously reads `stability_results[-1]`**, the last inserted row
  rather than the newest by `computed_at`, so the copilot may compare against a
  stale stability result.
- 🔴 **No AI-activity metrics.** Nothing counts proposals opened, discarded or
  adopted.
- 🟡 **A private function is a cross-module contract.** `_metrics_payload` is
  imported by `copilot_apply_service` and `copilot_tools` (twice); its `_`
  prefix promises an instability the callers cannot tolerate.
- 🟡 **`created_by` is nullable and unbackfilled**, so legacy rows carry `NULL`
  and a "who made this" query has a third, undocumented answer.
