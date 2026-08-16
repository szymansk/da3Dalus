# copilot-provenance — Implementation Tasks

> Executable sequence to re-implement the use case from the legacy behaviour.
> Every task cites the legacy file, a definition of done, and a confidence
> marker. Parent module tasks: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `branches.created_by` and `aeroplanes.created_by` / `provenance_message_id`
      — see [`../tasks.md`](../tasks.md) T-01, T-02.
- [ ] `create_branch` and `discard_branch` — see
      [`../branch-model/tasks.md`](../branch-model/tasks.md) T-03, T-06.
- [ ] `snapshot` — see
      [`../snapshot-immutability/tasks.md`](../snapshot-immutability/tasks.md)
      T-02.
- [ ] `copilot_messages` table (for the FK) — module `ai-copilot`. May be empty.
- [ ] `put_wing_as_wingconfig` (the delete-then-reinsert write path) — module
      `wing-design`. Needed to reproduce the identity-map failure T-05 guards
      against.

## Tasks

- [ ] **T-01 — Record `created_by` on branches and heads.**
  `create_branch(db, from_node_id, name, created_by="human")` sets it on
  **both** the `BranchModel` and the cloned head. The REST layer passes
  `body.created_by or "human"`.
  - Legacy origin: `app/services/aeroplane_version_service.py:216, 220-226`;
    `app/api/v2/endpoints/versioning.py:159`
  - Definition of done: a branch and its head carry the same value; omitting the
    field yields `"human"`.
  - Confidence: 🟢

- [ ] **T-02 — Record `"human"` on the `main` branch at aeroplane creation.**
  - Legacy origin: `app/services/aeroplane_service.py:75-100`
  - Definition of done: a new aeroplane's main branch has
    `created_by == "human"` and `is_main == True`.
  - Confidence: 🟢 · owned by `aeroplane-core`; verify from this side too.

- [ ] **T-03 — Record `"human"` on every snapshot node (characterisation).**
  `snapshot_node.created_by = "human"`, unconditionally.
  - Legacy origin: `app/services/aeroplane_version_service.py:172`
  - Definition of done: a snapshot taken through the copilot path **and** one
    taken by `spar_insert_service` both record `"human"`. The test's docstring
    names the gap; do not parametrise the value here — that is a product
    decision.
  - Confidence: 🟢

- [ ] **T-04 — `provenance_message_id` storage.**
  Accepted by `SnapshotRequest`, assigned in `snapshot`, returned on
  `VersionNode`.
  - Legacy origin: `app/services/aeroplane_version_service.py:171`,
    `app/schemas/versioning.py`
  - Definition of done: the value round-trips request → column → response.
    Record that **nothing reads it back** — no route, tool or query resolves a
    snapshot to its conversation turn.
  - Confidence: 🟢

- [ ] **T-05 — `get_or_open_proposal`.**
  ```
  root_id = node.root_id or node.id
  reuse the FIRST branch WHERE root_id = root_id
                           AND is_main = False
                           AND created_by = 'copilot'
                           AND name LIKE 'copilot-proposal%'
  else create_branch(from the LIVE head,
                     name='copilot-proposal[-<message_id>]',
                     created_by='copilot')
  ```
  - Legacy origin: `app/services/copilot_apply_service.py:107-241`
  - Definition of done: two consecutive calls yield **one** branch; a branch
    named `copilot-proposal-17` is reused for a different message id (proving
    the `LIKE`); the live head's geometry is unchanged after the fork.
  - Confidence: 🟢 · owned by `ai-copilot`; the versioning-side contract is
    verified here.

- [ ] **T-06 — `discard_open_proposal` with the identity-map reset.**
  `db.flush()` → `db.expunge_all()` → **re-resolve** the branch →
  `discard_branch`.
  - Legacy origin: `app/services/copilot_apply_service.py`
  - Definition of done: a test that (a) applies an edit through
    `put_wing_as_wingconfig`, (b) discards the proposal, and (c) asserts **no**
    `InvalidRequestError` is raised. A variant without `expunge_all()` must
    fail — that failure is the reason the line exists. The re-resolve is also
    required: the previously loaded branch object is detached after the expunge.
  - Confidence: 🟢

- [ ] **T-07 — Read-tool retargeting.**
  While a proposal is open, read tools resolve `branch.head_id` rather than the
  live aeroplane id.
  - Legacy origin: `app/services/copilot_apply_service.py` / `copilot_tools`
  - Definition of done: after an AI edit, a read reflects the pending change
    while `GET /aeroplanes/{live_uuid}` does not.
  - Confidence: 🟢 · owned by `ai-copilot`.

- [ ] **T-08 — `_metrics_payload`.**
  `id`, `uuid`, `name`, `total_mass_kg`; `assumption_computation_context`
  **only when non-empty**; `wing_count`; `wing_names[]`;
  `wings[{name, n_xsecs}]`; `fuselage_count`; `stability` from
  `stability_results[-1]` when present.
  - Legacy origin: `app/services/aeroplane_version_service.py:74-117`
  - Definition of done: `wing_names` and `n_xsecs` are present (gh-938 — without
    them the model edits the wrong wing or an invalid index); an empty context
    **omits the key** rather than emitting `null`; a node with no stability
    results omits `stability`.
  - Confidence: 🟢

