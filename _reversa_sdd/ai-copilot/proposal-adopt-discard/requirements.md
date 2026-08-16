# ai-copilot / proposal-adopt-discard

> Use-case specification. Parent module: [`../requirements.md`](../requirements.md).
> Cross-module: this use case **calls** `versioning`'s branch primitives; the
> branch mechanics themselves are specified in
> [`../../versioning/branch-model/requirements.md`](../../versioning/branch-model/requirements.md).
> Confidence: 🟢 CONFIRMED · 🟡 INFERRED · 🔴 GAP.

## Overview

The copilot's **only** write surface is a single disposable branch named
`copilot-proposal`, opened on demand, reused across turns, and removed either by
the model's `discard_proposal` tool or by the human in the Versions panel. 🟢

Adoption — promoting the proposal to `main` — is **not part of this use case and
has no tool**. That is the structural enforcement of ADR 0007: the copilot
proposes, only a human adopts. 🟢

## Responsibilities

- Open or reuse the proposal branch for an aeroplane's lineage. 🟢
- Apply validated edit ops to the **proposal head**, never to the live node. 🟢
- Collect per-op `applied` / `rejected` results. 🟢
- Compute the proposal's own pre-edit vs post-edit metrics diff. 🟢
- Discard the proposal safely (the `expunge_all` dance). 🟢
- Surface the proposal to the UI **without a dedicated endpoint** — the frontend
  detects it from the lineage tree. 🟢

**NOT this use case:** cloning, snapshotting, branch renaming and adoption
(→ `versioning`); wing-config validation and persistence (→ `wing-design`).

## Business Rules

- **BR-43 / ADR 0007 — Propose, never mutate; there is no adopt tool.** 🟢
- **BR-44 — At most one open proposal per aeroplane.** 🟢 Reuse query:
  `root_id = ? AND is_main = False AND created_by = 'copilot' AND name LIKE
  'copilot-proposal%'`, ordered by `BranchModel.id DESC`, first match wins.
- **BR-CO34 — The branch name prefix is `copilot-proposal`.** 🟢
  `_COPILOT_BRANCH_PREFIX = "copilot-proposal"`; the optional `-<message_id>`
  suffix exists in code and is **never** supplied, so the name is always the
  bare prefix. 🟢 Replaced by the typed `branch_kind` column (`Q-CO-12`).
- **BR-CO22 — `created_by = "copilot"`.** 🟢 A third vocabulary value alongside
  the documented `'human' | 'ai'`; the reuse query depends on it, so a branch
  created with `'ai'` would **not** be found.
- **BR-CO16 — A bad op is rejected, the batch is not.** 🟢
  `applied: list[str]`, `rejected: list[{op, error}]`; `apply_edits` never
  raises for a single op.
- **BR-CO17 — Per-wing composition.** 🟢 Geometry ops mutate
  `wing_config_cache[wing]` (mm) and each touched wing is written **once** via
  `put_wing_as_wingconfig(scale=0.001)`. `ReplaceWingConfig` deliberately breaks
  the pattern: validate, write immediately, evict the cache entry,
  `db.expire_all()`.
- **BR-CO18a — `db.expire_all()` after the wing writes** — because
  `put_wing_as_wingconfig` deletes-then-reinserts, and stale `WingModel`
  identities would make the metrics payload (and a same-turn
  `get_wing_geometry`) read **pre-edit** geometry. 🟢
- **BR-CO18b — `db.expunge_all()` before discarding** — the docstring names the
  exact failure it prevents: `InvalidRequestError: Can't attach instance
  <WingXSecSpareModel …>; another instance with key (…) is already present in
  this session`. 🟢
- **BR-CO19 — A tip append strips `tip_type` from every trailing segment.** 🟢
  Otherwise `create_wing_configuration()`'s tip pass processes the new winglet
  first and physically reorders the cross-sections.
- **BR-CO21 — The diff is the proposal's own before/after over 13 keys.** 🟢
  Baseline captured immediately after `get_or_open_proposal`, so recompute drift
  on the live node cannot pollute it. Returned twice —
  `diff_proposal_branch` and `diff_vs_live`, which becomes a real live-vs-proposal diff (`Q-CO-6`). 🟢
- **BR-CO20 — Post-apply recompute is non-fatal.** 🟢
- **BR-78 / ADR 0009 — Nothing here commits.** 🟢
- **BR-CO35 — The UI discovers the proposal from the lineage tree.** 🟢
  `useCopilotProposal` (gh-939) filters `GET /lineages/{root}/tree` for a branch
  with `created_by === "copilot"` and `is_main === false`, and drives adopt /
  discard through the existing `versioning` routes — *"no new API endpoints"*.

## Functional Requirements

