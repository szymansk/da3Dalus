# ADR 0007 — The AI copilot proposes on a branch; only a human adopts

- **Status:** Accepted — in force
- **Decided:** 2026-06-10 (gh-902 Slice 2, commit `85ea5ce6`; Slice 1 advisory-only, `28f2dc4e`)
- **Deciders:** Marc Szymanski (maintainer)
- **Confidence:** 🟢 CONFIRMED (design spec, commit body, code)

## Context

The copilot shipped in two slices: advisory-only, then the ability to change the
design. The question Slice 2 had to answer was not "can an LLM edit geometry" but
"what happens when it edits it wrongly". A wing edit here is not local:
`put_wing_as_wingconfig` deletes and reinserts rows, invalidates tessellations,
marks every operating point `DIRTY` and triggers a full assumption recompute, and
there is no undo. The enabling precondition had shipped three days earlier —
row-copy versioning ([ADR 0006](0006-versioning-by-row-copy-not-json-snapshots.md)).
The commit states the result: *"the copilot can now change the design — but only on
a #901 version branch (the branch = undo). It proposes; the human adopts."*

## Decision

**The copilot's entire write surface is one disposable branch, and adoption is
structurally reserved for the human.**

1. **Write tools operate only on a `copilot-proposal` branch.**
   `get_or_open_proposal` reuses the newest branch matching `root_id = ? AND
   is_main = false AND created_by = 'copilot' AND name LIKE 'copilot-proposal%'`,
   otherwise clones the live head. At most one open proposal per aeroplane.
2. **There is deliberately no adopt tool.** Promotion to `main` happens only in the
   Versions panel, by a person — structural, not prompt-based, enforcement.
3. **Two write tools total:** `apply_design_edits(ops)` and `discard_proposal()`.
   The whole registry is **6 tools**, not the 76-tool MCP surface: *"only the tools
   that are safe, fast, and meaningful for an advisory interaction"*.
4. **Edits go through the same validated services the UI uses** — never raw SQL or
   a bypass path. The copilot cannot construct a state a human could not.
5. **Invalid ops are rejected-with-reason, not raised.** `apply_edits` returns
   `applied` and `rejected: [{op, error}]` so the model self-corrects in-turn.
6. **Read-retargeting (gh-938):** while a proposal is open, `get_design_snapshot` /
   `get_wing_geometry` / `run_analysis` resolve to `branch.head_id`;
   `get_version_tree` and both write tools always use the live id.
7. **The diff is computed from the proposal's own before/after**, captured right
   after `get_or_open_proposal`, so recompute drift cannot pollute it.
8. **Numbers are computed server-side.** `_drag_breakdown` does the
   induced/parasite split in Python because *"the LLM is unreliable at this
   arithmetic (it has produced both physically-impossible splits and 10× errors)"*.

## Consequences

- **The branch is the undo.** A bad proposal costs a `discard_proposal` call, and
  every validator, unit conversion and invalidation hook applies automatically
  because the copilot writes through the UI's services. Verified E2E against a real
  database with a real recompute, which found four bugs the mocked tests missed.
- 🔴 **The accountability trail is designed but not wired**: `message_id` has no
  caller and `provenance_message_id` is written by `snapshot()` and read by nothing.
  `created_by = "copilot"` while the column comment documents `'human' | 'ai'` — this
  ADR is the origin of that divergence, resolved in
  [ADR 0022](0022-one-authority-per-user-facing-quantity.md) / `Q-CC-9`.
- 🔴 Four failure-mode defects: `_effective_target_id` swallows every exception and
  falls back to the live id; nothing prevents duplicate proposal branches; a
  JSON-decode failure on tool arguments becomes `{}` and the tool is **still
  invoked**; and a mid-stream SSE disconnect leaves the assistant message
  unpersisted.
- 🔴 **No rate limiting, quota or cost accounting** beyond `MAX_LOOP_ITERATIONS = 6`,
  and much of the answer-quality policy is prompt-only (~270 lines, no enforcement).

**Rejected:** an adopt tool with a confirmation prompt — a prompt-mediated
confirmation is not an enforcement boundary; the absence of the tool is.

## Related

[ADR 0006](0006-versioning-by-row-copy-not-json-snapshots.md) ·
[ADR 0004](0004-one-aero-truth-per-aircraft.md) ·
[`../permissions.md`](../permissions.md) §2 (actor A2) · domain rules BR-43 … BR-49.
Evidence: commits `85ea5ce6`, `28f2dc4e`;
`docs/superpowers/specs/2026-06-09-copilot-agentic-apply-design.md`;
`scripts/uat_copilot_driver.py` (UAT against the **real** hub).

---

## Amendment — 2026-08-15 — agent write semantics for MCP

**Source:** [`../questions.md`](../questions.md) §Q-MC-1. **Confidence:** 🟢
CONFIRMED (transaction boundary verified in code).

The decision above governs the copilot's 6-tool surface. The other agent surface —
the 76-tool **MCP server** — had no equivalent policy, and the reason it never
needed one was a bug: `_call_endpoint` (`app/mcp_server.py:96-107`) never commits,
so roughly **40 of the 76 tools are mutations that return a convincing payload while
persisting nothing**. Durability is *inconsistent* rather than absent —
self-committing services do persist. ADR 0016 lists this bug as `/mcp`'s "one
accidental mitigation"; it stops being one.

**The transaction boundary is fixed.** `_call_endpoint` adopts a
`get_db()`-equivalent context manager that **commits on success and rolls back on
exception**, i.e. the boundary
[ADR 0009](0009-get-db-owns-the-transaction-boundary.md) already defines for REST.
Two things travel with the fix and neither is optional: the **self-committing
services must be reviewed for nested-commit behaviour**, and the **test arrangement
must be repaired** — no current test can catch this, because the tool tests
monkeypatch `_call_endpoint` and the `_call_endpoint` tests use fake local
functions. Explicitly not a one-line change.

**Agent write semantics, layered:**

1. **A write master-switch — `MCP_ALLOW_WRITES`, defaulting to off.** Write
   capability is granted deliberately per session: the MCP analogue of the copilot's
   "no adopt tool", structural rather than prompt-mediated.
2. **An auto-snapshot before destructive writes**, making agent edits **recoverable
   by construction** rather than merely restricted. It reuses gh-1058's machinery
   and generalises *the branch is the undo* to *the snapshot is the undo*.

**This is only trustworthy because of `Q-VS-1`** — an auto-snapshot is worthless if
snapshots can be edited afterwards, and today nothing stops an ordinary CRUD `PUT`
from mutating a frozen node.

**Deferred:** a curated write surface — restricting the destructive subset requires a
per-tool review of 40 tools, and the auto-snapshot already makes the damage
reversible. **Security precondition, already satisfied:** `Q-CC-1`'s
loopback-by-default exposure guard
([ADR 0024](0024-single-user-desktop-operating-model.md)) is what makes the fix an
ordinary bug fix rather than a security decision.

**Related:** [ADR 0009](0009-get-db-owns-the-transaction-boundary.md) ·
[ADR 0006](0006-versioning-by-row-copy-not-json-snapshots.md) ·
[ADR 0024](0024-single-user-desktop-operating-model.md) ·
[ADR 0020](0020-one-designwarning-channel-no-undeclared-fallbacks.md) ·
[`../questions.md`](../questions.md) §Q-MC-1, §Q-VS-1, §Q-CC-1.