- [ ] **T-09 — Keep adoption human-only.**
  No copilot code path may call `adopt_branch`.
  - Legacy origin: ADR 0007; the absence of the call in
    `copilot_apply_service` / `copilot_tools`
  - Definition of done: a static test (import-graph or source grep) asserts
    `adopt_branch` is referenced only by `app/api/v2/endpoints/versioning.py`
    and the tests. This is the enforcement of the module's central safety
    property.
  - Confidence: 🟢

- [ ] **T-10 — Exclude `copilot_messages` from the clone, with its reason.**
  `EXCLUDED_TABLES["copilot_messages"] = "conversation excluded; provenance
  captured via note + cursor"`.
  - Legacy origin: `app/services/aeroplane_clone_service.py:105`
  - Definition of done: the reason string is reproduced verbatim — it is the
    statement that makes `provenance_message_id`'s unreadability a gap rather
    than a design choice.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Provenance values:** main branch `"human"` · REST default
      `"human"` · explicit `"ai"` accepted and stored · copilot `"copilot"`.
- [ ] **TT-02 — Head inherits its branch's `created_by`.**
- [ ] **TT-03 — Snapshot author (characterisation):** always `"human"`, even via
      the copilot and via `spar_insert_service`.
- [ ] **TT-04 — Cursor round-trip:** `provenance_message_id` request → column →
      response; and a test documenting that **no** read path resolves it.
- [ ] **TT-05 — Proposal reuse:** two AI edits ⇒ one branch; a suffixed name is
      reused; a renamed branch is **not** reused and a second proposal opens
      (characterisation).
- [ ] **TT-06 — Live-head isolation:** the live aeroplane is byte-identical
      before and after an AI edit, and after a discard.
- [ ] **TT-07 — Discard sequence:** with `put_wing_as_wingconfig` in the same
      session, the discard succeeds; without `expunge_all()` it raises
      `InvalidRequestError`.
- [ ] **TT-08 — Re-resolve after expunge:** using the pre-expunge branch object
      raises a detached-instance error.
- [ ] **TT-09 — Read retargeting:** the copilot sees its own pending edits.
- [ ] **TT-10 — Metrics payload:** `wing_names` · per-wing `n_xsecs` · omitted
      empty context · omitted `stability` · `stability` from the last row
      (characterisation).
- [ ] **TT-11 — Adoption is human-only:** the static reference test of T-09.
- [ ] **TT-12 — Duplicate proposals (characterisation):** with two matching
      branches, the first is used and the second is silently ignored.
- [ ] **TT-13 — `_metrics_payload` importers:** the three cross-module imports
      still resolve — a rename would break `copilot_apply_service` and
      `copilot_tools` despite the `_` prefix.

## Data Migration Tasks

- [ ] **TM-01 — `created_by` is backfilled to `"human"` for pre-existing
      aeroplanes** by the gh-903 migration's branch backfill. 🟢
- [ ] **TM-02 — Legacy `aeroplanes.created_by` stays `NULL`.** The migration
      does not backfill the node-level column, so "who made this" has three
      answers: `"human"`, `"copilot"`, and `NULL`. 🟡 Decide whether to
      backfill before relying on the column.
- [ ] **TM-03 — `provenance_message_id` stays `NULL` on every pre-existing
      row.** Nothing back-derives it. 🟢

## Suggested Order

1. **T-01 → T-04** — the columns and their writers. All four are small and
   independent, and T-03/T-04 are characterisations that should be written
   *before* anyone is tempted to "fix" the hard-coded value or wire up the
   cursor.
2. **T-08** next: `_metrics_payload` is a pure function over a loaded node, is
   imported by three modules, and is the contract the copilot's before/after
   comparison depends on.
3. **T-05** once `create_branch` exists — the reuse query is the use case's
   central rule and needs a populated lineage to test.
4. **T-06** immediately after, with its **negative** test. The `expunge_all()`
   line looks removable until you have the failing variant beside it; write both.
5. **T-07** with the copilot's read tools, in `ai-copilot`.
6. **T-09 → T-10** last: the static adoption test and the exclusion reason are
   guardrails rather than behaviour, and they are easiest to assert once
   everything they protect exists.

## Pending Gaps

- **What is the `created_by` vocabulary?** Four writers produce `'human'`,
  `'copilot'` and (documented but unwritten) `'ai'`, plus `NULL` on legacy rows.
  An enum plus a backfill would close it — but the value set is a product
  decision.
- **Should a snapshot record its true author?** Today every snapshot says
  `"human"`, including copilot-triggered and automatic ones — the exact
  distinction the provenance layer exists to make.
- **Should `provenance_message_id` be readable?** It is the documented
  substitute for cloning the conversation, and nothing resolves it. Options: a
  route on the version node, a field on `VersionNode` expanded to the message
  text, or a copilot tool.
- **Should a proposal branch be identified by a flag rather than a name
  prefix?** A human rename currently orphans the proposal and causes a second
  one to open.
- **Should duplicate proposals be detected?** `get_or_open_proposal` takes the
  first match and reports nothing.
- **Should `_metrics_payload` be promoted to a public, versioned contract?**
  Three modules import a `_`-prefixed function.
- **Should `_metrics_payload` order stability results by `computed_at`** rather
  than taking the last inserted row?
- **Should AI activity be measured** — proposals opened, discarded, adopted?
  Nothing counts them today.