| ID | Requirement | Priority | Acceptance criterion |
|----|-------------|----------|----------------------|
| RF-01 | Open a proposal branch on the first write op | Must | A branch named `copilot-proposal`, `created_by='copilot'`, `is_main=false` exists |
| RF-02 | Reuse the existing proposal on later ops | Must | The same `branch_id` is returned |
| RF-03 | Clone from the **live** head, not from the proposal | Must | `predecessor_id` is the live node's id |
| RF-04 | Never mutate the live head | Must | Live geometry is byte-identical after an apply |
| RF-05 | Validate ops through the discriminated union before touching anything | Must | An unknown `type` ⇒ `{"error": "Invalid ops payload: …"}` and **no** branch is opened |
| RF-06 | Collect `applied` and `rejected` per op | Must | Both lists present in the result |
| RF-07 | Write each touched wing exactly once | Must | One `put_wing_as_wingconfig` call per wing per batch |
| RF-08 | Expire the session after the wing writes | Must | A same-turn read returns post-edit geometry |
| RF-09 | Handle `ReplaceWingConfig` immediately and evict the cache | Must | A later op on that wing reads the replaced config |
| RF-10 | Strip `tip_type` on a tip append | Must | The appended station is last |
| RF-11 | Reject interior `AddXsec` with a steering message | Must | The message points at a tip-append |
| RF-12 | Reject non-interior `RemoveXsec` | Must | Index 0 and index `n−1` are rejected |
| RF-13 | Capture the pre-edit baseline from the proposal | Must | Not from the live node |
| RF-14 | Compute the 13-key diff, omitting unchanged keys | Must | Rounded to 6 decimals |
| RF-15 | Return the diff twice (`diff_proposal_branch`, `diff_vs_live`) | Must | Identical values |
| RF-16 | Discard the proposal and report whether one existed | Must | `{"discarded": true}` then `{"discarded": false}` |
| RF-17 | Expunge before discarding | Must | No `InvalidRequestError` with spares present |
| RF-18 | Recompute assumptions after an apply, non-fatally | Should | A failure logs a warning; `applied` is still returned |
| RF-19 | Never commit | Must | A rollback leaves no branch and no edits |
| RF-20 | Expose no adopt capability | Must | No tool, no service function in this module promotes a branch |

## Non-functional Requirements

| Type | Inferred requirement | Evidence | Confidence |
|------|----------------------|----------|-----------|
| Safety | The live design is unreachable from any AI write path | ADR 0007; `apply_edits(proposal_uuid, …)` | 🟢 |
| Safety | Adoption requires a human action in a different surface | absence of an adopt tool; `useCopilotProposal` | 🟢 |
| Correctness | Post-write reads must not see pre-write geometry | `db.expire_all()` + its comment | 🟢 |
| Correctness | The diff cannot be polluted by live-node recompute drift | baseline captured from the clone | 🟢 |
| Reliability | A malformed op batch cannot leave a half-applied wing | the per-wing cache is written only after the loop | 🟡 |
| Reliability | Discarding a proposal with spares must not raise | `db.expunge_all()` + its docstring | 🟢 |
| Integrity | Nothing commits; the request boundary owns the transaction | ADR 0009 | 🟢 |
| Scalability | Every proposal is a **full subgraph clone** — retention owned by `Q-VS-2` 🟡 | `versioning` G-9 | 🔴 |
| Traceability | 🟢 The message id is supplied and the version graph resolves back to the turn (`Q-CO-1`) | previously `message_id` never supplied; `provenance_message_id` never read | 🔴 |

## Acceptance Criteria

