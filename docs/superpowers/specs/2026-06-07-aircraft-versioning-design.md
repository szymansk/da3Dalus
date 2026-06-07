# Aircraft Versioning & Branching — Design Spec

**Epic:** #901 · **Date:** 2026-06-07 · **Status:** design approved, pre-implementation
**Foundation for:** #902 (AI Copilot — agentic changes land on branches; this is the safety net)

## 1. Goal & motivation

App-level **versioning & branching for whole aircraft**: experiment with design changes safely, compare variants side by side, roll back, keep alternatives. Today a change **overwrites** the aircraft in the DB — no undo, no before/after, no variants. This is the prerequisite for the AI copilot (agentic moves land on a branch = the undo).

Deliberately **app-level, not git** (a committed `db` symlink destroyed the dev DB twice on 2026-06-07, gh-895 — versioning belongs in the DB).

## 2. Settled decisions

- **Storage = real row copies, NOT JSON blobs.** A version/branch node is a full copy of the `aeroplanes` row + its owned subgraph as normal DB rows. **Decisive reason:** versions live in the same schema as live data → a data-model change is applied to all versions by the **normal Alembic migration**. JSON blobs would need separate versioned schemas + blob migration.
- **Replace the existing JSON system.** The current `design_versions` table + `design_version_service` (`_build_snapshot()` → JSON, and incomplete) is **retired**; row-copy becomes the single source of truth. Existing JSON snapshots are incomplete and are **NOT back-migrated** to row nodes (the data isn't there) — the table is dropped (or archived read-only), and versioning starts fresh from the current heads. The header "v3"/history affordance is repointed at the new system.
- **Git-like model:** the aircraft you edit **is** the mutable head node of the current branch; editing mutates it in place; snapshot/branch forks an immutable node off it. **Merge is excluded.**
- **Schema:** graph metadata as **columns on `aeroplanes`** + one **`branches`** table (no 1:1 wrapper table).
- **No automatic snapshots.** Snapshots are manual via the existing top-row **save icon**. AI changes land on a **branch** (the branch is the undo) → compare via the Metrics Dashboard → adopt (promote to main) or discard.
- **Provenance, not raw chat.** Raw `copilot_messages` are **not** cloned per branch. Each snapshot carries a `version_note` ("why" — manual in Phase 1; AI-generated summary of the chat-since-last-snapshot in #902) + a cheap `provenance_message_id` cursor (last `copilot_messages` id at snapshot time) so a later summarizer can reconstruct the delta. The immutable snapshot chain + timestamps + `created_by` is the provenance backbone (process summary, analyzable, **IP evidence**). A per-snapshot content hash is a future option, not built now.
- **Preview image per snapshot, generated via Plotly (server-side), not a screenshot.** Build the construction/planform Plotly figure from the (cloned) geometry and export to PNG (kaleido) → `preview_png`. Server-side so AI snapshots (no browser, #902) work too. Doubles as history thumbnail + frozen provenance visual. No separate Plotly-JSON stored (geometry is cloned → all views are re-derivable).

## 3. Data model

### New columns on `aeroplanes`
- `branch_id` → `branches.id` (nullable; null for legacy/unmigrated)
- `predecessor_id` → `aeroplanes.id` (the node this was forked from; null at lineage root)
- `root_id` → `aeroplanes.id` (lineage root; self at the root)
- `is_immutable` (bool, default false) — frozen snapshot vs mutable head
- `version_label` (str, nullable) · `version_note` (text, nullable, the "why") · `created_by` (`human`|`ai`)
- `provenance_message_id` (int → `copilot_messages.id`, nullable) — chat cursor at snapshot time
- `preview_png` (text/blob, nullable) — small (~256px) Plotly-rendered thumbnail, base64; travels with the row

### New table `branches`
`id` PK · `root_id` → aeroplanes · `name` (str: `main`, `ai/winglet`) · `head_id` → aeroplanes (current mutable node) · `is_main` (bool) · `created_by` · `created_at`

### Invariants
- The aeroplane picker shows only `branches.head_id` rows (`heads_only`); immutable snapshots are hidden history.
- Exactly one `is_main=true` branch per lineage (`root_id`).
- Mutations are rejected on `is_immutable=true` rows.

## 4. Clone service (engine)

`clone_aeroplane_subgraph(db, source, *, immutable, branch_id, predecessor_id, root_id) -> AeroplaneModel`
- Deep-copies the full owned subgraph; re-keys internal FKs; no `db.commit` (relies on `get_db`).
- **CLONED** (owned design + result state): wings → wing_xsecs → wing_xsec_details → spares / trailing_edge_devices → ted_servos; fuselages → fuselage_xsecs; weight_items; mission_objective; design_assumptions; aircraft_computation_config; stability_results; loading_scenarios; component_tree (re-key `parent_id` + component refs; re-key `loading_scenario.component_overrides` JSON); aeroplane JSON cols (`xyz_ref`, `assumption_computation_context`).
- **EXCLUDED — shared reference (keep FK):** `flight_profile`, component library, TED-servo `component_id`.
- **EXCLUDED — transient/lazy (recompute):** operating_points / operating_pointsets, flight_envelope.
- **EXCLUDED — conversation:** `copilot_messages` (provenance captured via note + cursor instead).
- **EXCLUDED — regenerated:** STEP paths (`step_path`, `solid_step_path`) → null, regenerated on demand.
- **Coverage test:** introspect all SQLAlchemy models with a (transitive) FK to `aeroplanes`; assert each table is in **either** the `CLONED` **or** the `EXCLUDED` set (with a reason). A new aeroplane-related table added without a decision → test fails. This is the safety mechanism.

## 5. Operations (service layer over the clone)

- `snapshot(branch, label, note, provenance_message_id)` → `clone(head, immutable=True)`, inserted as the head's predecessor (`head.predecessor = clone`); render `preview_png`; head keeps editing forward.
- `create_branch(from_node, name, created_by)` → `clone(node, immutable=False)` → new `branches` row, `head = clone`.
- `adopt_branch(branch)` → promote to main: `branch.is_main = true`, previous main demoted to a normal branch (kept). Merge-free.
- `restore(immutable_node)` → `create_branch(from immutable_node)` (fork an editable head from a frozen node).
- `discard_branch(branch)` → delete branch + its nodes (cascade). Guard: cannot discard `main` or the last branch.
- `compare(node_a, node_b)` → both nodes' Metrics-Dashboard payloads (via the existing metrics adapters / `assumption_computation_context`) for side-by-side. Read-only.
- `list_tree(root)` → the lineage graph (nodes, edges, branches, heads, notes, preview refs).

## 6. API

- `POST /aeroplanes/{id}/snapshot` `{label, note}` → immutable snapshot node
- `POST /aeroplanes/{id}/branch` `{name}` → branch + new head
- `POST /branches/{id}/adopt` → promote to main
- `POST /aeroplanes/{snapshot_id}/restore` → fork editable head from a snapshot
- `DELETE /branches/{id}` → discard (guarded)
- `GET /lineages/{root_id}/tree` → version graph
- `GET /aeroplanes/compare?a={id}&b={id}` → two dashboard payloads
- `GET /aeroplanes?heads_only=true` (default) → picker shows only heads

Pydantic schemas: `VersionNode`, `BranchOut`, `TreeOut`, `CompareOut`.

## 7. UI

- **Save icon (Header)** → wire `onClick` → snapshot dialog (label + "why" note) → `POST snapshot`. (Currently no handler.)
- **"v3"/history button (Header)** → **History/Variants panel** (seed of the future Design-Decisions tab, #902): the version tree (nodes with `preview_png` thumbnail, label/note/timestamp/`created_by`, branches, current head highlighted). Per-node actions: compare-select / branch-from / restore. Per-branch: adopt / discard.
- **Compare** → pick two nodes → Metrics Dashboard in **side-by-side compare mode** (small dashboard extension accepting two datasets).
- **Picker** → `heads_only`; branches of a lineage grouped/labelled.
- **Branch indicator** in the header breadcrumb (which branch/head you're on); `ai/…` branches visually marked.

## 8. Preview generation

Server-side: build the construction/planform **Plotly figure** from the cloned geometry and export to PNG via **kaleido** → `preview_png` (~256px thumbnail, base64). New backend deps: `plotly` + `kaleido`; a small figure-builder reused/derived from the existing planform/outline rendering. Works for human and AI (browserless) snapshots.

## 9. Sub-tickets (to cut under #901)

1. **DB model + migration** — columns on `aeroplanes`, `branches` table, drop/archive `design_versions` (no back-migration of incomplete JSON snapshots); backfill: each existing aeroplane becomes the head of a fresh `main` branch (`root_id = self`, `is_main = true`).
2. **`clone_aeroplane_subgraph()` + coverage test** — the engine + the all-tables-covered guard.
3. **Version operations + API** — snapshot/branch/adopt/restore/discard/compare/tree endpoints + schemas; picker `heads_only`.
4. **Preview generation** — backend Plotly figure-builder + kaleido → `preview_png`.
5. **UI** — save-icon → snapshot; History/Variants panel; dashboard compare mode; picker filter; branch indicator.

## 10. Deferred / out of scope

- Merge between branches (excluded by decision).
- AI-generated provenance summaries + the full Design-Decisions tab (Epic #902).
- Per-snapshot content hash / tamper-evidence (future IP hardening).
- Snapshot pruning policy (manual delete only for now; no auto-prune).
- 3D isometric preview (Plotly planform is the Phase-1 preview).
