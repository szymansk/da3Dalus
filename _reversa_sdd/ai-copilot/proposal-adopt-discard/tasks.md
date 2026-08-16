# ai-copilot / proposal-adopt-discard — Implementation Tasks

> Parent module task list: [`../tasks.md`](../tasks.md).

## Prerequisites

- [ ] `versioning`: `create_branch`, `discard_branch`, `BranchModel` with
      `root_id` / `head_id` / `is_main` / `created_by`, and `_metrics_payload`.
- [ ] `wing-design`: `put_wing_as_wingconfig(db, uuid, wing, cfg, scale=0.001)`
      and `create_wing_configuration()`'s two-pass (middle / tip) segment
      handling.
- [ ] `mission-and-sizing`: `design_assumptions_service` +
      `recompute_assumptions`.
- [ ] `app/schemas/copilot_edits.py` — the 7-member discriminated union.
- [ ] `get_db()` owning the transaction (ADR 0009).

## Tasks

- [ ] **T-01 — `_COPILOT_BRANCH_PREFIX` and `_find_open_proposal`.**
  `SELECT … WHERE root_id = ? AND is_main = FALSE AND created_by = 'copilot'
  AND name LIKE 'copilot-proposal%' ORDER BY id DESC LIMIT 1`.
  - Legacy origin: `app/services/copilot_apply_service.py:107-241`
  - Definition of done: the query is reproduced exactly. Record all three
    fragilities as gaps: duplicates are tolerated (newest wins), a `'ai'`
    `created_by` would not match, and a human rename detaches the branch.
  - Confidence: 🟢

- [ ] **T-02 — `get_or_open_proposal`.**
  `root_id = node.root_id or node.id`; reuse or
  `create_branch(from_node_id=live_id, name=prefix[+"-"+message_id],
  created_by="copilot")`.
  - Legacy origin: `app/services/copilot_apply_service.py:107`
  - Definition of done: two calls return the same branch; the clone's
    `predecessor_id` is the **live** node. Reproduce that `message_id` is
    accepted and never supplied by any caller, and record it.
  - Confidence: 🟢

- [ ] **T-03 — `apply_edits` skeleton.**
  Resolve the proposal node by UUID; iterate ops inside a `try/except` that
  appends to `rejected: [{op, error}]`; collect `applied: [str]`; never raise
  for a single op.
  - Legacy origin: `app/services/copilot_apply_service.py:248`
  - Definition of done: a batch of two ops where one fails returns both lists
    populated and applies the good one.
  - Confidence: 🟢

- [ ] **T-04 — The per-wing config cache.**
  Geometry ops mutate `wing_config_cache[wing]` (mm); after the loop, write each
  touched wing **once** via `put_wing_as_wingconfig(scale=0.001)`.
  - Legacy origin: `app/services/copilot_apply_service.py:248`
  - Definition of done: two ops on one wing produce exactly one write; two ops
    on two wings produce two writes.
  - Confidence: 🟢

- [ ] **T-05 — The station/segment ops.**
  `SetXsec` (station: interior writes **both** neighbours; 0 writes the first
  root; `n` writes the last tip); `SetSegment` (segment: its own fields + tip
  airfoil); `SetWingParam` (applies `sweep_mm` / `dihedral` to **every**
  segment).
  - Legacy origin: `app/services/copilot_apply_service.py`,
    `app/schemas/copilot_edits.py`
  - Definition of done: an interior `SetXsec` changes two segments — this is the
    index contract most rejections come from, so it needs its own test.
  - Confidence: 🟢

- [ ] **T-06 — `AddXsec` (tip append only) + the `tip_type` strip.**
  Reject any `at_index != n_xsecs` with a message steering to a tip-append;
  before appending, `pop("tip_type")` from **every** trailing segment.
  - Legacy origin: `app/services/copilot_apply_service.py:517-520`
  - Definition of done: appending to a 3-segment wing whose last segment carries
    `tip_type="flat"` puts the new station **last**. Without the strip,
    `create_wing_configuration()` runs its tip pass on the old segment and
    reorders the cross-sections — carry the comment. Record the unimplemented
    mid-wing insertion as a gap.
  - Confidence: 🟢

