# AI Copilot — Slice 2: Agentic Apply — Design Spec

**Epic:** #902 (AI Copilot) · **Slice:** 2 · **Date:** 2026-06-09 · **Status:** design approved
**Depends on:** #901 (Versioning — shipped) + Copilot Slice 1 (advisory — shipped)

## 1. Goal & scope

Slice 1 made the copilot **advise**. Slice 2 makes it **act**: it can change the
aircraft design — but only on a **#901 version branch** (the branch *is* the
undo). The copilot proposes, **the human disposes** (adopt/discard via the
shipped versioning UI). It never touches the live head.

**Settled decisions (this brainstorming):**
1. **Edit scope:** design **assumptions** (mass, cd0_override, cl_max,
   target_static_margin, …) **+ full wing geometry** via WingConfig/XSec
   (chord, twist, airfoil, dihedral, add/remove x-sec — incl. **winglets** as a
   dihedral-knee x-sec). "Build a winglet" = WingConfig/XSec edit, **never** a
   new `cad_designer` Creator.
2. **Edit expression: hybrid** — structured **edit-ops** (a small validated
   delta DSL) for the common cases, **plus a full-WingConfig-replace** escape
   hatch for exotic geometry. Both write through the **same validated services**
   the UI uses (`wing_service`, `design_assumptions_service`), so the copilot
   cannot produce invalid geometry — the Pydantic schemas + services reject it.
3. **Agentic depth: iterate on the branch.** The copilot opens one working
   branch, applies edits → recomputes → reads metrics → refines → … (bounded by
   a max-iteration guard) and presents the **final diff**. "Get SM to 12 %" → it
   tweaks and checks itself.
4. **Architecture (Approach ①):** one **open `copilot-proposal` branch** per
   aeroplane; while it is open, the read tools (`get_design_snapshot`,
   `run_analysis`) **auto-target the branch** so the copilot sees its own edits
   like a human in the branch. Review/adopt/discard reuses the shipped #901
   versioning UI + Metrics-Dashboard compare.
5. **Safety:** writes happen **only on the branch, never the live head**;
   **adopt is human-only** (the copilot has no adopt tool). Branch = undo.

