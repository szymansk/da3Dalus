# copilot-provenance

> Use-case specification, nested under the module
> [`versioning`](../requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.
> Sources: `app/services/copilot_apply_service.py:107-241`,
> `app/services/aeroplane_version_service.py:74-117, 172`,
> `app/services/aeroplane_service.py:75-100`,
> `app/schemas/versioning.py`, `_reversa_sdd/state-machines.md` §6-7,
> ADR 0007. Endpoint contract: [`../contracts.md`](../contracts.md).

## Overview

Who made this version — a person, or the AI? This use case covers the
**provenance layer** of versioning: the `created_by` column on both `branches`
and `aeroplanes`, the `provenance_message_id` cursor that ties a snapshot to a
conversation turn, and the copilot's proposal-branch lifecycle, which is the
only automated consumer of the branch primitives. 🟢

It is also the module's most inconsistent corner: four writers, three
vocabularies, no enum, and a cursor that nothing reads. 🔴

## Responsibilities

- Record `created_by` on every branch and on branch-head nodes. 🟢
- Record `provenance_message_id` on a snapshot as the AI cursor. 🟢
- Support the copilot's *one open proposal per lineage* rule. 🟢
- Keep the copilot's writes off the live head (ADR 0007). 🟢
- Expose `_metrics_payload` as the before/after contract the copilot compares
  against. 🟢

**NOT this use case:** the branch primitives themselves
(→ [`branch-model`](../branch-model/requirements.md)), the snapshot topology
(→ [`snapshot-immutability`](../snapshot-immutability/requirements.md)), and the
copilot's tools, streaming and conversation storage (→ `ai-copilot`).

## Business Rules

> Global ids from [`../../domain.md`](../../domain.md); `BR-VR*` from
> [`../requirements.md`](../requirements.md); `BR-CP*` are new here.

- **BR-43 / ADR 0007 — The copilot proposes; only a human adopts.** 🟢 Write
  tools operate **exclusively** on a `copilot-proposal` branch; the live head is
  never mutated by the AI. Adoption is `adopt_branch`, a human action.
- **BR-VR15 — Four writers, three vocabularies, no enum.** 🟢
  | Writer | Value written |
  |---|---|
  | `aeroplane_service.create_aeroplane` (the `main` branch) | `"human"` |
  | `aeroplane_version_service.snapshot` (the snapshot node) | `"human"` — **hard-coded** (`:172`) |
  | `versioning.py` REST (`BranchRequest.created_by`) | `"human"` by default; the schema documents `'human' \| 'ai'` |
  | `copilot_apply_service.get_or_open_proposal` | **`"copilot"`** |
  🔴 A UI filtering on `'ai'` misses every copilot branch; `'ai'` is documented
  and never written.
- **BR-CP1 — One open proposal per lineage.** 🟢 `get_or_open_proposal` reuses
  the **first** branch matching
  ```
  root_id = <lineage>  AND  is_main = False
                       AND  created_by = 'copilot'
                       AND  name LIKE 'copilot-proposal%'
  ```
  and only creates a new one when none exists.
- **BR-CP2 — The proposal branch name is prefix-matched, not exact.** 🟢
  `create_branch(name='copilot-proposal[-<msg_id>]')` — the optional message-id
  suffix means the reuse query must be a `LIKE`, not an equality test.
- **BR-CP3 — The proposal is a *derived* state, not a column.** 🟢 There is no
  `is_proposal` flag: "a proposal is open" means *a branch exists matching those
  four predicates*.
- **BR-CP4 — Discarding a proposal requires an identity-map reset.** 🟢
  ```
  discard_open_proposal(db, live_aeroplane_id):
      db.flush() → db.expunge_all() → re-resolve the branch → discard_branch
  ```
  The `expunge_all()` is **not** cosmetic: `apply_edits` calls
  `put_wing_as_wingconfig`, which does delete-then-reinsert in the *same*
  session, leaving stale `WingXSecSpareModel` instances in the identity map; the
  subsequent cascade delete then raises
  `InvalidRequestError: Can't attach instance … already present in this
  session`.
- **BR-VR16 — `provenance_message_id` is the AI cursor, and it is
  write-only.** 🟢 It is the id of the last `copilot_messages` row at snapshot
  time: accepted by `SnapshotRequest`, written by `snapshot()`, returned on
  `VersionNode` — and read by **nothing**. There is no route, tool or query that
  resolves a snapshot back to its conversation turn. 🔴
- **BR-VR6 — A snapshot always records `"human"`.** 🟢 Even one taken on the
  copilot's behalf or automatically by `spar_insert_service`. 🔴
- **BR-CP5 — `copilot_messages` is deliberately not cloned.** 🟢
  `EXCLUDED_TABLES["copilot_messages"] = "conversation excluded; provenance
  captured via note + cursor"` — the note and the cursor are the *intended*
  substitute for copying the conversation, which makes the cursor's
  unreadability the gap it is. 🔴
- **BR-CP6 — `_metrics_payload` is the copilot's before/after contract.** 🟢
  A private (`_`-prefixed) function imported by three other modules —
  `copilot_apply_service` and `copilot_tools` (twice). It carries `wing_names[]`
  and per-wing `n_xsecs` **specifically** so the LLM targets a wing by name and
  can compute a valid 1-based `at_index` for `AddXsec` (gh-938, Bug A:
  appending at the tip is `at_index = n_xsecs`).
- **BR-CP7 — Read tools retarget to the proposal head.** 🟢 Once a proposal is
  open, the copilot's read tools resolve `branch.head_id` rather than the live
  aeroplane, so the model sees its own pending edits.
- **BR-CP8 — `created_by` is nullable everywhere.** 🟢 Both columns are
  `String NULL`; a legacy row carries `NULL` and nothing backfills it. 🟡

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Record `created_by` on every branch | Must | A REST-created branch defaults to `"human"`; a copilot branch is `"copilot"` |
| RF-02 | Record `created_by` on a new branch head | Must | The cloned head carries the same value as its branch |
| RF-03 | Record `"human"` on the `main` branch at aeroplane creation | Must | A new aeroplane's main branch has `created_by == "human"` |
| RF-04 | Record `"human"` on every snapshot node | Must | Even a copilot-triggered or automatic snapshot records `"human"` (current behaviour) |
| RF-05 | Accept and store `provenance_message_id` on a snapshot | Must | It round-trips through `SnapshotRequest` → the column → `VersionNode` |
| RF-06 | Reuse the single open proposal branch per lineage | Must | Two consecutive `apply_design_edits` calls target **one** branch |
| RF-07 | Match the proposal branch by name prefix | Must | `copilot-proposal` and `copilot-proposal-42` are both reused |
| RF-08 | Create the proposal from the **live head**, never in place | Must | The live aeroplane's geometry is unchanged after an AI edit |
| RF-09 | Retarget read tools to the proposal head while it is open | Must | A read after an AI edit reflects the pending change |
| RF-10 | Discard a proposal with a flush + `expunge_all` + re-resolve | Must | Discarding after a wing edit does not raise `InvalidRequestError` |
| RF-11 | Leave the live head untouched when a proposal is discarded | Must | The live aeroplane is byte-identical before and after |
| RF-12 | Expose `_metrics_payload` with `wing_names` and per-wing `n_xsecs` | Must | Both present; `n_xsecs` equals `len(wing.x_secs)` |
| RF-13 | Omit `assumption_computation_context` when empty | Should | The key is absent, not `null` |
| RF-14 | Include the latest stability summary when results exist | Should | `stability` carries `static_margin_pct`, `is_statically_stable`, `neutral_point_x`, `mac` |
| RF-15 | Require a human action to adopt a proposal | Must | No copilot code path calls `adopt_branch` |

## Non-functional Requirements

| Type | Inferred requirement | Evidence in code | Confidence |
|------|----------------------|------------------|-----------|
| Safety | The AI can never write to the live design; every write lands on a branch a human must adopt (ADR 0007) | `copilot_apply_service:107-241` | 🟢 |
| Correctness | The identity map is reset before a cascade delete, because a same-session delete-then-reinsert leaves stale instances | `discard_open_proposal`'s `expunge_all()` | 🟢 |
| Correctness | One proposal per lineage, so successive AI turns accumulate rather than fork | the four-predicate reuse query | 🟢 |
| Usability | The metrics payload names wings and counts cross-sections so the model targets edits correctly (gh-938) | `_metrics_payload:97-104` | 🟢 |
| Traceability | A snapshot can carry the conversation cursor that produced it | `provenance_message_id` | 🟢 (unreadable 🔴) |
| Consistency | `created_by` has no enum and no validation; four writers disagree | BR-VR15 | 🟡 |
| Auditability | A snapshot's true author is not recorded — every snapshot says `"human"` | `:172` | 🟡 |

## Acceptance Criteria

```gherkin
Feature: Provenance recording

  Scenario: A new aeroplane's main branch is human
    When I create an aeroplane
    Then its main branch has created_by "human"
    And is_main is true

  Scenario: A REST branch defaults to human
    When I POST /aeroplanes/{id}/branch without created_by
    Then the branch has created_by "human"

  Scenario: A copilot branch records copilot
    When the copilot opens a proposal
    Then the branch has created_by "copilot"
    And its name starts with "copilot-proposal"

  Scenario: A snapshot always records human
    Given the copilot triggers a snapshot
    When the snapshot is created
    Then created_by is "human"

  Scenario: The provenance cursor round-trips
    When I snapshot with provenance_message_id 42
    Then the returned VersionNode has provenance_message_id 42
    And the stored column is 42

Feature: The proposal lifecycle

  Scenario: The first AI edit opens a proposal
    Given an aeroplane with no open proposal
    When apply_design_edits runs
    Then a branch named "copilot-proposal…" exists with created_by "copilot"
    And its head is a clone of the live head
    And the live head is unchanged

  Scenario: A second AI edit reuses the same proposal
    Given an open copilot proposal
    When apply_design_edits runs again
    Then no second proposal branch is created
    And the edit lands on the existing proposal head

  Scenario: The name suffix does not break reuse
    Given an open branch named "copilot-proposal-17"
    When apply_design_edits runs with a different message id
    Then that branch is reused

  Scenario: Read tools see the pending edits
    Given an open proposal whose head has an extra wing cross-section
    When the copilot reads the design
    Then the extra cross-section is visible

  Scenario: Discarding after a wing edit does not raise
    Given a proposal whose head had a wing replaced via put_wing_as_wingconfig
    When discard_proposal runs
    Then the branch and its nodes are deleted
    And no InvalidRequestError is raised

  Scenario: Discarding leaves the live design untouched
    Given an open proposal with several edits
    When it is discarded
    Then the live aeroplane is identical to its pre-proposal state

  Scenario: Only a human adopts
    Given an open proposal
    Then no copilot code path calls adopt_branch
    And promoting it requires POST /branches/{id}/adopt

Feature: The metrics contract

  Scenario: Wing names and cross-section counts are surfaced
    Given an aircraft with wings "main_wing" (6 xsecs) and "h_tail" (2 xsecs)
    When I read the metrics payload
    Then wing_names is ["main_wing", "h_tail"]
    And wings contains {name: "main_wing", n_xsecs: 6}

  Scenario: An empty computation context is omitted
    Given an aircraft whose assumption_computation_context is empty
    When I read the metrics payload
    Then the key is absent from the payload
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|-------------|--------|-----------|
| Proposal isolation from the live head (RF-08/RF-11/RF-15) | Must | ADR 0007 — the safety property the whole AI feature rests on |
| One open proposal per lineage (RF-06/RF-07) | Must | Without it, each AI turn forks a new branch and the user drowns in proposals |
| The `expunge_all` discard sequence (RF-10) | Must | Without it the discard raises and the proposal cannot be cleaned up |
| Read-tool retargeting (RF-09) | Must | Otherwise the model reasons about a design it has already changed |
| `created_by` recording (RF-01…RF-04) | Should | Informational today — no behaviour keys off it |
| `_metrics_payload` wing names and counts (RF-12) | Must | gh-938 — without them the model edits the wrong wing or an invalid index |
| Provenance cursor storage (RF-05) | Should | The intended substitute for cloning the conversation |
| Context omission + stability summary (RF-13/RF-14) | Should | Payload hygiene |
| A `created_by` enum | Won't | 🟡 not implemented; four writers, three values |
| Reading the provenance cursor back | Won't | 🟡 nothing resolves it |
| Recording a snapshot's true author | Won't | 🟡 hard-coded `"human"` |

## Code Traceability

| File | Class / Function | Coverage |
|------|------------------|----------|
| `app/models/aeroplanemodel.py:602-716` | `branches.created_by`, `aeroplanes.created_by`, `provenance_message_id` | 🟢 |
| `app/services/aeroplane_service.py:75-100` | the `main` branch's `created_by="human"` | 🟢 owned by `aeroplane-core` |
| `app/services/aeroplane_version_service.py:172` | the hard-coded `"human"` on snapshots | 🟢 |
| `app/services/aeroplane_version_service.py:74-117` | `_metrics_payload` (gh-938) | 🟢 |
| `app/services/aeroplane_version_service.py:186-241, 324-393` | `create_branch` / `discard_branch` — the primitives the copilot calls | 🟢 |
| `app/services/copilot_apply_service.py:107-241` | `get_or_open_proposal`, `discard_open_proposal` | 🟢 owned by `ai-copilot` |
| `app/services/aeroplane_clone_service.py:105` | `EXCLUDED_TABLES["copilot_messages"]` and its reason | 🟢 |
| `app/schemas/versioning.py` | `SnapshotRequest.provenance_message_id`, `BranchRequest.created_by`, `VersionNode` | 🟢 |
| `_reversa_sdd/state-machines.md` §7 | the proposal state machine | 🟢 |
</content>