- [ ] **T-07 — `RemoveXsec`.**
  Accept `1 … n_xsecs − 2` only; merge `seg[i-1]` and `seg[i]` by adding lengths
  **and adding sweeps**.
  - Legacy origin: `app/services/copilot_apply_service.py`
  - Definition of done: index 0 and index `n−1` are rejected. Reproduce the
    sweep **sum** and record the divergence from the "weighted avg" comment as a
    gap — do not silently "fix" it, it changes geometry.
  - Confidence: 🟢

- [ ] **T-08 — `ReplaceWingConfig`.**
  Validate `WingConfigurationSchema`; write immediately; evict the cache entry;
  `db.expire_all()`.
  - Legacy origin: `app/services/copilot_apply_service.py`
  - Definition of done: a `SetSegment` followed by a `ReplaceWingConfig` on the
    same wing persists the replacement, not the cached edit.
  - Confidence: 🟢

- [ ] **T-09 — `SetAssumption`.**
  Delegate to `design_assumptions_service` with the op's `param` /`value` in
  **SI or degrees** (unlike the geometry ops, which are mm).
  - Legacy origin: `app/services/copilot_apply_service.py`
  - Definition of done: an unknown `param` is rejected into `rejected[]`, not
    raised. The unit difference between this op and the geometry ops is
    documented in the tool description.
  - Confidence: 🟢

- [ ] **T-10 — `db.expire_all()` after the batch.**
  - Legacy origin: `app/services/copilot_apply_service.py` (commented call)
  - Definition of done: `_metrics_payload` and a same-turn `get_wing_geometry`
    both return **post-edit** geometry. Carry the comment explaining the
    delete-then-reinsert identity problem.
  - Confidence: 🟢

- [ ] **T-11 — Non-fatal recompute.**
  `recompute_assumptions(db, proposal_uuid)` in a `try/except` that
  `logger.warning`s.
  - Legacy origin: `app/services/copilot_apply_service.py`
  - Definition of done: with recompute patched to raise, `applied` is still
    returned and the branch still exists.
  - Confidence: 🟢

- [ ] **T-12 — `discard_open_proposal`.**
  `_find_open_proposal` → `None ⇒ False`; else `db.flush()` →
  `db.expunge_all()` → **re-resolve** → `discard_branch` → `True`.
  - Legacy origin: `app/services/copilot_apply_service.py`
  - Definition of done: discarding a proposal whose wings carry spares does not
    raise `InvalidRequestError: Can't attach instance <WingXSecSpareModel …>`.
    The re-resolve after the expunge is mandatory — the earlier object is
    detached.
  - Confidence: 🟢

- [ ] **T-13 — `compute_metrics_diff` + `_DIFF_KEYS`.**
  13 `(label, dot-path)` pairs; omit unchanged and both-missing; round to 6
  decimals; `{label: {before, after, delta}}`.
  - Legacy origin: `app/services/copilot_apply_service.py:44`
  - Definition of done: a mass-only change produces exactly one key; a key
    missing on both sides is absent, not `null`.
  - Confidence: 🟢

- [ ] **T-14 — `_apply_design_edits` orchestration.**
  Validate → resolve live node → open/reuse branch → capture the **pre-edit**
  baseline from the proposal → apply → diff → return with both diff fields.
  - Legacy origin: `app/services/copilot_tools.py:700-750`
  - Definition of done: an invalid ops payload returns an error and **no branch
    is created** (assert the branch count). The baseline must come from the
    clone, not the live node — a test with a deliberately stale live context
    proves it.
  - Confidence: 🟢

- [ ] **T-15 — `_discard_proposal` wrapper.**
  `{"discarded": bool}`; on exception `logger.exception` + `{"error": str(exc)}`.
  - Legacy origin: `app/services/copilot_tools.py:757-770`
  - Definition of done: a second call returns `{"discarded": false}` rather than
    an error.
  - Confidence: 🟢

- [ ] **T-16 — Confirm the absence of an adopt path.**
  No tool, no service function and no endpoint in this module may promote a
  branch.
  - Legacy origin: ADR 0007; `TOOL_REGISTRY`
  - Definition of done: a test enumerates the registry and asserts no name
    matches `adopt|promote|merge|publish`. This test is the executable form of
    the ADR — keep it.
  - Confidence: 🟢

