# Remaining questions — what still needs the maintainer

> Companion to [`questions.md`](questions.md), produced on 2026-08-14 after the
> 2026-08-13 interview round. The 26 maintainer answers plus the two policies
> `P-WARN-0` and `P-DEAD-0` were applied to every remaining open question.
> Where an answer **followed necessarily** from a decision already taken, it was
> written into `questions.md` marked
> `_(derived — not a maintainer decision)_`. Everything listed here did **not**
> follow — it is a product call, a domain value, or a fact nobody has looked up.
>
> Rule used: *constrained but not determined* counts as still open. Where a
> bundle had some items settled and some not, the whole bundle stayed open and
> the settled part is recorded in the "already constrained by" column.
>
> **Updated after the wave-3 lookups.** The 18 questions that were factual
> rather than decisional have since been answered from the code and moved to
> [`## Resolved by lookup`](#resolved-by-lookup) below. Where such a question
> was a bundle whose *other* items are still decisions, the residual is named
> in that section and in the answer itself, so nothing drops off the interview
> list.
>
> **Updated again after the expert-consensus round (2026-08-14).** 25 further
> questions were decidable by *domain expertise* rather than by maintainer
> preference. They were put to the project's domain-expert skills under the
> authority hierarchy (Scholz/Sadraey lead → Anderson physics →
> AeroSandbox/AVL tooling → RC practice, RC-only and deferring to Scholz),
> framed for hobby RC and UAV aircraft (0.5–15 kg), and the rulings are now
> written into `questions.md` marked
> `_(expert consensus, endorsed by the maintainer 2026-08-14)_`. They are
> listed in [`## Resolved by expert consensus`](#resolved-by-expert-consensus)
> and removed from the tiers below. Full reasoning:
> [`expert-consensus-sizing.md`](expert-consensus-sizing.md),
> [`expert-consensus-powertrain.md`](expert-consensus-powertrain.md),
> [`expert-consensus-aero.md`](expert-consensus-aero.md).

## Summary

| | Count |
|---|---|
| Open questions processed | **159** |
| Derived (answer written into `questions.md`) | **41** |
| Resolved by code lookup (wave 3) | **18** |
| Resolved by expert consensus (2026-08-14) | **25** |
| Still open (placeholder untouched) | **75** |

Per module:

| Module | Processed | Derived | Resolved by lookup | Resolved by consensus | Still open |
|---|---:|---:|---:|---:|---:|
| Cross-cutting (`Q-CC-*`) | 5 | 1 | 1 | 0 | 3 |
| `aeroplane-core` | 10 | 4 | 0 | 0 | 6 |
| `wing-design` | 9 | 1 | 2 | 1 | 5 |
| `fuselage-design` | 7 | 0 | 1 | 2 | 4 |
| `airfoil-catalog` | 9 | 4 | 3 | 0 | 2 |
| `cad-generation` | 4 | 1 | 1 | 0 | 2 |
| `cad-designer-topology` | 5 | 2 | 1 | 0 | 2 |
| `construction-plans` | 8 | 2 | 1 | 0 | 5 |
| `openvsp-import` | 9 | 3 | 1 | 1 | 4 |
| `aero-analysis` | 8 | 4 | 2 | 0 | 2 |
| `avl-integration` | 8 | 2 | 1 | 1 | 4 |
| `mission-and-sizing` | 13 | 1 | 0 | 9 | 3 |
| `mass-and-balance` | 10 | 5 | 1 | 2 | 2 |
| `powertrain` | 13 | 1 | 1 | 7 | 4 |
| `versioning` | 7 | 3 | 0 | 0 | 4 |
| `ai-copilot` | 12 | 3 | 0 | 2 | 7 |
| `mcp-server` | 7 | 3 | 1 | 0 | 3 |
| `platform-core` | 7 | 0 | 0 | 0 | 7 |
| `frontend-workbench` | 8 | 1 | 1 | 0 | 6 |
| **Total** | **159** | **41** | **18** | **25** | **75** |

**Where the derivations came from.** `P-WARN-0` (14), `P-DEAD-0` (8),
`Q-MB-1` (5), `Q-CC-10` / `Q-CC-3` (4 each), `Q-CC-7`, `Q-CC-8`, `Q-CC-1`,
`Q-CC-4`, `Q-CC-5`, `Q-CC-11`, `Q-FD-2`, `Q-CC-15` (1–2 each), plus two
answered from the wave-2 code lookup rather than by decision (`Q-AF-3`,
`Q-CP-4`) — those two are still counted under **Derived**; the 18 wave-3
lookups are counted separately.

**Two modules produced no derivations at all** — `platform-core` and
`fuselage-design`. Both are almost entirely product calls (observability,
readiness, async job model, fit thresholds), which is worth knowing before the
next interview: they cannot be shortened by more policy work.

---

## Still open — proposed interview order

Ordered as in the original wave plan: remaining cross-cutting/root first, then
correctness-relevant, then module decisions, then cosmetic. The questions that
were purely factual (previously marked **⚙**) have been removed from these
tiers and answered in [`## Resolved by lookup`](#resolved-by-lookup); their
residual decisions are listed there. The 25 questions decidable by domain
expertise have likewise been removed and are listed in
[`## Resolved by expert consensus`](#resolved-by-expert-consensus).

### Tier 0 — remaining cross-cutting / root (6)

| Q-id | Title | Why it still needs you | Already constrained by |
|---|---|---|---|
| `Q-PC-1` | `NonFiniteSafeJSONResponse` app-wide? | Product call — **and in tension with the policy**: silently rendering NaN as `null` is itself an undeclared substitution, so "make it the default" and `P-WARN-0` pull in opposite directions. Needs your ruling on which wins. | `P-WARN-0` (a non-finite result must be *declared*, not quietly nulled) |
| `Q-CC-6` | `/api/v2` prefix vs 229 root routes | Product call on the public API shape; both directions are breaking. | `Q-CC-1` (no external consumers → the break is cheap), `Q-CC-11` (feeds the generated client) |
| `Q-CC-14` | Housekeeping bundle (4 items) | Three of four need you: the Docker geometry-kernel pin (was it chosen for a specific OCCT bug?), the committed `db/test.db`, and the `test/` root. | `P-DEAD-0` already settles the fourth — `azure-pipelines.yml` (broken path, non-default branch, no ticket) → delete |
| `Q-PC-3` | Structured logging / metrics planned? | Product call on observability scope for a single-user desktop app. | — (but `Q-MC-1`/`Q-MC-7` note that missing instrumentation is why the MCP commit defect went unnoticed) |
| `Q-PC-2` | `/ready` endpoint + startup summary | Product call. Deployment gating is weakened by `Q-CC-1`/`Q-CC-8` (no load balancer), but the "am I on the right Alembic head after a merge?" need is real and separate. | `Q-CC-1` (startup log line already mandated), `Q-CC-8` (single-worker assertion at startup) |
| `Q-CC-12` | Golden-file test for the MCP tool contract | Product call. Your pattern is pro-contract-test (`Q-CC-10`, `Q-CC-11`, `Q-VS-1`) but nothing makes it necessary here. | `Q-CC-11` (the same drift class, solved by generation on the REST side) |

### Tier 1 — correctness, safety, silent data loss (20)

These are the ones where a wrong or absent answer produces wrong numbers, a
lost artefact, or an unsafe part.

| Q-id | Title | Why it still needs you | Already constrained by |
|---|---|---|---|
| `Q-MB-7` | `GET /total_mass_kg` vs the `mass` assumption | Product call — which is authoritative, and does one derive from the other. | `Q-MB-1` (fixes the *computed* side to a single producer; says nothing about `total_mass_kg`) |
| `Q-PT-4` | Which spec-key spelling is canonical? | Domain naming call, and the enforcement point depends on the unresolved `Q-PT-5`. Today a battery imported under one spelling is invisible to the other consumer. | `Q-CC-9` (one vocabulary + normalise writers + backfill — the shape of the fix, not the key) |
| `Q-PT-7` | Should the whole COTS library be versioned? | Large product call — editing a component's `mass_g` retroactively changes every historical snapshot. | `Q-VS-1` (snapshot immutability is the guarantee being violated from outside) |
| `Q-VI-4` | Bug #814 — which body does the CAD download serve? | Product call: fix the sewing or change the download contract. The solid is the input to battery-bay cuts and carbon-tube bores. | `Q-VI-5` (derived) now records which sew tolerance was used, which will identify the affected bodies |
| `Q-VI-2` | `validate_geometry` — wire it or delete it? | **`P-DEAD-0` explicitly reserves this for an individual verdict** (one of the three finished, switched-off mechanisms). | `P-DEAD-0` (only "leave as is" is excluded) |
| `Q-AV-3` | AVL replay artefacts — wire or delete? | Same: one of the three reserved individual verdicts. | `P-DEAD-0` |
| `Q-CT-2` | `gp_D*` singleton mutation — ADR 0002 carve-out? | Only you can grant a carve-out from the freeze; the corruption is reachable from a real servo/engine build. | `Q-CC-13` (the freeze itself stands; only the *quality gate* exclusion was narrowed) |
| `Q-CP-9` | Construction-part storage and lifecycle (bundle) | Needs you on the missing traversal guard (`STORAGE_ROOT` outside `ARTIFACTS_BASE_DIR`), the untyped `material_component_id`, deletion of referenced parts and the leaked `mkstemp` files. | `Q-CC-7` (real FK + explicit `ondelete`, and the file lifecycle must follow the row lifecycle), `P-WARN-0` (null geometry must carry its reason) |
| `Q-CP-6` | What counts as a "destructive" spar edit? | Domain call, plus the 5 mm collinearity tolerance is a bare constant that changes meaning with aircraft size. | `Q-MC-1` (auto-snapshot before destructive writes — the same recoverable-by-construction stance) |
| `Q-CP-7` | `_migrate_tree_json` on every read | Product call: is the migration still needed, and should it become a one-off Alembic data migration. Today every read is a write, with no audit trail. | your consistent preference for real migrations (`Q-CC-5`, `Q-CC-7`, `Q-CC-9`, `Q-MB-1`) — a pattern, not a determination |
| `Q-WD-7` | Historical data audits (3 items) | Only you can answer from the live database whether pre-gh-402 / gh-1053 / gh-951 rows exist and whether re-entry is expected. | — |
| `Q-WD-4` | Is the `role is None` validation skip deliberate? | Validation-policy call — BR-12's gate is bypassable in two writes. | — |
| `Q-WD-11` | Does a stored `deflection_deg` persist into every trim? | Domain call; affects every trim on an aircraft with a pre-set surface. | `Q-WD-1` (the resolver now owns name resolution, not the baseline semantics) |
| `Q-FD-7` | Should `update_fuselage` preserve import artefacts? | Product call — today a UI edit can silently orphan an imported STEP. | — |
| `Q-AC-3` | Read-time cycle detection in the component tree | Robustness call; a cycle hangs the read path. Stakes raised by `Q-MB-1`. | `Q-MB-1` (the tree is now the only mass/CG source) |
| `Q-AC-4` | Are negative `scale_factor` / `quantity` legal? | Product call — is a negative quantity a deliberate "credit" affordance? | — |
| `Q-MS-9` | Design-assumption semantics (bundle) | Needs you on the zero-divergence rule, writing `calculated_value` onto a design choice, the no-op `switch_source` fan-out and the `0.0` "not set" sentinel. | `Q-CC-10`/`P-WARN-0` settle the resolver's missing-key behaviour (no defaults, `error` warning) and forbid the untraced suppressed fan-out |
| `Q-PC-4` | `schedule_retrim` short-circuit asymmetry | Confirmation of intent — a retrim scheduled during a compute is dropped, so the edit that triggered it may never be retrimmed. Survives `Q-CC-8` because it is *intra*-process. | `Q-CC-8` (only intra-process defects remain real work) |
| `Q-VS-6` | Branch and lineage edge cases (bundle) | Six lineage-integrity calls, incl. `discard_branch` truncating surviving nodes' history and `compare` diffing nothing. | `Q-CO-12` (typed `branch_kind` + partial-unique-index precedent covers the proposal case only) |
| `Q-CO-11` | Should prompt policy become server-side validation? | Architecture/product call — prompt text is currently the only guard on the copilot's numeric claims. | `P-WARN-0`/`Q-CC-10` settle one item: a missing `x_np_m` may not silently disable the gh-924 single-source override |

### Tier 2 — module design decisions (32)

| Q-id | Title | Why it still needs you | Already constrained by |
|---|---|---|---|
| `Q-CP-2` | Where do servo / engine / component information come from? | Data-source design call; three of 29 Creators are unreachable through REST. | `P-DEAD-0` (they may not stay inert indefinitely) |
| `Q-VI-6` | Assert the export-unit ↔ detection dependency? | Design call on invariant enforcement. | `Q-FD-2` (the plausibility layer covers part of it) |
| `Q-WD-3` | TED representation (bundle) | Needs you on the `Servo`-or-`int` servo union, NULL servo dimensions, and which layer supplies the CAD-build default. | `Q-CC-9` settles the fourth item: the TED `role` gets a DB CHECK constraint |
| `Q-WD-2` | Can the `units` block express the mm spar exception? | Design call: correct the field descriptions vs add a per-field storage-unit override. | `Q-FD-2` (storage units stay as they are) |
| `Q-FD-5` | Should a 5–30 s slice become an async job? | Product call — changes the contract from 200-with-body to 202-with-status. | `Q-CP-1` (CAD work belongs in the process pool — stated for plan execution, not extended to slicing) |
| `Q-FD-8` | Is `from_step_file` dead, and is a parametric CAD fuselage planned? | The roadmap half is load-bearing for the module's whole dual-representation design. | `P-DEAD-0` settles the dead `set`-of-`dict` path itself |
| `Q-AF-6` | Where does the batch backfill run from? | Operator-surface design call (chunking, cancellation, moving out of `scripts/`). Pairs with `Q-PC-5`. | — |
| `Q-CG-5` | Fuselage tessellation + cache unique constraint | Roadmap call (is a producer planned) plus a DDL call. | `Q-CC-8` (the multi-process framing collapses; the duplicate-row risk is intra-process and survives) |
| `Q-CT-5` | Dead topology code (bundle) | The user-facing half is yours: `round_inside` / `round_outside` are selectable hinge types that cannot build — narrow the literal or write the sketch creators? | `P-DEAD-0` settles the four dead items (`construct`, `create_XYZ_ted_sketch`, `scaleXyz`/`y_sacle`, `offest3D` + checkpoints) → delete |
| `Q-AC-5` | Is an empty `AirplaneConfiguration` export legal? | Product call; separately `self.wings[0]` raises `IndexError` at construction. | — |
| `Q-AC-9` | Is `_to_json_compatible` permanent or transitional? | Ownership call: tighten the converter hub's return contract vs keep the defensive stripper. | — |
| `Q-AA-4` | Are the duplicated geometry listeners deliberate? | Design call — every geometry write fires the bus twice. | — |
| `Q-AV-4` | Should a successful regenerate clear `is_dirty`? | UX call — the user-editable `.avl` escape hatch silently stops taking effect. | — |
| `Q-MS-10` | Should a mission-preset change fan out? | Architecture call, incl. whether the resulting recompute/retrim storm needs a batch mode. | `Q-MS-1` (the presets are being re-authored anyway — good moment to decide) |
| `Q-MS-13` | Loading-scenario and profile constraints (bundle) | Needs you on `component_uuid` validation, `ga_runway`'s absence from `AircraftMode`, and the PATCH-side consistency validator. | `Q-CO-12` (partial-unique-index precedent for the unconstrained `is_default`), `P-DEAD-0` (`force_recompute` is dead surface) |
| `Q-PT-5` | Is the `component_types` schema a contract or a minimum? | Design call; gates `Q-PT-4`'s enforcement point. | — |
| `Q-PT-11` | Should the performance endpoint keep requiring an unused aeroplane? | Roadmap call — is aircraft state expected to enter the computation later. | `Q-CC-3` settles two of three contract rows (envelope; helpers stop raising `HTTPException` directly) |
| `Q-VS-2` | Long-term growth bound for snapshots | Product call (prune/expire policy, thumbnail layer). Compounded by the copilot cloning a subgraph per proposal. | — |
| `Q-VS-5` | Copy `construction_parts` on clone? | UX call — a branch is currently not a complete copy of the design. | `Q-CC-7` (real FK makes the table visible to the coverage test; files must follow rows) |
| `Q-VS-8` | Should the versioning routes expose UUIDs? | API-identity call; the one place the public surface is internally inconsistent. | `Q-CC-11` (a generated client makes the inconsistency more visible) |
| `Q-CO-1` | Wire or remove the AI audit trail? | Product call: was a "show me the chat that produced this version" view intended? | `P-DEAD-0` (both halves may not stay inert), `Q-CC-9` (provenance is a live concern) |
| `Q-CO-4` | Persist the turn from a background task + heartbeat? | Design call — a client disconnect loses the assistant message while the proposal branch survives. | — |
| `Q-CO-5` | Is conversation branching still planned? | **This is exactly the input `P-DEAD-0` rule 2 needs**: with a live ticket the scaffolding stays behind `# UNREACHABLE(gh-N)`; without one it is deleted. Plus the `sort_index` `COUNT(*)` race. | `P-DEAD-0` (named as scaffolding-for-planned-work) |
| `Q-CO-10` | Is the "agentic expert panel" still planned? | Roadmap call, incl. whether the hard-coded knowledge tables should come from the `rc-aircraft-designer` / Scholz skill data. | `P-DEAD-0` (the unread `COPILOT_EMBEDDING_MODEL` setting), `Q-CC-4` (settings merge) |
| `Q-MC-7` | Is standalone `run_mcp_server` still used? | Needs you: is the mode alive (then `P-DEAD-0` keeps it) or dead (delete)? Instrumentation pairs with `Q-PC-3`. | `Q-CC-1` settles the bind address (respect `UVICORN_HOST`, loopback default) |
| `Q-PC-5` | Move the airfoil backfill out of `scripts/`? | Architecture call — application code importing from `scripts/` inverts the dependency. Pairs with `Q-AF-6`. | — |
| `Q-PC-6` | Reject a relative `ARTIFACTS_BASE_DIR`? | Validation-policy call; same bug class the `AIRFOILS_DIR` comment documents. | `Q-CC-4` (one settings class to put the validator in) |
| `Q-FW-3` | Global `SWRConfig` + shared key module? | Design call — expensive solver endpoints currently revalidate on window focus. | `Q-FW-1` (SPA-direct premise confirmed) |
| `Q-FW-4` | Component size budget / design-system layer | Product call; the seven 1 000+ line panels are where a re-implementation spends most effort with least guidance. | — |
| `Q-FW-5` | Bound the tessellation cache? | Perf/product call (LRU, TTL, WebGL context disposal). | `Q-CC-8` (process-locality is accepted; unbounded growth is not addressed) |
| `Q-FW-6` | Plan for moving off the Next.js canary | Roadmap call; the spec currently documents canary behaviour as contract. | — |
| `Q-FW-7` | Error boundary, stale-id reset, `beforeunload` guard | Product call — four independent ways to lose the session. | — |

### Tier 3 — cosmetic, scope confirmations, contract tidying (17)

| Q-id | Title | Why it still needs you | Already constrained by |
|---|---|---|---|
| `Q-AC-2` | Should `aeroplanes.name` be unique? | Confirm UUID-only identity is the intended contract. | `Q-CC-5` (the German 409 message is translated regardless), `Q-CC-3` |
| `Q-AC-10` | Is subtree deletion contractual or incidental? | Confirmation before callers rely on a SQLAlchemy cascade. | `Q-CC-7` (whatever the answer, the delete policy must be explicit per table) |
| `Q-FD-1` | Duplicate name: 409 (fuselage) or 422 (wing)? | Both are defensible; you pick. | `Q-CC-3` (shape settled, status code not) |
| `Q-AF-7` | Is renaming an airfoil forbidden by convention? | Two confirmations (no `ON UPDATE CASCADE`; the missing ORM relationship is deliberate). | `Q-CC-7` (explicitly "constrains `Q-AF-7`") |
| `Q-CG-6` | Is `_template_runs` in plan listings a bug? | Confirmation of intent. | — |
| `Q-CP-8` | Is template → plan provenance wanted? | Design change, currently `Won't`. | — |
| `Q-VI-10` | Is epic #638 (B5 / B6) still the direction? | Scope confirmation alongside ADR 0018. | — |
| `Q-AA-9` | Is `recompute_assumptions`'s 750-line form deliberate? | Style/roadmap — does the spec prescribe the same shape. | — |
| `Q-AV-2` | Is the wing-only AVL model an accepted limitation? | Scope confirmation; the two solvers disagree on `Cnb` by construction. | — |
| `Q-AV-8` | Was file-based `.mass` / `.run` input deliberately dropped? | Scope confirmation for eigenmode / dynamic analysis. | — |
| `Q-MB-3` | Is lateral/vertical CG out of scope? | Roadmap confirmation for two published-but-unread fields. | — |
| `Q-CO-6` | Rename, remove or implement `diff_vs_live`? | Product call on a misleading name that costs prompt tokens. | — |
| `Q-CO-8` | Is mid-wing `AddXsec` planned? | Same `P-DEAD-0` rule-2 input as `Q-CO-5`: live ticket or delete. | `P-DEAD-0` (named as scaffolding-for-planned-work) |
| `Q-MC-2` | Is the MCP surface intentionally frozen? | Scope confirmation: deliberate subset or maintenance gap. | — |
| `Q-MC-8` | Is there a review process for tool descriptions? | Process question; the descriptions are an agent's only documentation. | `Q-CC-12` (the proposed detector) |
| `Q-PC-7` | Is `bind_loop` correctly the one intolerant startup step? | Confirmation — note it is **no longer the only one**: `Q-CC-8` adds a hard refusal to start with more than one worker. | `Q-CC-8`, `Q-CC-4` (the `run_app` 8000-vs-8001 default) |
| `Q-FW-9` | Explicit labels for the two copilot write tools | Small UX wording call. | — |

---

## Resolved by expert consensus

These 25 were open because they needed a *domain* answer, not a product
preference. They were put to the project's domain-expert skills under the
authority hierarchy from `CLAUDE.md` — `aircraft-design-scholz` (Scholz /
Sadraey) as lead, `aerodynamics-expert` (Anderson) as physics ground truth,
`aerosandbox-expert` / `avl-advisor` as tooling, and `rc-aircraft-designer`
as lower-authority RC practice that defers to Scholz on conflict — framed
throughout for **hobby RC and UAV aircraft (0.5–15 kg), not
transport-category design**. Each answer is now written into `questions.md`
marked `_(expert consensus, endorsed by the maintainer 2026-08-14)_`, with
the deciding authority and a confidence level; the full reasoning, including
every worked number, is in
[`expert-consensus-sizing.md`](expert-consensus-sizing.md),
[`expert-consensus-powertrain.md`](expert-consensus-powertrain.md) and
[`expert-consensus-aero.md`](expert-consensus-aero.md).

### Sizing, performance, stability, mass & CG (9)

| Q-id | Recommendation | Confidence |
|---|---|---|
| `Q-MS-2` | The gh-477 energy balance is the authoritative landing distance — Roskam §3.4 is calibrated on a braked Cessna 172N (`μ_brake = 0.4`) and is invalid for unbraked 0.5–15 kg models (48 % apart on a 1.5 kg trainer: 35.5 m vs 52.5 m); `t_static_N` on `mission_objectives` wins. | high |
| `Q-MS-3` | `LANDING_SURFACE_MU` is a **deceleration coefficient `a/g`**, not tyre friction — rename it, keep 0.15/0.22/0.30/0.40, raise `hard_paved` 0.07 → 0.10, add braked 0.40, replace the fixed 15 m flare with `h_obs·(L/D)_app`; the WCL constant is wrong three ways — use `W/S_max = (WCL[oz/ft³]·9.818)^(2/3)·W^(1/3)`, drop the spurious `AR^0.25`, raise trainer 6 → 9 oz/ft³. | high (WCL) / medium (μ) |
| `Q-MS-6` | Persist **both** `n_target` and `cl_trimmed` — `n = 1/cos φ` exactly, so `turn_60` at n = 1.0 is a **factor-of-two error**; correct placement also exposes that the turn velocity `1.3·V_S` is inside the stall boundary at 60° bank (needs ≥ 1.414·V_S). | high |
| `Q-MS-7` | Add an explicit `role` field (`best_ld` ← `max_range`, `min_sink` ← `loiter_endurance`, `max_turn` ← `turn_60` — the prop-aircraft mapping); gate the `"trimmed"` tier on `status == TRIMMED` **and** within 5 % of the polar `v_md`/`v_min_sink`. Nearest-match is unstable — reject it. | high |
| `Q-MS-8` | One `V_max` (declared → computed `V_H` → 1.35·V_cruise, never a bare 28.0), `V_C = 0.9·V_H`, `V_D = 1.4·V_C`; **ρ = 1.225 is correct** — a V-n diagram is an EAS chart and the real bug is plotting TAS markers on it; a missing gust envelope must name the missing input (gust sensitivity ∝ 1/(W/S), so it is *most* critical at this scale); snapshot every shaping input plus a context hash; cold start → 422. | high (8.2–8.5) / medium (8.1) |
| `Q-MS-11` | Unit is **N/m²** and the 10–120 band is right (1 g/dm² = 0.981 N/m², correct in both units to 2 %); **`412` is a full-scale value — default to 55 N/m²**, show g/dm² as a secondary label, and return `None` not `0.0` for a degenerate axis range. | high |
| `Q-MS-14` | Seeded default **0.10** (not 0.12), delete the inline 0.10 in `sm_suggestions.py`, precedence user > preset > default; presets are already correct **except `acro_3d = 0.0`, which must become 0.03** (Sadraey: dynamically unstable within 2–3 % MAC of the NP); add error < 0.02 / warning < 0.03. | high |
| `Q-MB-2` | The formula is exactly Sadraey Eq. 11.18 — cite it in ADR 0011; make `mass_cg_service.compute_recommended_cg` the single implementation and have the other two delegate; drop the dead `/recommended_cg` schemas; return the NP provenance, because a VLM `x_np` is power-off and fuselage-free so the real SM is *smaller* than computed. | high |
| `Q-MB-6` | Keep `cg_design − cg_agg` but rename to `required_cg_shift_x_m` ("positive = move mass aft"), state "x positive aft from datum" in the contract, and ship a categorical `cg_verdict ∈ {NOSE_HEAVY, TAIL_HEAVY, ON_TARGET}` the UI drives off instead of the sign; report Δx in % MAC and make the tolerance 1 % MAC (floor 5 mm). | high |

### Powertrain / propulsion (7)

| Q-id | Recommendation | Confidence |
|---|---|---|
| `Q-PT-1` | Gate on **peak** (not cruise) current at sag voltage: `cont ≥ 1.4 × I_design`, `burst ≥ motor.max_current_a`, two-sided cell window at 4.2 V/cell, BEC gate **before** the sort; then sort lightest → smallest → id, and return a *reason* when `esc_id` is null. | high |
| `Q-PT-2` | Yes — add propeller `weight_g` to `total_mass` (1–3 % of AUM, always one-signed on stall speed); do **not** apply Sadraey's GA installation factor at this scale; a NULL mass must raise an error-severity warning and exclude the candidate, never contribute zero. | high |
| `Q-PT-3` | Yes — the fixed 0.30 m placeholder is up to **2× wrong** at 6–8 in; size D from power, take `J` from the selected propeller's polar (fallback `J = 0.95 × P/D`, measured), cap tip speed at 150 m/s, keep `load_rpm_factor = 0.85`, and take `eta_prop` and `weight_g` from the same propeller. | high |
| `Q-PT-6` | **Rm is not a prerequisite** (maintainer, on verified data availability): the fixed-RPM model stays the default, the QPROP path is offered only for motors that have Rm, and the response **declares which model fidelity was used**. Add the field and populate it **opportunistically** from vendors who publish `Ri` (Hacker, Scorpion, T-Motor, AXi); partial coverage is accepted and made visible. D-Power publishes no Rm and its manuals carry a one-row-per-motor spec table, not a bench table — **the PDF/voltage-balance-fit route is investigated and closed**. Never synthesise Rm from Kv and i₀. | high |
| `Q-PT-9` | Yes to ISA — one shared helper wrapping `asb.Atmosphere` with a closed-form ISA fallback (aarch64 guard), deleting all three duplicate density paths — **but ship `temperature_deviation` and `density_altitude()` with it**: a hot day is worth 350–1000 m of density altitude, 3–6× the model error being fixed. | high |
| `Q-PT-10` | Not out of scope — a windmilling prop costs **20–45 % of glide ratio** on a typical RC e-glider. Keep `max(Ct, 0)` in the thrust path; add a `prop_state` drag increment on the aircraft polar (`k_prop` on disk area: folded 0–0.01, stopped 0.02–0.05, windmilling 0.05–0.20 default 0.10, hard ceiling 8/9). | high (belongs in budget) / medium (coefficients) |
| `Q-PT-12` | Yes to the inertia guard, two-tier: absolute `1e-7 … 1e-2 kg·m²` plus dimensionless `0.010 ≤ I/(m·D²) ≤ 0.10` (observed 0.0204–0.0676; hard physical ceiling 0.25) — drop the field and count the skip on failure. Add a **content hash** for the freshness decision and keep `source_version` for provenance; checksum the snapshot too. | high |

### Aerodynamics, geometry & trim (9)

| Q-id | Recommendation | Confidence |
|---|---|---|
| `Q-WD-5` | Enforce it — **in the Pydantic schema layer, not in the frozen `cad_designer`** (maintainer refinement). Within a segment chords differ freely (that is taper); between segments the invariant holds only because construction goes through `add_segment`, which `from_json_dict` bypasses — so a deserialised structure can carry a discontinuity while the API path silently discards a supplied root chord. Reject with 422 naming the previous segment's tip chord, or accept with a `DesignWarning` — never silently. Tolerance: exact equality at 1 µm. | high |
| `Q-FD-3` | **Not a bare runtime assertion** — the mode that matters most (the `a ↔ b` swap) is volume-neutral and invisible to any integral metric. Instead: collapse the two `2.0 * a` conversions into one `superellipse_to_asb_xsec()` seam; assert against the **STEP bounding box** where a `step_path` survives (`2a ≤ 1.02·Y_extent`, aspect ratio within 20 %) — which doubles as the historical audit query; and a `[0.3, 3.0]` aspect-ratio band as a `DesignWarning`, never an exception. | high (analysis) / medium (numbers) |
| `Q-FD-4` | Good `[0.95, 1.05]` → silent; degraded `[0.85, 1.15]` → `info`; poor `[0.70, 1.40]` → `warning`; **reject** outside `[0.70, 1.40]`, or `volume_ratio ≤ 0.05`, or non-finite. The 1.40 cut catches the Q-FD-3 factor-2 bug; the ≤ 0.05 / non-finite cut catches the degenerate dimension that produced 15/15 NaN on the Stratos. **Yes, warn on a bound-hitting `n`**: `info` per station, escalating to `warning` above 25 % of stations. | medium-high |
| `Q-VI-8` | **#791: ship** — the loss is a pure `C_L0`/`C_m0` offset that provably leaves `C_Lα`, the ac, the neutral point and static margin untouched, and the geometry says the importer's share is `ΔC_L0 ≈ 0.10–0.17`, not 0.43 (VSPAERO overshoots by more than the importer undershoots); retitle to "`α_L0` fidelity", warn above 0.5° of `Δα_L0`, and fix the separate lost-XForm-incidence bug. **#792: accept** — keep AeroBuildup default, scale `spanwise_resolution = max(1, round(120/n_sections))` + `chordwise_resolution = 8` + `run_symmetric_if_possible`. | high (physics) / medium (root cause) |
| `Q-MS-5` | No deflection grid — the defect is rank deficiency, not resolution. Use a two-point secant on δE (exact in one step, 2× cost); add `CONTROL_AUTHORITY_LIMIT` as a third status carrying the required δE; tighten trim to `\|C_m\| ≤ 0.01` / `\|ΔC_L\| ≤ 0.02`; raise the Opti-failure log to WARNING. | high (diagnosis) / medium (numbers) |
| `Q-MS-12` | Store the trimmed `C_L` and solved deflections on the operating point; derive turn banks from `target_turn_n` via `φ = arccos(1/n)` (today the hardest turn is n = 2.0 while a user asking n = 3.0 gets no warning); require `has_pitch_control`; make `STALL_IN_TURN` a bare token; re-express the six weights as three tolerances (0.01/0.02/0.03, `w = 1/tol²`) plus a `1e-3` regulariser; persist the reference-speed provenance. | high (definitions) / medium (weights) |
| `Q-AV-6` | An inconsistency — **but the fix is a merge, not a swap.** `Sref/Cref/Bref/Xref` are global header data that "correspond to the total geometry" (avl_doc:289), so a full-airplane file genuinely cannot be reused by deleting surfaces; spacing, `CDCL`, `CLAF` and `CONTROL` are per-`SURFACE` and can be. Lift the matching `SURFACE` block verbatim, always regenerate the header from the pruned wing, warn when no match exists, and report `avl_source` either way. Silence is the one unacceptable option. | high |
| `Q-CO-7` | **The sum is correct; the comment is wrong** — sweep is a chordwise *distance* along an invariant `xDir`, so `x_k = x₀ + Σ sweep_i` and the merged segment must reproduce `x_{j+1} − x_{j−1} = sweep_j + sweep_{j+1}`; a weighted average halves it (40 + 80 = 120 mm, not 60 mm). Fix the comment, add that regression test, and warn when the merged dihedrals differ by > 2°. | high |
| `Q-CO-13` | **Yes — read `ctx["v_cruise_mps"]`** exactly as `_run_stability_async` already does in the same file, and report V, altitude and Re in the summary; replace the fixed α range with **[−6°, +16°] at 1° steps (23 points)**; never sweep velocity. At RC scale `Re = v·t_mm·70` makes 12 vs 20 m/s 168 k vs 280 k, where `C_Lmax` varies by −54 % and profile drag nearly doubles — a bigger error than Q-VI-8's camber loss. | high |

**Two rulings carry a maintainer correction that overrides the consensus
document**, recorded in the answers themselves:

- **`Q-PT-6`** — the consensus made sourcing Rm a prerequisite (vendor →
  bench-table fit → locked-rotor measurement). The maintainer has no test rig
  and cannot buy 41 motors, and two facts were verified: D-Power publishes no
  winding resistance, and its manual PDFs carry a **one-row-per-motor
  specification table**, not a multi-point bench table — so a voltage-balance
  fit is impossible from that source. Recorded as: Rm is **not** a
  prerequisite, the fixed-RPM model stays the default, fidelity is declared
  per response, coverage is opportunistic and partial, the PDF route is
  **investigated and closed**, and the method hierarchy survives only as
  documentation of how Rm should be obtained if a source ever provides it.
- **`Q-WD-5`** — the consensus said "enforce it by removing the field". The
  maintainer refined this: the invariant is a property of the **construction
  API** (`add_segment`), not of the data structure, and `from_json_dict`
  bypasses it — so the guard belongs in the **Pydantic schema layer**, not in
  the frozen `cad_designer` topology (ADR 0002).

**Residual still yours.** Only one of the 25 leaves a named remainder:

| Q-id | What is still yours |
|---|---|
| `Q-MS-12` | Two of the six items are **contract shape, not physics**, and were deliberately flagged rather than ruled on: whether `replace_existing` is scoped to the set or renamed (today it deletes manually created points aircraft-wide), and the SSE stream's `targets`/`skip` filtering, where a capability-gated target appears in neither array and `skip` carries no reason. |

Several rulings also carry **medium**-confidence values that invite later
calibration rather than a decision: `Q-MS-3`'s `Δ_aero = 0.06` (one
instrumented RC landing would settle it), `Q-MS-14`'s acro target 0.03 vs
0.05, `Q-PT-10`'s `k_prop` brackets, and `Q-FD-3`/`Q-FD-4`'s band edges.

---

## Resolved by lookup

These 18 were open only because nobody had read the code. They were resolved
the way `Q-AF-3` and `Q-CP-4` were in wave 2 — by a lookup agent producing
citations — and **cost no interview time**. Each answer is now written into
`questions.md` marked
`_(resolved by code lookup — not a maintainer decision)_`; the full evidence is
in [`wave3-lookups.md`](wave3-lookups.md).

| Q-id | Verdict |
|---|---|
| `Q-PT-13` | **Confirmed defect (high severity).** The containment check is absent from `components.py`; the **upload** path is safe by construction, the **download** path (`GET /components/{id}/model` + client-writable `model_ref`) is an unauthenticated arbitrary-file-read. §A |
| `Q-CC-17` | **Confirmed defect.** The cycle is real — `ImportOpenVspButton.tsx ↔ ImportProgressBar.tsx` — 1 error / 16 warnings / 5 info, exit code 1, and `deps:check` is not in CI. §B |
| `Q-AF-4` | **Confirmed safe.** `db/suitability` (`:492`) precedes `db/{name}` (`:698`); no route is shadowed, and existing 422 assertions pin it behaviourally. §C |
| `Q-AF-5` | **Confirmed defect on 3 of 6** (no-polar airfoils scored `0.0`, Lens-2 null coerced upstream, unguarded `import aerosandbox` breaking ADR 0012 for the whole router); **safe on 3** (null-metric row, `_level_flight_cl` call sites, 409/200 duplicate upload). §D |
| `Q-AF-1` | **Confirmed safe** for the bundled corpus — 0 Lednicer candidates in 1 665 files, and no file loses a coordinate to the header skip. §E |
| `Q-CT-4` | **Confirmed safe.** `euler_xyz` is display/serialisation-only and is not even read back on deserialisation; the convention is unobservable. §F |
| `Q-FD-6` | **Confirmed defect on the ≥ 2-usable-slices item** (200 with 0–1 xsecs is reachable); axis resolution and the 500 / 4 096 bounds confirmed as-is. §G |
| `Q-VI-9` | **Blocker cleared, one confirmed defect.** CUSTOM = 5 API calls, 12×32 `CompPnt01` → Y/Z bbox half-axes, `n=2.0`; a mid-body sampling failure truncates the body without marking it lossy. §H |
| `Q-WD-9` | **Confirmed defect + confirmed safe.** Duplicate control name → opaque **500** with the message dropped; `required_section_modulus` → **422** produced one layer up. §I |
| `Q-WD-10` | **Confirmed safe / as-specified.** `xtr_opt` is never persisted (adoption stays manual); `symmetry_factor` is read from `wings.symmetric` via the ASB converter, not inferred. §J |
| `Q-AA-5` | **Confirmed safe to move.** No ordering guarantee depends on the pairing; moving the marking into the handlers is a pure refactor. §K |
| `Q-AA-6` | **Confirmed defect.** No `ondelete`, no ORM cascade, no service cleanup, no SQLite FK enforcement — and 22 live orphans in the working database. §L |
| `Q-CG-4` | **Confirmed safe — the wiring is small, not hard.** Both TODO blockers are already solved in-repo; only the canonical dict for `compute_geometry_hash` is open. §M |
| `Q-MC-6` | **Confirmed safe** on all three `request=None` paths; separately **confirmed defect**: `download_export_zip` omits three required arguments and always raises `TypeError`. §N |
| `Q-MB-11` | **Confirmed safe.** A `3d_print_material` spec, not a node field; only `print_type` is node-level, so the `aeroplane-core` contract is the one to correct. §O |
| `Q-FW-8` | **Confirmed dead code.** `metricsMock.ts` has zero imports anywhere; `no-orphans` cannot see it, so that info list undercounts dead modules. §P |
| `Q-CP-5` | **Confirmed safe** on the stock half — snapping runs on 100 % of production paths; only persistence remains a decision. §Q |
| `Q-AV-1` | **Confirmed defect, fix available.** AVL prints `Trim convergence failed` on stdout; the current inference is inert because a failed run writes no file, and the user gets a misleading 500. §R |

**Residual decisions still on the interview list.** Fifteen of the eighteen
leave a named remainder, recorded in the answer itself and carried forward
here — they are *smaller* than the original question, not gone:

| Q-id | What is still yours |
|---|---|
| `Q-PT-13` | The bundle's other four items: the silently-dropped `PUT` on component types, the missing delete guard for *components*, the guard ordering, and whether `cots_import` should read the taxonomy from the DB. |
| `Q-CC-17` | Whether `deps:check` joins the frontend CI job. |
| `Q-AF-4` | Whether to add an explicit route-order assertion. |
| `Q-AF-5` | Whether the main sweep should adopt the `include` path's "not fabricated" rule instead of ranking a `0.0`. |
| `Q-AF-1` | Whether to add format sniffing on the **upload** path (`POST /airfoils/datfile` validates nothing today). |
| `Q-FD-6` | Whether a failing component-tree sync should block a fuselage delete. |
| `Q-VI-9` | `_read_section_parm`'s one-index fallback intent, and whether `_u_to_segment_index` should clamp or report. |
| `Q-WD-9` | The 422-vs-500 call for duplicate control names, and whether `required_section_modulus` should become a domain exception anyway. |
| `Q-WD-10` | Whether Slice 3 (persisting the optimum) is wanted, plus the per-section → per-segment mapping. |
| `Q-AA-5` | Whether to actually move the marking into the handlers. |
| `Q-AA-6` | `ondelete="CASCADE"` vs an ORM cascade, the one-off migration for the 22 orphans, and the bundle's other three state-machine items. |
| `Q-CG-4` | Whether #202 is wanted at all (`P-DEAD-0` wire-or-delete), and if so the canonical dict feeding `compute_geometry_hash`. |
| `Q-MC-6` | Whether to pin `request=None` with a test. |
| `Q-FW-8` | The other five hygiene items (dark-theme-only, shared Plotly layout, deep-linkable selection, `treeMode` persistence, the mirrored gauge-zone literals). |
| `Q-CP-5` | Whether the plan itself should be persisted for provenance. |

`Q-CT-4`, `Q-MB-11` and `Q-AV-1` leave no residual decision — they are closed
outright.

---

## Residuals inside derived answers

Three derived answers deliberately leave a named remainder, recorded here so it
is not lost:

- **`Q-MC-4`** — the exception/capability mapping is derived; whether
  `tools/list` is itself **capability-filtered** is still a protocol/UX call.
- **`Q-MC-3`** — single-worker and "no externalisation" are derived; the
  **unbounded, never-evicted `ASSET_REGISTRY`** and the un-cleaned
  `tmp/mcp_assets/` are not covered by it, and the `base_url` 8000-vs-8001
  default rides on `Q-CC-4`'s settings merge.
- **`Q-MB-5`** — the `PUT`/`PATCH` question dies with `weight_items`, but the
  same `model_dump()`-without-`exclude_unset` defect should be re-checked on the
  component-tree update path during the migration.

*Related: [`questions.md`](questions.md) · [`wave2-lookups.md`](wave2-lookups.md) ·
[`wave3-lookups.md`](wave3-lookups.md) · [`gaps.md`](gaps.md) ·
[`confidence-report.md`](confidence-report.md)*