**Out of scope (later slices):** CG/component edits, mission edits, `run_python`
code-exec + goal optimization (Slice 3), `save_tool` library, per-tab agents +
supervisor (Slice 5), the agentic expert panel (#929).

## 2. Existing building blocks (reuse, don't rebuild)

All shipped and **callable in-process, keyed by `aeroplane_uuid`, no global
state** (verified by exploration):
- **Branch ops** (`aeroplane_version_service`): `create_branch(db, from_node_id,
  name, created_by)`, `adopt_branch`, `discard_branch`, `compare(db, a, b)`,
  `list_tree`, `clone_aeroplane_subgraph` (copies the full subgraph incl.
  `assumption_computation_context`).
- **Wing write path** (`wing_service`): `put_wing_as_wingconfig(db,
  aeroplane_uuid, wing_name, WingConfigurationSchema, scale=0.001)` (full
  replace, validated), `put_wing_cross_section(...)`, `on_wing_changed` hook.
- **Assumption write path** (`design_assumptions_service`):
  `update_assumption(db, aeroplane_uuid, param_name, AssumptionWrite)`.
- **Recompute:** `assumption_compute_service.recompute_assumptions(db, uuid)` —
  **synchronous**, safe to call from a worker thread (used in #924 verification).
- **Copilot loop** (`copilot_tools.TOOL_REGISTRY` + `copilot_service.run_turn`):
  tools registered as `ToolEntry{schema, impl}`, executed via
  `asyncio.to_thread(copilot_tools.execute, name, db, aeroplane_id, **args)`;
  the `db` session is **writable** and commits once at turn end (atomicity is
  automatic).

## 3. Design

### 3.1 Edit-ops DSL (new — `app/schemas/copilot_edits.py`)
A small, validated discriminated-union of operations:
- `SetAssumption{param, value}`
- `SetXsec{wing, index, chord?, twist?, airfoil?, dihedral?, ...}` (only the
  provided fields change)
- `AddXsec{wing, at_index, chord, span, twist?, airfoil?, dihedral?}` (winglet =
  a tip x-sec with a dihedral knee)
- `RemoveXsec{wing, index}`
- `SetWingParam{wing, sweep?, dihedral?, ...}`
- `ReplaceWingConfig{wing, wing_config: WingConfigurationSchema}` (the escape
  hatch)
Each op is a Pydantic model; the union is validated before any DB write.

### 3.2 Apply engine (new — `app/services/copilot_apply_service.py`)
`apply_edits(db, proposal_aeroplane_uuid, ops) -> ApplyResult`:
1. For geometry ops: load the wing's current `WingConfiguration`, apply the ops
   in memory to produce a new `WingConfigurationSchema`, write via
   `wing_service.put_wing_as_wingconfig` (so the existing validation + spare
   recompute + tessellation hook run). `ReplaceWingConfig` writes directly.
2. For assumption ops: `design_assumptions_service.update_assumption`.
3. After all ops: `recompute_assumptions(db, uuid)` synchronously.
4. Return `{applied: [...], rejected: [{op, error}], metrics: <new>, ...}`.
   Invalid ops are **rejected with a reason** (not raised) so the copilot can
   self-correct (agentic).

### 3.3 Proposal-branch lifecycle (new — in `copilot_apply_service`)
- `get_or_open_proposal(db, live_aeroplane_id, message_id) -> branch` — if an
  **open** `copilot-proposal` branch exists for this lineage, reuse it; else
  `create_branch(... created_by="copilot", name="copilot-proposal-<msgid>")`.
  "Open" = a copilot branch not yet adopted/discarded. **One open proposal per
  aeroplane** (MVP).
- Adopt/discard: **reuse the shipped #901** `adopt_branch` / `discard_branch`
  (user-driven via the versioning UI). The copilot gets a `discard_proposal`
  tool (to abandon its own dead-end), but **no adopt tool**.

### 3.4 Copilot tools (extend `copilot_tools.py`)
- **`apply_design_edits{ops}`** (write): `get_or_open_proposal` → `apply_edits`
  → return `{branch_id, branch_uuid, applied, rejected, diff_vs_live}` where
  `diff_vs_live` = `compute_metrics_diff(live, proposal)` (new small pure
  helper). This is the agentic primitive — the copilot calls it repeatedly to
  iterate.
- **`discard_proposal{}`** (write): `discard_branch` the open proposal.
- **Read-tool retargeting:** when an open proposal exists for the conversation's
  aeroplane, `get_design_snapshot` / `run_analysis` resolve to the **proposal
  branch head** (so the copilot reads its own edits). Implemented by resolving
  the effective target uuid in `execute()` / the tool impls.

### 3.5 Transport & loop (`copilot_service.run_turn`, `/copilot/stream`)
No structural change — write tools plug into the existing registry/loop. The
existing **max-iteration guard** bounds the agentic refine loop. The final
assistant turn explains the proposal + the diff and tells the user to **review &
adopt/discard** in the History/Variants panel.

### 3.6 System prompt (extend)
Add: the copilot may **propose** design changes via `apply_design_edits` (it
**never** changes the live design — only a branch the user must adopt); express
changes as edit-ops; iterate (apply → run_analysis → refine) until the goal is
met or no longer improves; **always present the before/after metrics diff** and
end by telling the user to adopt or discard in the Versions panel; if ops are
rejected, fix and retry; never claim the design was changed — say "I've prepared
a proposal on a branch."

### 3.7 Frontend (light — reuse #901 UI)
The proposal branch already appears in the shipped `VersionHistoryPanel`. Add a
small **"Copilot proposal pending"** affordance in the `CopilotStrip` (badge +
"Review / Adopt / Discard" that deep-links to the versioning panel +
Metrics-Dashboard compare). No new compare/adopt UI — reuse #907.

## 4. Safety / gating
- Writes target **only** the proposal branch; the live head is never mutated.
- **No adopt tool** — adoption is a deliberate human action via the #901 UI.
- All geometry/assumption writes go through the **validated services** → invalid
  designs are rejected, surfaced to the copilot, not persisted.
- One open proposal per aeroplane; `discard_proposal` cleans up dead-ends.

## 5. Testing
- **Backend unit:** edit-ops validation; apply engine (each op type applied →
  correct WingConfig; invalid op → rejected-with-reason, not raised); winglet =
  add-xsec produces a valid dihedral-knee config; metrics-diff helper.
- **Backend integration (real migrated DB):** `apply_design_edits` creates one
  proposal branch, applies ops to the branch (live head unchanged), recompute
  runs, diff returned; second call reuses the same open branch; `discard_proposal`
  removes it; read-tool retargeting returns branch metrics while a proposal is
  open. Hub **mocked** in CI.
- **3-persona real-hub UAT** (standing requirement for AI features): drive real
  goals through the copilot ("add a winglet to cut induced drag", "get the
  static margin to ~12 %"), judge with `/rc-aircraft-designer`,
  `/aircraft-design-scholz`, and a hobbyist — verify it opens a branch, applies
  *valid* geometry, iterates sensibly, presents a correct diff, and never claims
  it touched the live design. Fix findings before sign-off.

## 6. Sub-tickets (under #902)
1. **Edit-ops DSL + apply engine** — `copilot_edits.py` schema + `copilot_apply_service.apply_edits` (wing-ops → WingConfig → validated write; assumption-ops; recompute; reject-with-reason) + metrics-diff helper. Unit + integration tests.
2. **Proposal branch + write tools + read-retargeting** — `get_or_open_proposal`/`discard_proposal`, `apply_design_edits` + `discard_proposal` copilot tools, read-tool retargeting, system-prompt update. Integration tests (hub mocked).
3. **Frontend proposal UX** — "proposal pending" affordance in `CopilotStrip` deep-linking to the #901 versioning panel + compare. vitest.
4. **3-persona real-hub UAT + hardening** — drive real apply goals, judge, fix.

## 7. Deferred (later #902 slices)
CG/component + mission edits; `run_python` sandbox + goal optimization (Slice 3);
multi-proposal management; per-tab agents + supervisor (Slice 5); expert panel
(#929).