```gherkin
Feature: Opening and reusing a proposal

  Scenario: The first edit opens a branch
    Given an aeroplane with no copilot proposal
    When apply_design_edits runs with a valid SetSegment op
    Then a branch named "copilot-proposal" exists
    And its created_by is "copilot" and is_main is false
    And its head is a clone whose predecessor is the live node
    And the live node's geometry is unchanged

  Scenario: The second edit reuses it
    Given an open proposal
    When apply_design_edits runs again
    Then the returned branch_id is unchanged
    And no second branch exists

  Scenario: Invalid ops never open a branch
    Given an aeroplane with no proposal
    When apply_design_edits runs with an op of unknown type
    Then the result is an error mentioning "Invalid ops payload"
    And no branch was created

Feature: Applying edits

  Scenario: Partial success
    Given two ops, one naming a wing that does not exist
    When apply_design_edits runs
    Then applied contains the good op
    And rejected contains {op, error} for the bad one

  Scenario: Composition
    Given two SetSegment ops on the same wing
    When apply_design_edits runs
    Then put_wing_as_wingconfig is called exactly once for that wing

  Scenario: Replace evicts the cache
    Given a SetSegment op followed by a ReplaceWingConfig on the same wing
    When apply_design_edits runs
    Then the persisted config is the replacement
    And the session was expired

  Scenario: A tip append lands at the tip
    Given a three-segment wing whose last segment has tip_type "flat"
    When AddXsec is applied with at_index equal to n_xsecs
    Then the new cross-section is the last one
    And no cross-section was reordered

  Scenario: Interior insertion is refused with guidance
    When AddXsec is applied with an interior at_index
    Then it is rejected with a message steering to a tip-append

  Scenario: Post-write reads are fresh
    Given an apply that changed the root chord
    When get_wing_geometry runs in the same turn
    Then it returns the new chord

Feature: The diff

  Scenario: Only changed keys appear
    Given an apply that changes mass only
    When the diff is computed
    Then it contains mass_kg with before, after and delta
    And it does not contain span_m

  Scenario: The baseline is the proposal, not the live node
    Given a live node whose stored context is stale
    When apply_design_edits runs
    Then the diff's "before" values come from the freshly cloned proposal

Feature: Discarding

  Scenario: Discard removes the branch
    Given an open proposal
    When discard_proposal runs
    Then the result is {"discarded": true}
    And the branch and its nodes are gone

  Scenario: Discarding twice is not an error
    When discard_proposal runs again
    Then the result is {"discarded": false}

  Scenario: Discarding a proposal with spares does not raise
    Given a proposal whose wings carry spares
    When discard_proposal runs
    Then no InvalidRequestError is raised

Feature: Adoption is human-only

  Scenario: There is no adopt tool
    When I enumerate the copilot tool registry
    Then nothing promotes, adopts or merges a branch

  Scenario: The UI adopts through the versioning API
    Given an open proposal visible in the lineage tree
    When the human adopts it in the Versions panel
    Then POST /branches/{id}/adopt is called
    And exactly one branch of the lineage has is_main true
```

## Priority (MoSCoW)

| Requirement | MoSCoW | Rationale |
|---|---|---|
| Proposal confinement (RF-01…RF-04) | Must | ADR 0007 — the system's central AI-safety property |
| Validation before side effects (RF-05) | Must | Otherwise a typo leaves an empty branch behind |
| Per-op rejection (RF-06) | Must | The model's self-correction loop depends on it |
| Single write per wing + expire (RF-07/RF-08) | Must | Composability and post-write correctness |
| `tip_type` strip (RF-10) | Must | Otherwise geometry silently reorders |
| Expunge before discard (RF-17) | Must | Otherwise the discard raises on any aircraft with spares |
| No adopt capability (RF-20) | Must | The structural guarantee |
| No commit (RF-19) | Must | ADR 0009 |
| The diff (RF-13…RF-15) | Should | Informational; the prompt forbids using it for performance |
| Non-fatal recompute (RF-18) | Should | The next read recomputes anyway |
| `ReplaceWingConfig` immediacy (RF-09) | Should | A deliberate exception to the cache pattern |
| Naming a proposal after its message (`-<message_id>`) | **Must** | 🟢 decided (`Q-CO-1`): the copilot supplies the message id and the version graph resolves back to the turn |
| Multiple concurrent proposals | **Won't** | 🟢 decided (`Q-CO-12`): a partial unique index enforces at most one open proposal per `root_id` |
| Server-side adopt from the copilot | Won't | ADR 0007 |
| Proposal retention / size accounting | Won't (owned by `versioning`) | 🟡 `Q-VS-2` decides the snapshot growth policy; the copilot compounds it per proposal |

## Code Traceability

| File | Symbol | Coverage |
|---|---|---|
| `app/services/copilot_apply_service.py:44` | `_DIFF_KEYS` (13 dot-paths) | 🟢 |
| `…:107-241` | `get_or_open_proposal`, `_find_open_proposal`, `discard_open_proposal` | 🟢 |
| `…:248` | `apply_edits` | 🟢 |
| `…:517-520` | the `tip_type` strip | 🟢 |
| `…` | `compute_metrics_diff` | 🟢 |
| `app/services/copilot_tools.py:700-770` | `_apply_design_edits`, `_discard_proposal` | 🟢 |
| `app/schemas/copilot_edits.py` | the 7-op union | 🟢 |
| `app/services/aeroplane_version_service.py:186-241` | `create_branch` | 🟢 owned by `versioning` |
| `…:324-393` | `discard_branch` | 🟢 owned by `versioning` |
| `frontend/hooks/useCopilotProposal.ts` (gh-939) | proposal detection + adopt/discard | 🟢 owned by `frontend-workbench` |
| `app/tests/test_copilot_apply_integration.py` (2 679 l.) | the behaviour above | 🟢 |