## Test Tasks

- [ ] **TT-01 — Open:** first op creates `copilot-proposal`,
      `created_by='copilot'`, `is_main=false`, predecessor = live node.
- [ ] **TT-02 — Reuse:** second op returns the same `branch_id`; only one branch
      exists.
- [ ] **TT-03 — Live untouched:** the live head's wing config is byte-identical
      after an apply.
- [ ] **TT-04 — Validation gate:** an unknown op type ⇒ error and **zero**
      branches created.
- [ ] **TT-05 — Partial success:** `applied` + `rejected` both populated.
- [ ] **TT-06 — Single write per wing:** one `put_wing_as_wingconfig` per wing.
- [ ] **TT-07 — Interior `SetXsec`:** both neighbouring segments change.
- [ ] **TT-08 — Tip append:** the new station is last; no reordering.
- [ ] **TT-09 — Interior `AddXsec`:** rejected with the steering message.
- [ ] **TT-10 — `RemoveXsec` bounds:** 0 and `n−1` rejected; interior merges
      lengths and sweeps (characterisation of the sweep sum).
- [ ] **TT-11 — `ReplaceWingConfig`:** replacement wins over a cached edit.
- [ ] **TT-12 — Expire:** a same-turn read sees post-edit geometry.
- [ ] **TT-13 — Recompute failure:** non-fatal.
- [ ] **TT-14 — Discard:** `true` then `false`; spares present and no
      `InvalidRequestError`.
- [ ] **TT-15 — Diff:** only changed keys; 6-decimal rounding; both diff fields
      identical.
- [ ] **TT-16 — Baseline provenance:** with a stale live context, the diff's
      `before` still matches the clone.
- [ ] **TT-17 — No adopt:** the registry contains no promote/adopt/merge tool.
- [ ] **TT-18 — No commit:** a rollback after an apply leaves no branch and no
      edits.

## Suggested Order

1. **T-01 → T-02** the branch lookup and open, because every other task needs a
   proposal to write to.
2. **T-03 → T-04** the apply skeleton and the cache — the composition rule
   shapes every op implementation.
3. **T-05 → T-09** the seven ops. `SetXsec` (T-05) first: its station↔segment
   contract is the one most rejections come from and it defines the cache
   layout. `AddXsec` (T-06) needs its own test *before* implementation — the
   `tip_type` strip is invisible in the happy path and only shows up as
   reordered geometry.
4. **T-10 → T-11** session hygiene and recompute, after the writes exist.
5. **T-12** discard — it needs a populated proposal (with spares) to be a
   meaningful test.
6. **T-13 → T-14** the diff and the orchestration, which need both apply and
   `_metrics_payload`.
7. **T-15 → T-16** the wrappers and the structural no-adopt test.

## Pending Gaps (🔴)

- **Should duplicate proposal branches be prevented** with a uniqueness rule, or
  should the reuse query take the oldest instead of the newest?
- **What should happen when a human renames the proposal branch?** Today the
  `LIKE 'copilot-proposal%'` query silently stops matching and a second proposal
  is opened.
- **Should `created_by` become an enum** so `'ai'` and `'copilot'` cannot
  diverge? A branch created with the documented `'ai'` would break reuse.
- **Should `message_id` be supplied** so a proposal names its originating turn
  and `provenance_message_id` becomes readable?
- **Should `diff_vs_live` be removed or made truthful?**
- **Should mid-wing `AddXsec` be implemented**, or should the tool description
  state the restriction so the model never attempts it?
- **Is `RemoveXsec`'s sweep sum intended?** The comment says "weighted avg".
- **Should a fully-rejected batch discard the branch it just opened**, so the UI
  does not show an empty proposal?
- **What happens if the human adopts mid-turn?** A subsequent tool call opens a
  second proposal from the adopted design; nothing tests this.
- **Is there a retention policy for proposals?** Every one is a full subgraph
  clone and nothing prunes them.
- **Should proposal activity be measured** — opened / reused / discarded /
  adopted — to judge whether the copilot helps?
