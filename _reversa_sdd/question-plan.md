# Question Plan — dependency-ordered interview for `questions.md`

> Built from `_reversa_sdd/questions.md` (185 `## Q-` sections, 19 modules),
> cross-read against `gaps.md` and ADRs 0002, 0004, 0005, 0006, 0007, 0009,
> 0010, 0011, 0012, 0016, 0017.
>
> **What this file is for:** `questions.md` is ordered by module. That is the
> wrong order to *answer* it in — roughly two thirds of the questions stop
> being open once a handful of upstream decisions are made. This file gives the
> order, the reasons, and a briefing note per high-leverage question so the
> interview can run without re-reading the catalogue.

---

## Summary

| | Count | Notes |
|---|---|---|
| **Total questions** | **185** | `Q-CC` 17 · `Q-AC` 10 · `Q-WD` 11 · `Q-FD` 8 · `Q-AF` 9 · `Q-CG` 6 · `Q-CT` 5 · `Q-CP` 9 · `Q-VI` 10 · `Q-AA` 9 · `Q-AV` 8 · `Q-MS` 14 · `Q-MB` 11 · `Q-PT` 13 · `Q-VS` 8 · `Q-CO` 13 · `Q-MC` 8 · `Q-PC` 7 · `Q-FW` 9 |
| **Roots** (≥2 outgoing edges) | **23** | 8 of them are themselves downstream of another root |
| **Downstream-only** | **103** | at least one incoming edge, no outgoing |
| **No question→question edge** | **59** | of which **28** are still resolved or constrained by a policy cluster |
| **Genuinely independent leaves** | **31** | answer these in any order, or not at all |
| **Policy clusters** | **8** | collectively resolve or constrain **110 of 185** questions |
| Already flagged **Blocking** by the catalogue | 12 | all 12 land in Wave 0–2 below |

Two clusters have **no existing question as their root** — the policy is asked
185-times-in-miniature but never once as itself. Those two proposed decisions
(`P-WARN-0`, `P-DEAD-0`) are the highest-leverage additions to the interview.

**Single highest-leverage question in the catalogue: `Q-CC-10`**
(`assumption_computation_context` as a versioned, validated contract). It is
simultaneously the root of the aero-correctness chain (`Q-AA-1`, `Q-MS-4`,
`Q-MS-9`, `Q-PT-8`, `Q-CO-11`, `Q-MB-7`) *and* the densest concrete instance of
the warning policy — ~40 keys, 9 consumers, every one of them substituting an
RC-typical default on a miss. The catalogue's own note ("the highest-leverage
structural question in the corpus") matches what the graph says.

---

## Policy clusters

Eight recurring policies. Each is the *same* decision asked once per module.
Deciding the policy once collapses the listed questions from "open" to
"instance of a decided rule".

### PC-1 — Design-warning surfacing policy · **34 questions** · ADR 0012

> **Proposed single decision (`P-WARN-0`, no existing Q-id):**
> *Is there ONE structured warning channel — e.g. `warnings: [{code, category,
> severity, message, context}]` on every response whose numbers were degraded —
> and is emitting into it **mandatory** for every silent fallback, swallowed
> exception, clamped bound, and truncated or partial result?*

ADR 0012 already says "an unphysical result is a design warning, never a silent
fallback". It is honoured in two places (the six categorised polar-rejection
gates; the turbulator optimiser) and violated in ~30. The two places that *do*
warn each invented their own shape — which is the divergence a single model
prevents.

`Q-CC-10` · `Q-AC-7` · `Q-AC-8` · `Q-WD-6` · `Q-WD-8` · `Q-WD-10` · `Q-FD-4` ·
`Q-FD-6` · `Q-AF-8` · `Q-AF-9` · `Q-CP-3` · `Q-CP-9` · `Q-VI-3` · `Q-VI-5` ·
`Q-VI-7` · `Q-AA-1` · `Q-AA-3` · `Q-AV-5` · `Q-AV-7` · `Q-MS-4` · `Q-MS-5` ·
`Q-MS-8` · `Q-MS-9` · `Q-MS-10` · `Q-MS-12` · `Q-PT-1` · `Q-PT-2` · `Q-PT-8` ·
`Q-PT-12` · `Q-CO-2` · `Q-CO-3` · `Q-MC-4` · `Q-MC-5` · `Q-PC-1`

### PC-2 — Single-authority policy for duplicated producers · **18 questions**

> **Proposed decision:** *When two code paths produce the same user-facing
> number, is the rule (a) one designated producer and the other becomes a
> read-only view, (b) reconcile and warn on divergence, or (c) tolerate and
> document?*

`Q-CC-4` · `Q-CC-9` · `Q-WD-1` · `Q-AA-1` · `Q-AA-4` · `Q-MS-1` · `Q-MS-2` ·
`Q-MS-9` · `Q-MS-14` · `Q-MB-1` · `Q-MB-2` · `Q-MB-7` · `Q-MB-8` · `Q-MB-9` ·
`Q-PT-4` · `Q-PT-8` · `Q-PT-9` · `Q-VS-7`

Note the pattern's frequency: two `Settings` classes, three version strings,
three `created_by` vocabularies, two mass producers, two `cd0` producers, two
landing-distance models, two `t_static_N` sources, three
`target_static_margin` defaults, two effective-value resolvers, two aggregation
implementations, two `GRAVITY` constants, two atmosphere models, three spec-key
spellings, two control-name vocabularies. This is the system's dominant defect
shape, and ADR 0004 ("one aero truth per aircraft") is the only place it has
been decided so far.

### PC-3 — Dead-code disposition policy · **30 questions**

> **Proposed single decision (`P-DEAD-0`, no existing Q-id):**
> *For complete-but-unreachable code, is the default (a) delete and record it in
> the spec as removed, (b) wire it in this cycle, or (c) keep as a documented
> template behind a `# UNREACHABLE(gh-N)` marker plus a test asserting it stays
> unreachable?*

`Q-CC-14` · `Q-CC-16` · `Q-AC-1` · `Q-AC-9` · `Q-CT-1` · `Q-CT-3` · `Q-CT-5` ·
`Q-CG-1` · `Q-CG-4` · `Q-CP-2` · `Q-FD-8` · `Q-VI-1` · `Q-VI-2` · `Q-AV-3` ·
`Q-AV-8` · `Q-AA-2` · `Q-AA-8` · `Q-MS-13` · `Q-MB-2` · `Q-MB-3` · `Q-MB-10` ·
`Q-VS-3` · `Q-CO-1` · `Q-CO-5` · `Q-CO-6` · `Q-CO-8` · `Q-CO-10` · `Q-MC-7` ·
`Q-PT-12` · `Q-FW-8`

These are not equivalent. Three of them (`Q-AV-3` AVL replay verification,
`Q-VI-2` geometry cross-check, `Q-CG-4` background re-tessellation) are
*completed safety or confidence mechanisms* sitting unused; the catalogue
argues explicitly against shipping them inert a second time. Others
(`Q-CC-16`, `Q-CT-5`'s `scaleXyz` with a typo'd `y_sacle` parameter) have no
retention argument at all.

### PC-4 — Closed-set constraint policy · **11 questions** · gated by `Q-CC-7`

> **Root: `Q-CC-9`.** *Do closed vocabularies get a DB-level CHECK/enum, or does
> Pydantic remain the only enforcement?*

`Q-CC-9` · `Q-WD-3` · `Q-CT-5` · `Q-MS-10` · `Q-MS-13` · `Q-MB-10` · `Q-PT-5` ·
`Q-PT-13` · `Q-VS-6` · `Q-CO-5` · `Q-CO-12`

### PC-5 — Referential-integrity policy · **9 questions** · root `Q-CC-7`

> *Do soft `String` aeroplane references become real FKs?* The clone-coverage
> test can only see tables that carry a SQLAlchemy `ForeignKey` object, so this
> is not only a Postgres question — it is the only structural guard against
> silently losing data on branch.

`Q-CC-7` · `Q-AF-7` · `Q-CG-5` · `Q-CP-9` · `Q-AA-6` · `Q-MS-13` · `Q-VS-4` ·
`Q-VS-5` · `Q-CO-5`

### PC-6 — Error-envelope and status-code policy · **13 questions** · root `Q-CC-3`

`Q-CC-3` · `Q-CC-6` · `Q-AC-2` · `Q-AC-6` · `Q-FD-1` · `Q-WD-9` · `Q-AF-5` ·
`Q-MS-8` · `Q-MB-10` · `Q-PT-11` · `Q-VS-3` · `Q-MC-4` · `Q-FW-2`

### PC-7 — Process-locality and long-running-work policy · **14 questions** · root `Q-CC-8`

`Q-CC-8` · `Q-FD-5` · `Q-AF-6` · `Q-CG-2` · `Q-CG-4` · `Q-CG-5` · `Q-CP-1` ·
`Q-CO-5` · `Q-MC-3` · `Q-PC-2` · `Q-PC-3` · `Q-PC-4` · `Q-PC-5` · `Q-FW-5`

### PC-8 — UI language policy · **3 questions** · root `Q-CC-5`

`Q-CC-5` · `Q-AA-7` · `Q-MS-12` (the last only for the `warnings[]` token-vs-
sentence half — `STALL_IN_TURN` is a formatted sentence where every sibling is
a bare token).

---

## Dependency graph

`A → [B, …]` means *the answer to A changes what B's sensible answers are, or
makes B moot*.

### Wave-0 roots (product scope)

```
Q-CC-1  → [Q-CC-2, Q-MC-1, Q-MC-7, Q-CO-9, Q-PT-13, Q-CC-9, Q-PC-2, Q-PC-3]
          no identity ⇒ no quota, no per-subject audit, no bind policy
Q-CC-8  → [Q-CP-1, Q-CG-2, Q-CG-4, Q-CG-5, Q-FD-5, Q-AF-6, Q-PC-2, Q-PC-4,
           Q-PC-5, Q-MC-3, Q-CO-5, Q-FW-5]
          per-process state is either a documented constraint or eight bugs
Q-CC-7  → [Q-VS-4, Q-VS-6, Q-CP-9, Q-CC-9, Q-AA-6, Q-AF-7, Q-CG-5, Q-MB-10,
           Q-MS-13]
          Postgres target decides FK/CHECK feasibility for every soft column
Q-FW-1  → [Q-CC-1, Q-FW-2, Q-FW-3, Q-CC-11]
          the missing proxy layer is the *cause* of wildcard CORS, not a choice
```

### Wave-1 roots (cross-cutting contracts)

```
Q-CC-3  → [Q-CC-6, Q-AC-2, Q-AC-6, Q-FD-1, Q-WD-9, Q-MS-8, Q-MB-10, Q-VS-3,
           Q-PT-11, Q-MC-4, Q-FW-2]
          one envelope ⇒ every per-route status question becomes mechanical
Q-CC-10 → [Q-AA-1, Q-AA-3, Q-AA-8, Q-AA-9, Q-AF-2, Q-MS-2, Q-MS-4, Q-MS-8,
           Q-MS-9, Q-PT-8, Q-MB-7, Q-CO-11]
          a typed, versioned context removes the per-consumer default fallbacks
Q-CC-9  → [Q-WD-3, Q-CT-5, Q-MS-10, Q-MS-13, Q-MB-10, Q-PT-5, Q-CO-12]
          the created_by / role / category vocabulary decision
Q-CC-4  → [Q-PC-2, Q-PC-6, Q-PC-7, Q-MC-3, Q-CC-14]
          which Settings owns which value; the 8000-vs-8001 base_url bug
Q-CC-13 → [Q-CT-1, Q-CT-2, Q-CT-3, Q-CT-5, Q-CC-14]
          whether cad_designer/ questions are "frozen" or "gated"
Q-CC-11 → [Q-FW-2, Q-FW-3, Q-FW-9, Q-CC-12]
          generated types decide how much hand-written client contract survives
Q-CC-15 → [Q-CP-4, Q-VS-7]
          ownership is why SparPlanResult and _metrics_payload were never pinned
Q-CC-5  → [Q-AA-7]
```

### Wave-2 roots (correctness)

```
Q-MB-1  → [Q-MB-3, Q-MB-4, Q-MB-5, Q-MB-7, Q-MB-9, Q-MB-11, Q-AC-4, Q-AC-7,
           Q-AC-8, Q-PT-2]
          who owns aircraft mass decides every completeness/sync question
Q-AA-1  → [Q-AA-2, Q-AA-8, Q-MS-2, Q-MS-4, Q-PT-8, Q-CO-11]
          a corrupted cd0 makes nine consumers' answers unverifiable
Q-WD-1  → [Q-WD-3, Q-WD-4, Q-WD-11, Q-MS-5, Q-MS-12, Q-AV-6, Q-VI-1]
          control-name resolution gates every trim/authority question
Q-FD-2  → [Q-FD-3, Q-FD-4, Q-FD-7, Q-VI-3, Q-VI-6, Q-CP-9]
          the unit contract for every externally authored geometry file
Q-VS-1  → [Q-VS-2, Q-VS-5, Q-VS-6, Q-VS-8, Q-CP-6, Q-PT-7, Q-CO-1, Q-CO-12]
          immutability is the premise of the branch model and of ADR 0007
Q-MC-1  → [Q-MC-2, Q-MC-3, Q-MC-4, Q-MC-5, Q-MC-6, Q-MC-7, Q-MC-8, Q-CC-12]
          read-only vs read-write is the module's whole contract
Q-MS-1  → [Q-MS-9, Q-MS-10, Q-MS-11, Q-MS-14, Q-PT-3, Q-PT-8]
          the unit of power_to_weight decides preset backfill and sizing defaults
Q-CP-1  → [Q-CG-2, Q-CP-2, Q-CP-3, Q-CP-7, Q-FD-5]
          where CAD runs decides the concurrency and artefact-lifecycle answers
Q-CG-1  → [Q-CG-2, Q-CG-6, Q-CP-2]
          the export-format contract and the export directory model
Q-VI-1  → [Q-VI-2, Q-VI-4, Q-VI-8, Q-VI-9, Q-WD-3]
          whether imports start producing TEDs changes the import contract
Q-CO-12 → [Q-CO-1, Q-CO-3, Q-CO-4, Q-CO-5, Q-CO-6]
          a typed proposal removes five failure modes with one root cause
```

### True leaves — no question→question edge (59)

Of these, **28** are still constrained by a policy cluster (marked ▸):

`Q-CC-16`▸ · `Q-CC-17` · `Q-AC-1`▸ · `Q-AC-3` · `Q-AC-5` · `Q-AC-9`▸ ·
`Q-AC-10` · `Q-WD-2` · `Q-WD-5` · `Q-WD-6`▸ · `Q-WD-7` · `Q-WD-8`▸ ·
`Q-WD-10`▸ · `Q-FD-6`▸ · `Q-FD-8`▸ · `Q-AF-1` · `Q-AF-3` · `Q-AF-4` ·
`Q-AF-5`▸ · `Q-AF-8`▸ · `Q-AF-9`▸ · `Q-CG-3` · `Q-CT-4` · `Q-CP-5` ·
`Q-CP-8` · `Q-VI-5`▸ · `Q-VI-7`▸ · `Q-VI-10` · `Q-AA-4` · `Q-AA-5` ·
`Q-AV-1` · `Q-AV-2` · `Q-AV-3`▸ · `Q-AV-4` · `Q-AV-5`▸ · `Q-AV-7`▸ ·
`Q-AV-8`▸ · `Q-MS-3` · `Q-MS-6` · `Q-MS-7` · `Q-MB-2`▸ · `Q-MB-6` ·
`Q-MB-8`▸ · `Q-PT-1`▸ · `Q-PT-4`▸ · `Q-PT-6` · `Q-PT-9`▸ · `Q-PT-10` ·
`Q-PT-12`▸ · `Q-CO-2`▸ · `Q-CO-7` · `Q-CO-8`▸ · `Q-CO-10`▸ · `Q-CO-13` ·
`Q-PC-1`▸ · `Q-FW-4` · `Q-FW-6` · `Q-FW-7` · `Q-FW-8`▸

The **31 genuinely independent** ones (no edge, no cluster) can be answered in
any order or skipped: `Q-CC-17`, `Q-AC-3`, `Q-AC-5`, `Q-AC-10`, `Q-WD-2`,
`Q-WD-5`, `Q-WD-7`, `Q-AF-1`, `Q-AF-3`, `Q-AF-4`, `Q-CG-3`, `Q-CT-4`,
`Q-CP-5`, `Q-CP-8`, `Q-VI-10`, `Q-AA-4`, `Q-AA-5`, `Q-AV-1`, `Q-AV-2`,
`Q-AV-4`, `Q-MS-3`, `Q-MS-6`, `Q-MS-7`, `Q-MB-6`, `Q-PT-6`, `Q-PT-10`,
`Q-CO-7`, `Q-CO-13`, `Q-FW-4`, `Q-FW-6`, `Q-FW-7`.

Three of them are **pure lookups, not decisions** — `Q-AF-3` (confidence tier
boundaries), `Q-CP-4` (`SparPlanResult` field list) and `Q-CC-17` (run
`npm run deps:check`). They are re-implementation blockers regardless of their
graph position, so they are promoted into Wave 2.

---

## Interview plan (waves)

### Wave 0 — product scope (5 questions)

These reframe everything downstream. Nothing in Waves 1–4 should be answered
before these.

| Q-id | Title | Why now / what it unblocks | Downstream |
|---|---|---|---|
| `Q-CC-1` | No-auth permanent? | Gates whether ~40 destructive MCP tools may be made to work at all; gates quota, bind policy, `created_by` as an identity seam | **8** |
| `Q-CC-8` | Single-process permanent? | Converts eight per-process-state gaps into either one documented constraint or one shared work item | **12** |
| `Q-CC-7` | PostgreSQL ever? | Decides whether every soft `String` reference and closed-set column can get a real constraint | **9** |
| `Q-FW-1` | Was the server-side proxy dropped? | Root cause of the wildcard CORS in `Q-CC-1`; decides whether CORS can ever be tightened | **4** |
| `Q-CC-2` | Commit a sanitised `deploy/`? | ADR 0016's boundary is currently unreviewable and unreproducible from a clone | 0 |

### Wave 1 — cross-cutting contracts and policies (10 items)

| Item | Title | Why now / what it unblocks | Downstream |
|---|---|---|---|
| **`P-WARN-0`** *(new)* | One mandatory warning channel? | Highest-leverage single decision in the plan: resolves or constrains **34** questions across 13 modules | **34** |
| `Q-CC-10` | Assumption context as a versioned contract | The densest instance of `P-WARN-0` *and* root of the aero-correctness chain | **12** |
| `Q-CC-3` | Which HTTP error envelope | Every module's `contracts.md` error table; decides whether `parseApiError.ts` can be deleted | **11** |
| `Q-CC-9` | Closed sets / `created_by` vocabulary | The `'ai'` vs `'copilot'` split silently breaks UI filtering and copilot proposal reuse | **7** |
| **`P-DEAD-0`** *(new)* | Dead-code disposition default | **30** questions are variants of "delete, wire, or keep?"; three are completed safety mechanisms | **30** |
| `Q-CC-4` | Two `Settings`, three versions | Nobody owns config today — the 8000-vs-8001 `base_url` bug is a symptom | **5** |
| `Q-CC-13` | Narrow the `cad_designer/**` gate exclusion | Decides whether the four `cad-designer-topology` questions are "frozen" or "gated" | **5** |
| `Q-CC-11` | Generated TypeScript client | Decides how much hand-written client contract the spec must prescribe | **4** |
| `Q-CC-15` | Ownerless schema files | Directly causes `Q-CP-4` and `Q-VS-7`; five files are the only production code with no home unit | **2** |
| `Q-CC-5` | German user-facing strings | Cheap, and the `PolarRejection.hint` half is user-facing by design (gh-956) | **1** |

### Wave 2 — correctness roots (15 questions)

Eleven roots plus four pure re-implementation blockers that carry no
dependency edge but cannot be guessed.

| Q-id | Title | Why now / what it unblocks | Downstream |
|---|---|---|---|
| `Q-MB-1` | Two mass producers, one column | Mass drives retrim, `V_stall`, matching chart, solution space, endurance | **10** |
| `Q-AA-1` | `_auto_populate_cd0` writes total CD | Corrupts the single source of truth for nine consumers; ADR 0004 violation | **6** |
| `Q-WD-1` | gh-772 mixing-name ownership (#955) | Every V-tail / elevon aircraft reports wrong control authority | **7** |
| `Q-FD-2` | STEP source unit | The most reachable silent-1000× path in the system; two upload paths must agree | **6** |
| `Q-VS-1` | Snapshot immutability guard coverage | The premise ADRs 0006 and 0007 both rest on | **8** |
| `Q-MC-1` | MCP writes discarded | Fix vs formalise changes the module's whole contract; interacts with `Q-CC-1` | **8** |
| `Q-MS-1` | `power_to_weight` unit | Seven of nine shipped presets seed a physically absurd sizing input | **6** |
| `Q-CP-1` | Plan execution vs the CAD process pool | ADR 0005 and the code contradict each other; a re-implementer must not pick silently | **5** |
| `Q-CG-1` | 3MF/AMF export broken, test pins the bug | Two of five advertised export formats do not work; the test protects the defect | **3** |
| `Q-VI-1` | Wire the `SS_CONTROL` post-pass? | Turning it on starts creating TEDs nothing downstream has seen | **5** |
| `Q-CO-12` | Typed proposal branch | Five copilot failure modes with one root cause; also settles `Q-CC-9` for branches | **5** |
| `Q-WD-8` | Spar-sizing factor ownership | Numerically load-bearing: a double `g_limit`/`j` would oversize every spar by 4.5× | 0 (P-WARN) |
| `Q-AF-3` | Confidence tier boundaries | **Lookup.** Ranking order is unreproducible without it | 0 |
| `Q-CP-4` | `SparPlanResult` field names | **Lookup.** The module's one hard re-implementation blocker | 0 |
| `Q-CG-3` | Degenerate bounding box on tessellation | Needs an empirical browser check to know if it is cosmetic or a visible bug | 0 |

### Wave 3 — module decisions (135 questions)

Only the questions **not** already implied by Waves 0–2. Grouped by module;
answer a module in one sitting. "Implied by" names the upstream decision that
usually settles it.

#### cross-cutting (2)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-CC-6` | `/api/v2` prefix on the importer | Breaking either way; the spec must say which direction was intended | `Q-CC-3` | 0 |
| `Q-CC-12` | Golden-file test for MCP tool schemas | Only proposed mechanism for detecting MCP contract drift | `Q-MC-1`, `Q-CC-11` | 0 |

#### aeroplane-core (8)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-AC-1` | Shadowed `aeroplane.py` router | Only file in the module marked dead | `P-DEAD-0` | 0 |
| `Q-AC-2` | `aeroplanes.name` unique? | Settles whether the German 409 is reachable at all | `Q-CC-3`, `Q-CC-5` | 0 |
| `Q-AC-3` | Read-time cycle defence in the tree | `_roll_up_weights` recurses infinitely on a cycle | — | 0 |
| `Q-AC-4` | Negative `scale_factor` / `quantity` | They subtract from aircraft total mass | `Q-MB-1` | 0 |
| `Q-AC-5` | Empty `AirplaneConfiguration` export | `self.wings[0]` raises `IndexError` at construction | — | 0 |
| `Q-AC-6` | Conversion failures classified 500 | User-fixable data problems look like server faults | `Q-CC-3` | 0 |
| `Q-AC-7` | Persistently failing mass sync | Bare `except` vs the narrower one in `weight_items_service` | `P-WARN-0`, `Q-MB-1` | 0 |
| `Q-AC-8` | Completeness indicator on `/weight` | A total cannot be told from a partial total | `P-WARN-0`, `Q-MB-1` | 0 |

#### wing-design (9)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-WD-2` | `units` block vs the mm spar exception | The one place the system's self-description contradicts its storage | — | 0 |
| `Q-WD-3` | TED representation bundle (4 items) | `servo` union, NULL servo dims, default divergence, `role` constraint | `Q-WD-1`, `Q-CC-9`, `Q-VI-1` | 0 |
| `Q-WD-4` | `role is None` skips mix validation | BR-12's gate is bypassable in two writes | `Q-WD-1` | 0 |
| `Q-WD-5` | BR-6 segment root chord enforcement | The only business rule with no enforcement at any layer | — | 0 |
| `Q-WD-6` | Degraded spar-vector recompute | Client cannot tell recomputed from stale | `P-WARN-0` | 0 |
| `Q-WD-7` | Historical data audits (3 items) | Only answerable from the live DB; decides whether migrations are needed | — | 0 |
| `Q-WD-9` | Duplicate control name status code | 422 vs 500; same for `required_section_modulus`'s bare `ValueError` | `Q-CC-3` | 0 |
| `Q-WD-10` | Turbulator optimiser semantics (6 items) | `symmetry_factor` on a fin doubles ΔCD0 invisibly | `P-WARN-0` | 0 |
| `Q-WD-11` | Stored `deflection_deg` into every trim | Affects every trim on an aircraft with a pre-set surface | `Q-WD-1` | 0 |

#### fuselage-design (7)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-FD-1` | 409 (fuselage) vs 422 (wing) | Two adjacent CRUD families, one condition, two codes | `Q-CC-3` | 0 |
| `Q-FD-3` | Assert `a`/`b` ↔ `width`/`height` | Swapping rotates the body 90°; no error either way | `Q-FD-2` | 0 |
| `Q-FD-4` | `volume_ratio` / `area_ratio` threshold | Nothing flags a bad reconstruction; `n` fitted at the bound silently | `P-WARN-0`, `Q-FD-2` | 0 |
| `Q-FD-5` | 5–30 s slice as an async job | Every other long CAD op is a task with a status endpoint | `Q-CC-8`, `Q-CP-1` | 0 |
| `Q-FD-6` | Slicing details bundle (4 items) | `slice_axis="auto"`, ≥2 slices, max xsecs, delete-sync failure | `P-WARN-0` | 0 |
| `Q-FD-7` | `update_fuselage` destroys import artefacts | A UI edit can silently orphan an imported STEP | `Q-FD-2` | 0 |
| `Q-FD-8` | `from_step_file` dead; parametric fuselage planned? | The load-bearing justification for the dual representation | `P-DEAD-0` | 0 |

#### airfoil-catalog (5)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-AF-1` | Selig-only assumption / format sniffing | A mis-parsed airfoil propagates into polars, scoring and CAD | — | 0 |
| `Q-AF-2` | Staleness marker for the low-Re backfill | Pre-gh-834/gh-825 rows are silently wrong and undetectable | `Q-CC-10` | 0 |
| `Q-AF-5` | Polar/scoring edge cases (6 items) | Null-metric policy, ASB-absent shape, duplicate upload | `Q-CC-3`, `P-WARN-0` | 0 |
| `Q-AF-6` | Where the batch backfill runs from | The module's most expensive operation has no operator surface | `Q-CC-8` | 0 |
| `Q-AF-8` | `high_re` degraded-confidence signal | The one place the module asserts more than the data supports | `P-WARN-0` | 0 |

#### cad-generation (3)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-CG-2` | Per-task export directory | Data loss under concurrency, today; plans already solved this | `Q-CC-8`, `Q-CP-1`, `Q-CG-1` | 0 |
| `Q-CG-4` | GH #202 background re-tessellation | Fully implemented, nothing calls it | `P-DEAD-0`, `Q-CC-8` | 0 |
| `Q-CG-5` | Fuselage tessellation + cache unique constraint | Modelled-but-unreachable component type; duplicate rows possible | `Q-CC-7`, `Q-CC-8` | 0 |

#### cad-designer-topology (4)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-CT-1` | Three undecodable plan JSONs | Ownership unresolved between two modules | `Q-CC-13`, `P-DEAD-0` | 0 |
| `Q-CT-2` | `gp_D*` singleton mutation carve-out | Reachable from a real build; strongest ADR 0002 exception candidate after `Turbulator` | `Q-CC-13` | 0 |
| `Q-CT-3` | `_main_wing_index = 0` dead path | A latent 8× coefficient error waiting for its first caller | `Q-CC-13`, `P-DEAD-0` | 0 |
| `Q-CT-5` | Dead topology bundle + hinge types | `round_inside`/`round_outside` are selectable and cannot build — user-facing | `Q-CC-13`, `Q-CC-9`, `P-DEAD-0` | 0 |

#### construction-plans (7)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-CP-2` | Where servo/engine/component info comes from | Three of 29 Creators unreachable through REST | `Q-CP-1`, `Q-CG-1` | 0 |
| `Q-CP-3` | Report a partially converted aircraft | A builder can get a manufacturable file for an incomplete aircraft | `P-WARN-0`, `Q-CP-1` | 0 |
| `Q-CP-5` | Persist the spar plan; stock tube sizes | Structural provenance for a safety-relevant output | — | 0 |
| `Q-CP-6` | What counts as a destructive spar edit | The hard-coded list misses future edit types; `tol_mm = 5.0` is scale-blind | `Q-VS-1` | 0 |
| `Q-CP-7` | `_migrate_tree_json` as a one-off migration | Every read is currently a write | `Q-CP-1` | 0 |
| `Q-CP-8` | Template → plan provenance | Would mirror the aeroplane versioning model | `Q-VS-1` | 0 |
| `Q-CP-9` | Construction-part storage bundle (6 items) | Files outside `ARTIFACTS_BASE_DIR` miss the traversal guard | `Q-CC-7`, `Q-FD-2`, `P-WARN-0` | 0 |

#### openvsp-import (8)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-VI-2` | `validate_geometry`: wire or delete | Complete and tested, referenced only by its own test | `P-DEAD-0`, `Q-VI-1` | 0 |
| `Q-VI-3` | Feet-unit model without a fuselage | The one remaining silent-3.28× path after gh-808 | `Q-FD-2`, `P-WARN-0` | 0 |
| `Q-VI-4` | Bug #814: which body does CAD download serve | The solid is input to bay cuts, servo mounts, tube bores | `Q-VI-1` | 0 |
| `Q-VI-5` | Disclose the loose-tolerance sewing retry | Likeliest producer of the malformed solid in #814 | `P-WARN-0` | 0 |
| `Q-VI-6` | Assert export-unit ↔ unit-detection | BR-76 is valid only because BR-OV13 forces `LEN_M` | `Q-FD-2` | 0 |
| `Q-VI-7` | Report handler registration failures | Broken handler is indistinguishable from unsupported geom type | `P-WARN-0` | 0 |
| `Q-VI-8` | Camber loss (#791) and VLM cost (#792) | #791 makes every imported lift curve wrong at α=0 | `Q-VI-1` | 0 |
| `Q-VI-9` | Handler details bundle (3 items) | The CUSTOM handler is a genuine re-implementation blocker | `Q-VI-1` | 0 |

#### aero-analysis (7)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-AA-2` | `min`/`max_static_margin` as real assumptions | Effectively hard-coded while appearing configurable | `Q-AA-1`, `P-DEAD-0` | 0 |
| `Q-AA-3` | Missing `mass` → 1.0 kg speed polar | ADR 0012's own rule argues against the current behaviour | `P-WARN-0`, `Q-CC-10` | 0 |
| `Q-AA-4` | Duplicated geometry listeners | Every geometry write fires the bus twice | — | 0 |
| `Q-AA-5` | `mark_ops_dirty` into the handlers | Fan-out is correct only by convention; the log line is actively misleading | — | 0 |
| `Q-AA-6` | OP lifecycle bundle (4 items) | Warnings never cleared; `DIRTY` absorbing; alphabetical status ordering | `Q-CC-7` | 0 |
| `Q-AA-7` | German polar-rejection hints | gh-956's whole point is surfacing them to the user | `Q-CC-5` | 0 |
| `Q-AA-9` | `recompute_assumptions` 750-line form | Guides whether the spec prescribes the same shape | `Q-CC-10` | 0 |

#### avl-integration (7)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-AV-1` | Real AVL convergence flag | The module's only `Must (open)`; a partial run reports success | — | 0 |
| `Q-AV-2` | Wing-only AVL model | The two solvers disagree by construction on `Cnb` | — | 0 |
| `Q-AV-3` | Replay-artefact wiring lost or staged | A complete safety mechanism sitting unused | `P-DEAD-0` | 0 |
| `Q-AV-4` | Clear `is_dirty` on regenerate | The user-editable escape hatch silently stops taking effect | — | 0 |
| `Q-AV-5` | CDCL count mismatch as a hard error | Later sections silently get zero viscous drag | `P-WARN-0` | 0 |
| `Q-AV-6` | `.avl` edits ignored on single-wing runs | Applied on some routes, not others, with no indication | `Q-WD-1` | 0 |
| `Q-AV-7` | Missing AVL binary as a capability error | AVL is the one heavy dependency with no probe (ADR 0017) | `P-WARN-0` | 0 |

#### mission-and-sizing (13)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-MS-2` | Which landing-distance model; two `t_static_N` | Two user-facing numbers with two producers each | `Q-CC-10`, `Q-AA-1` | 0 |
| `Q-MS-3` | `LANDING_SURFACE_MU` calibration | Largest lever on a user-facing "field sufficient" verdict | — | 0 |
| `Q-MS-4` | Is the `e = 0.8` design warning implemented | The exact fallback ADR 0012 and gh-956 were written to eliminate | `P-WARN-0`, `Q-AA-1` | 0 |
| `Q-MS-5` | `_grid_search_trim` deflection grid | Mislabels an authority limit as a solver failure | `Q-WD-1`, `P-WARN-0` | 0 |
| `Q-MS-6` | Store trimmed CL for V-n markers | Turn points plot on the 1-g line, where they are not | — | 0 |
| `Q-MS-7` | Marker → KPI mapping | A whole confidence tier is unreachable | — | 0 |
| `Q-MS-8` | Flight-envelope bundle (5 items) | Two `V_max` fallbacks; fixed ρ; silent gust envelope; 500-vs-422 | `Q-CC-3`, `Q-CC-10`, `P-WARN-0` | 0 |
| `Q-MS-9` | Design-assumption semantics (6 items) | Two effective-value resolvers; `0.0` as a "not set" sentinel | `Q-CC-10`, `Q-MS-1` | 0 |
| `Q-MS-10` | Should a mission-preset change fan out | The largest assumption edit a user can make propagates to nothing | `Q-MS-1`, `Q-CC-9` | 0 |
| `Q-MS-11` | `wing_loading` axis unit consistency | One of the two bands is in the wrong unit; every KPI score rides on it | `Q-MS-1` | 0 |
| `Q-MS-12` | OP sweep semantics (6 items) | Trim weights (50, 3, 15, 2, 2, 0.001) unreproducible without provenance | `Q-WD-1`, `P-WARN-0` | 0 |
| `Q-MS-13` | Loading-scenario/profile bundle (4 items) | `is_default` unconstrained; `ga_runway` unselectable | `Q-CC-7`, `Q-CC-9` | 0 |
| `Q-MS-14` | Three `target_static_margin` defaults | Static margin is the central design target of ADR 0011 | `Q-MS-1` | 0 |

#### mass-and-balance (7)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-MB-2` | Home of the top-down CG rule | ADR 0011's central rule is implemented three times | `Q-MB-1`, `P-DEAD-0` | 0 |
| `Q-MB-3` | Lateral/vertical CG scope | Two computed and published fields nothing reads | `Q-MB-1`, `P-DEAD-0` | 0 |
| `Q-MB-4` | CG comparison including the tree | ADR 0011's feedback signal is unavailable for tree-built aircraft | `Q-MB-1` | 0 |
| `Q-MB-5` | `PUT` on a weight item should be `PATCH` | Silent data loss: an omitted `x_m` resets a position to 0.0 | `Q-MB-1` | 0 |
| `Q-MB-7` | `/total_mass_kg` vs the `mass` assumption | Two "the aircraft's mass" endpoints that can disagree | `Q-MB-1`, `Q-CC-10` | 0 |
| `Q-MB-9` | One shared aggregation helper; one empty convention | A divergence would be invisible until the numbers drifted | `Q-MB-1` | 0 |
| `Q-MB-10` | DB constraint on `weight_items.category`; dead 409 | Three contract rows | `Q-CC-7`, `Q-CC-9`, `Q-CC-3` | 0 |

#### powertrain (13)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-PT-1` | ESC selection criterion | A user-facing recommendation that is non-deterministic | `P-WARN-0` | 0 |
| `Q-PT-2` | Propeller mass in the sizing total | Sizing total feeds wing loading and stall speed | `Q-MB-1`, `P-WARN-0` | 0 |
| `Q-PT-3` | Solution-space KV from the APC database | A documented placeholder whose blocker (#615) has shipped | `Q-MS-1` | 0 |
| `Q-PT-4` | Canonical spec-key spelling | A battery imported under one spelling is invisible to the other consumer | — | 0 |
| `Q-PT-5` | `component_types` schema: contract or minimum | Seeded components the API then rejects | `Q-CC-9` | 0 |
| `Q-PT-6` | Winding-resistance source for QPROP | Every production performance curve comes from the approximation | — | 0 |
| `Q-PT-7` | Version the COTS library | Editing `mass_g` retroactively changes every historical snapshot | `Q-VS-1` | 0 |
| `Q-PT-8` | Unify the two sizing paths' RC defaults | Two answers to one sizing question; staleness undetectable | `Q-CC-10`, `Q-AA-1`, `Q-MS-1` | 0 |
| `Q-PT-9` | ISA atmosphere in the powertrain | Two atmosphere models in one aircraft's calculation | — | 0 |
| `Q-PT-10` | Windmilling drag scope | Glide performance on a powered aircraft is optimistic | — | 0 |
| `Q-PT-11` | Performance endpoint's unused aeroplane | 404 vs 422 on a wrong component type; `HTTPException` in helpers | `Q-CC-3` | 0 |
| `Q-PT-12` | Propeller-polar integrity (5 items) | 454 propellers with no import audit trail | `P-WARN-0`, `P-DEAD-0` | 0 |
| `Q-PT-13` | COTS lifecycle (5 items) | **Includes the only unverified security control in the corpus** (upload path containment) | `Q-CC-1`, `Q-CC-9` | 0 |

#### versioning (7)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-VS-2` | Snapshot growth bound; `preview_png` | Compounded by the copilot cloning a subgraph per proposal | `Q-VS-1` | 0 |
| `Q-VS-3` | Five dead `design-versions` routes | Five published OpenAPI routes that can never succeed | `Q-CC-3`, `P-DEAD-0` | 0 |
| `Q-VS-4` | String references → real FKs | The clone-coverage test's blind spot, one level down (columns, not tables) | `Q-CC-7`, `Q-VS-1` | 0 |
| `Q-VS-5` | Copy `construction_parts` on clone | A branch is not a complete copy of the design | `Q-VS-1`, `Q-CC-7` | 0 |
| `Q-VS-6` | Branch/lineage bundle (6 items) | `discard_branch` truncates surviving nodes' lineage | `Q-VS-1`, `Q-CC-7` | 0 |
| `Q-VS-7` | Promote `_metrics_payload` | Four call sites depend on a private function's shape | `Q-CC-15` | 0 |
| `Q-VS-8` | Expose UUIDs on versioning routes | The one place the public API is inconsistent about identity | `Q-VS-1` | 0 |

#### ai-copilot (10)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-CO-1` | Wire or remove the AI audit trail | ADR 0007's accountability story is entirely unimplemented | `Q-CO-12`, `Q-VS-1`, `P-DEAD-0` | 0 |
| `Q-CO-2` | Malformed tool arguments become `{}` | A write tool executed on garbage input | `P-WARN-0` | 0 |
| `Q-CO-3` | Retarget failure swallowed | The model describes changes it is not looking at | `Q-CO-12`, `P-WARN-0` | 0 |
| `Q-CO-4` | Persist the turn from a background task | A proposal branch can exist with no message explaining it | `Q-CO-12` | 0 |
| `Q-CO-5` | Conversation branching; `sort_index` races | Three pieces of dead or unsafe schema | `Q-CO-12`, `Q-CC-8`, `Q-CC-7` | 0 |
| `Q-CO-7` | `RemoveXsec` sums sweeps vs "weighted avg" | Every AI station removal changes the planform | — | 0 |
| `Q-CO-9` | Per-user / per-aeroplane quota | Unbounded spend on an unauthenticated endpoint | `Q-CC-1` | 0 |
| `Q-CO-10` | Agentic expert panel still planned | The copilot's domain knowledge lives in a prompt literal | `P-DEAD-0` | 0 |
| `Q-CO-11` | System-prompt policy → server-side validation | Prompt text is the only guard on the copilot's numeric claims | `Q-CC-10`, `Q-AA-1` | 0 |
| `Q-CO-13` | Polar sweep vs the aircraft's cruise speed | The model reasons about the wrong flight condition | — | 0 |

#### mcp-server (6)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-MC-2` | Is the 76-tool surface deliberately frozen | Deliberate subset vs maintenance gap | `Q-MC-1` | 0 |
| `Q-MC-3` | Assets out of the process | Three defects, one root cause; the 8000-vs-8001 `base_url` | `Q-MC-1`, `Q-CC-8`, `Q-CC-4` | 0 |
| `Q-MC-4` | Translate exceptions + capability guards | An agent cannot tell a missing aeroplane from a missing dependency | `Q-MC-1`, `Q-CC-3`, `P-WARN-0` | 0 |
| `Q-MC-5` | Explicit shape for `None`-returning tools | The agent's only feedback signal on a destructive call | `Q-MC-1`, `P-WARN-0` | 0 |
| `Q-MC-6` | Is `request=None` safe everywhere | A latent break with no detector | `Q-MC-1` | 0 |
| `Q-MC-7` | Standalone `run_mcp_server` still used | Hard-codes `0.0.0.0:8001` on an unauthenticated surface | `Q-CC-1`, `Q-MC-1`, `P-DEAD-0` | 0 |

#### platform-core (6)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-PC-1` | `NonFiniteSafeJSONResponse` app-wide | ADR 0012's numeric-safety guarantee covers ~7 % of the API | `P-WARN-0` | 0 |
| `Q-PC-2` | A `/ready` endpoint + startup summary | After a migration-bearing merge nothing reveals the schema state | `Q-CC-1`, `Q-CC-4`, `Q-CC-8` | 0 |
| `Q-PC-3` | Structured logging | The signal that would have surfaced the MCP commit defect | `Q-CC-1`, `Q-CC-8` | 0 |
| `Q-PC-4` | `schedule_retrim` short-circuit asymmetry | Two opposite behaviours for one scheduling problem | `Q-CC-8` | 0 |
| `Q-PC-5` | Move the airfoil backfill out of `scripts/` | Application code depending on `scripts/` inverts the dependency | `Q-CC-8`, `Q-AF-6` | 0 |
| `Q-PC-6` | Reject a relative `ARTIFACTS_BASE_DIR` | Same class of bug the `AIRFOILS_DIR` comment documents | `Q-CC-4` | 0 |

#### frontend-workbench (6)

| Q-id | Short | Why now | Implied by | Downstream |
|---|---|---|---|---|
| `Q-FW-2` | One HTTP client for the hooks | Error handling is non-uniform across 48 hooks | `Q-CC-3`, `Q-CC-11`, `Q-FW-1` | 0 |
| `Q-FW-3` | Global `SWRConfig` + shared key module | Expensive solver endpoints revalidate on window focus | `Q-CC-11`, `Q-FW-1` | 0 |
| `Q-FW-4` | Component size budget; design-system layer | Seven files >1 000 lines — where a re-implementation spends most effort | — | 0 |
| `Q-FW-5` | Bound the tessellation cache | Unbounded `Map`; WebGL contexts leak to a blank canvas | `Q-CC-8` | 0 |
| `Q-FW-6` | Plan for moving off the Next.js canary | The spec documents canary behaviour as if it were the contract | — | 0 |
| `Q-FW-7` | Error boundary, stale-id reset, `beforeunload` | Four independent ways to lose the user's session | — | 0 |

### Wave 4 — cosmetic and housekeeping bundles (22 questions)

Answer these last, or in a single sweep. None blocks a re-implementation.

| Bundle | Q-ids | One-line framing |
|---|---|---|
| **Delivery hygiene** | `Q-CC-14`, `Q-CC-16`, `Q-CC-17` | Docker kernel pin, `azure-pipelines.yml`, committed `db/test.db`, the `test/` root; two unimported files; run `npm run deps:check` and paste the output |
| **Confirmations (🟡 → 🟢)** | `Q-AC-9`, `Q-AC-10`, `Q-AF-4`, `Q-AF-7`, `Q-CT-4`, `Q-MB-6`, `Q-PC-7` | Each converts one acceptance criterion; `Q-AF-4` (route declaration order) is worth a pinning test — same class as gh-914 |
| **Disclosure polish** | `Q-AF-9`, `Q-FW-9` | Echo the NeuralFoil model size; label the two copilot write tools |
| **Scope boundaries** | `Q-AV-2`, `Q-AV-8`, `Q-VI-10` | Confirm the wing-only AVL model, the dropped `.mass`/`.run` input, and epic #638's B5/B6 deferral |
| **Constant/dead-field cleanups** | `Q-AA-8`, `Q-MB-8`, `Q-MB-11`, `Q-CG-6`, `Q-CO-6`, `Q-CO-8` | `GRAVITY`/`RHO` centralisation, `print_resolution_mm` ownership, `_template_runs` leakage, `diff_vs_live` naming, mid-wing `AddXsec` |
| **Process** | `Q-MC-8`, `Q-FW-8` | Tool-description review process; six small frontend hygiene items |

---

## Per-question briefing notes

Read these aloud. Each is self-contained — no need to open `questions.md`.

---

### Wave 0

#### `Q-CC-1` — Is "no application authentication" a permanent product position?

**What the code does today.** `app/core/security.py` is a 4-line `verify_token`
comparing against the literal `"valid_token"`, with zero callers. REST, `/docs`,
`/redoc`, `/static`, `/assets` and `/mcp` are all open. ADR 0016 records that the
deployment tunnel (ngrok → oauth2-proxy → Caddy) is the trust boundary, but
nothing in the app enforces that the tunnel is present: no trusted-proxy check,
no forwarded-identity header, no bind-address restriction, and
`run_mcp_server()` hard-codes `0.0.0.0:8001` ignoring `UVICORN_HOST`.

**Why it's ambiguous.** The spec must say either "deliberately unauthenticated"
or "unfinished". It also gates `Q-MC-1`: fixing the MCP commit bug makes ~40
destructive tools genuinely reachable on an open port.

**Candidates.**
- **(a) Permanent, tunnel-only, plus an app-side bind guard** — default to
  loopback, require an explicit `ALLOW_PUBLIC_BIND` opt-in. Spec says
  "unauthenticated by design"; the MCP write fix becomes safe behind the proxy.
- **(b) Permanent, no app-side guard** — status quo. Every exposure question
  (`Q-CC-2`, `Q-MC-7`, `Q-CO-9`, `Q-MC-3`, `Q-PT-13`) answers "out of scope".
- **(c) Auth deferred; trust a forwarded-identity header from the proxy** — gives
  `created_by` a real subject (`Q-CC-9`) and makes a per-user quota possible
  (`Q-CO-9`).
- **(d) Full application auth** — supersedes ADR 0016 entirely.

**Recommendation.** (a) is the only evidence-backed *adjustment*: ADR 0016 is
recent and explicit, and the bind guard costs nothing while closing the gap
between what the ADR claims and what the process does. Whether to add identity
(c) is a genuine product call with no technical default.

---

#### `Q-CC-8` — Is single-process operation a permanent constraint?

**What the code does today.** The `JobTracker`, the CAD task registry, the MCP
`ASSET_REGISTRY` and the frontend tessellation cache are all per-process with no
persistence. A restart loses every pending retrim/recompute; a task started
before a reload becomes unqueryable (404) though its worker may still run; an
`img://…` URI minted by one worker is a 404 in another; a cross-thread schedule
is dropped silently after a 2 s timeout.

**Why it's ambiguous.** It decides whether ~8 separate gaps are "won't fix,
documented" or one shared work item — and whether the concurrency defects
(`Q-CG-2`, `Q-CG-5`, `Q-CO-5`) are real or theoretical.

**Candidates.**
- **(a) Single worker permanent, asserted at startup** (refuse to boot with
  `--workers > 1`). All per-process state becomes legitimate and documented.
- **(b) Single worker for now, no assertion** — status quo; silent breakage the
  day someone sets `--workers 2`.
- **(c) Multi-worker target** — job rows in the DB, assets in the DB or object
  storage, a real queue. Large.

**Recommendation.** (a). The codebase already assumes it everywhere, and ADR
0005's process pool is *intra*-process, so nothing conflicts. An explicit
startup assertion converts eight latent bugs into one documented constraint at
near-zero cost. **Important caveat:** `Q-CG-2` survives (a) — the export race is
between the four workers of the CAD pool *inside* one process, not between
uvicorn workers.

---

#### `Q-CC-7` — Will PostgreSQL ever actually be used?

**What the code does today.** `construction_plans.aeroplane_id` is a `String` FK
onto an `Integer` PK — SQLite tolerates it, PostgreSQL would reject the
constraint outright. `component_tree` and `construction_parts` reference the
aeroplane by an unconstrained `String` UUID with no FK at all, so deleting an
aeroplane orphans tree nodes, parts and their files. `.env.example` mentions
PostgreSQL.

**Why it's ambiguous.** If Postgres is real, three tables need a migration; if
not, the `.env.example` mention should go. It also decides `Q-VS-4`: the
clone-coverage test discovers related tables by introspecting SQLAlchemy
`ForeignKey` objects, so soft-reference tables are invisible to it.

**Candidates.**
- **(a) SQLite only, forever** — delete the Postgres mention; soft refs stay;
  clone coverage stays hand-registered; document the orphan behaviour.
- **(b) SQLite now, Postgres later; migrate the three tables to real FKs now** —
  cheap while single-user, and it closes the clone-test blind spot for free.
- **(c) Postgres soon** — additionally revisit WAL/threading assumptions and the
  per-process job state (`Q-CC-8`).

**Recommendation.** (b). The FK migration pays for itself through `Q-VS-4`
regardless of whether Postgres ever arrives: the clone-coverage test is the only
structural guard against silently losing a table's data on every branch, and it
is blind to exactly these three tables today.

---

#### `Q-FW-1` — Was the server-side proxy layer dropped deliberately?

**What the code does today.** `frontend/CLAUDE.md:12-13` states that all API
calls go through server-side route handlers or server actions "to avoid CORS".
There is no `app/**/route.ts`, nothing declares `"use server"`, and no
server-side fetching exists — every call is a direct browser `fetch` to
`NEXT_PUBLIC_API_URL`. The backend's `allow_origins=["*"]` is the consequence,
not an independent choice; ADR 0016 says so explicitly, and the code carries the
inline admission *"copied from other python backends to resolve the cors origin
problem"*.

**Why it's ambiguous.** The documentation and the architecture disagree, and one
of them is the spec. It is the root cause of the wildcard CORS in `Q-CC-1` and
shapes `Q-FW-2` / `Q-FW-3` / `Q-CC-11`.

**Candidates.**
- **(a) The documentation is wrong; SPA-direct is the architecture** — correct
  `frontend/CLAUDE.md`, keep `*` CORS, record it as a consequence of ADR 0016.
- **(b) The proxy was intended and dropped** — reinstate route handlers; CORS can
  then be locked to the origin, and the frontend gains the one place a forwarded
  identity could be attached (`Q-CC-1c`).
- **(c) Proxy for writes only** — hybrid; adds a second call convention.

**Recommendation.** No evidence-backed default — this is an architecture call.
But note that (b) is the only option under which CORS can ever be tightened, and
ADR 0016 already frames the missing proxy as the *cause* rather than the choice,
which is an argument that it was never a decision anyone made.

---

#### `Q-CC-2` — Should a sanitised copy of `deploy/` be committed?

**What the code does today.** `deploy/` is gitignored. The ngrok + oauth2-proxy +
Caddy chain that ADR 0016 designates as the system's *only* access control is
therefore not reproducible from a clone and not reviewable in a PR.

**Why it's ambiguous.** It determines whether the deployment topology belongs in
the spec at all or stays an operational secret.

**Candidates.**
- **(a) Commit a secret-free scaffold** — ngrok config template, oauth2-proxy
  config with a placeholder client id, Caddyfile. The boundary becomes reviewable
  and `permissions.md` can describe it normatively.
- **(b) Keep it out; describe the topology in prose in `permissions.md` only** —
  the spec records an unverifiable claim.
- **(c) Private submodule** — reviewable by the maintainer, not by a
  re-implementer.

**Recommendation.** (a), evidence-backed. ADR 0016 argues that the proxy chain
*is* the security control; an unreviewable, unreproducible security control is
the largest hole in that argument. Nothing in `deploy/` needs to stay secret
except the OAuth client secret and the ngrok token, both of which are env vars.

---

### Wave 1

#### `P-WARN-0` *(proposed)* — One mandatory structured warning channel?

**What the code does today.** ADR 0012 states: "when a computation cannot produce
a physically meaningful number, surface it — categorised, attributed and visible
— instead of substituting a default." Two places honour it: the parabolic polar
fit's six categorised rejection gates (`PolarRejection{category, hint}`), and the
turbulator optimiser. Roughly thirty places violate it: the ~40-key computation
context's per-consumer RC defaults (`cd0 0.03`, `e 0.8`, `AR 8.0`, `S 0.5`,
`mass 1.0`), `_build_speed_polar`'s 1.0 kg, `DEFAULT_E_OSWALD = 0.8`, the
sewing-tolerance retry, `inject_cdcl`'s truncating loop, per-wing conversion
drops, swallowed `ImportError`/`FileNotFoundError`, `except Exception: pass` in
the copilot's retarget. There is no shared envelope: `PolarRejection` has one
shape, operating points carry a bare-token `warnings[]` (except `STALL_IN_TURN`,
a formatted sentence), most responses carry nothing.

**Why it's ambiguous.** Nobody has ever asked the policy question — only its 34
instances. Answered one at a time, the corpus stays inconsistent even if every
individual answer is "yes, warn".

**Candidates.**
- **(a) One `warnings: [{code, category, severity, message, context}]` array,
  one shared `DesignWarning` Pydantic model, mandatory on any response whose
  numbers were degraded; ADR 0012 amended to name the channel.** Resolves 34
  questions with one rule. Migration is broad but mechanical, and the frontend
  gets one renderer instead of eight.
- **(b) Warnings mandatory, shapes per module.** Fixes the semantics, not the
  client's problem.
- **(c) Keep case-by-case.** All 34 remain separate decisions, and the next
  fallback added will be silent again.

**Recommendation.** (a). Evidence: ADR 0012 already exists and is violated mostly
because there is nothing to emit *into*; and the two subsystems that did warn
each invented their own shape, which is precisely the divergence a single model
prevents.

---

#### `Q-CC-10` — Should `assumption_computation_context` become a versioned, validated contract?

**What the code does today.** A schemaless JSON column. ~40 keys produced once at
the cruise point by `assumption_compute_service._cache_context()` and read by
nine consumers: speed polar, V-n envelope, matching chart, mission KPIs,
endurance, spar sizing, powertrain solution space, and two copilot tools. Every
consumer falls back to an RC-typical default on a missing key — `cd0 0.03`,
`e 0.8`, `AR 8.0`, `S 0.5 m²`, `mass 1.0 kg` — with only a log warning.

**Why it's ambiguous.** A key rename degrades silently: the answer stays
structurally valid and physically meaningless. Is the looseness deliberate
(the key set is still growing) or accidental?

**Candidates.**
- **(a) Pydantic model + `context_version` key + producer/consumer contract
  test; a missing key becomes a warning, never a default** (ties into
  `P-WARN-0`). Highest-leverage structural fix; requires a migration and touching
  nine consumers.
- **(b) `context_version` + contract test only, keep the dict.** Catches renames,
  preserves flexibility, leaves the fallbacks in place.
- **(c) Leave as-is; document the key set in the spec.**

**Recommendation.** At least (b), and (a) if the key set has stabilised. Evidence
for acting: the corpus already contains three live consequences of the looseness
— `Q-AA-1` (a second writer corrupting `cd0`), `Q-PT-8` (a *stale* context
indistinguishable from a fresh one, because fallback warnings fire only on
*missing* values), and `Q-MS-8` (`assumptions_snapshot` records `{mass, cl_max,
g_limit}` while `cl_alpha_per_rad`, `v_md_mps` and `v_min_sink_mps` also shape
the output).

---

#### `Q-CC-3` — Which HTTP error envelope is the contract?

**What the code does today.** Two shapes coexist. The three global handlers in
`app/main.py` emit `{"error": {code, message, details}}`. Per-module
`_raise_http` / `_call` helpers emit FastAPI's `{"detail": …}` —
`mission-and-sizing` alone ships five distinct local mappers across nine
endpoint modules, and `mass-and-balance`, `versioning`, `ai-copilot` and
`construction-plans` each have their own. The frontend's `lib/parseApiError.ts`
exists solely to absorb the difference. Separately, `matching_chart.py` and
`field_lengths.py` deliberately map a bare `ServiceException` to **422** while
every other handler maps it to **500**.

**Why it's ambiguous.** Every module's `contracts.md` error table depends on the
answer, as does whether `parseApiError.ts` can be deleted.

**Candidates.**
- **(a) `{"error": {…}}` everywhere; delete the local mappers; add an explicit
  `ValidationDomainError → 422`** so the deliberate 422s survive as a *type*
  rather than a per-file habit. One client contract; `parseApiError.ts` goes;
  breaking for anyone parsing `detail`.
- **(b) `{"detail": …}` everywhere** (FastAPI-native). Smaller diff, loses the
  structured `code`, and the 422 divergence has nowhere to live.
- **(c) Keep both and document both.** The status quo, made official.

**Recommendation.** (a). Evidence: the 422 behaviour in `matching_chart` /
`field_lengths` is described in the corpus as deliberate and *better* than the
500 default — and only a named exception type makes it reproducible instead of
accidental. `Q-MS-8` records the user-visible cost of not having it: the same
class of cold-start mistake gets a remediation sentence on one endpoint and
"Unexpected error" on another.

---

#### `Q-CC-9` — Should the closed sets become database enums or check constraints?

**What the code does today.** `component_tree.node_type`,
`weight_items.category`, `construction_plans.plan_type`, the TED `role` and
`created_by` are validated in Pydantic only; the DB columns are plain `String`.
The sharpest case is `created_by`: **four writers, three vocabularies** — the
column comment and `BranchRequest` document `'human' | 'ai'`,
`copilot_apply_service` writes `'copilot'`, and legacy `aeroplanes.created_by`
is `NULL` and unbackfilled. **Any UI filtering on `'ai'` misses every copilot
branch.**

**Why it's ambiguous.** `permissions.md` §6 names this as the seam a future
identity model would attach to, so the vocabulary is not purely cosmetic — it
interacts with `Q-CC-1(c)`.

**Candidates.**
- **(a) Adopt `'human' | 'copilot'`, backfill NULLs, add a CHECK on all five
  columns.** The UI filter works; `Q-CO-12`'s string-matched proposal lookup can
  key off a typed value.
- **(b) Adopt `'human' | 'ai'` and change `copilot_apply_service`.** Matches the
  documented vocabulary — but `Q-CO-12` records that `_find_open_proposal`
  filters on `'copilot'`, so this breaks proposal reuse unless both are changed
  together.
- **(c) Keep loose; filter defensively in the UI.**

**Recommendation.** (a). The code is the ground truth here: `'copilot'` is what
is actually written to the database, and `Q-CO-12` states plainly that switching
to `'ai'` "would break reuse". So the documentation is the thing to fix, not the
writer. The DB-CHECK half is gated by `Q-CC-7`.

---

#### `P-DEAD-0` *(proposed)* — Dead-code disposition default

**What the code does today.** Thirty questions ask a variant of "delete, wire, or
keep as a template?" about code that is complete and unreachable. The range is
wide: `app/services/example.py` and `app/db/exceptions.py` (imported by nothing);
`cq_plugins/scaleXyz` (registered but never installed, and its implementation has
a typo'd `y_sacle` parameter); five `design-versions` routes whose service stub
unconditionally raises; `AirplaneConfiguration._main_wing_index = 0` (the same
assumption that made every coefficient ≈8× wrong for a tail-first import, fixed
in the app converter but not here); and four *completed mechanisms* —
`avl_artefact_service`'s full gh-529 replay verification, `validate_geometry`'s
gh-647 cross-check, `trigger_background_tessellation`, and `compute_recommended_cg`
(ADR 0011's central rule, unit-tested, with no production caller).

**Why it's ambiguous.** With no default, each is argued from scratch. The
catalogue names the real costs on both sides: "shipping it inert a second time is
worse than not having it" (`Q-VI-2`) and "any future caller would silently
inherit the bug" (`Q-CT-3`).

**Candidates.**
- **(a) Default delete; anything kept needs a ticket and a `# UNREACHABLE(gh-N)`
  marker.** Smallest surface; discards four completed mechanisms.
- **(b) Default wire-in this cycle.** Largest behaviour change — `Q-VI-1` alone
  changes what every import produces.
- **(c) Triage by class:** delete pure debris; wire the safety/confidence
  mechanisms (`Q-AV-3`, `Q-VI-2`); keep documented templates only where a ticket
  exists (`Q-CG-4`/#202, `Q-VI-10`/#638).

**Recommendation.** (c). The thirty questions split cleanly into those three
groups, and the split is not a judgement call: some items have an explicit
retention argument in the corpus, and others (`Q-CC-16`, `scaleXyz`) have none
at all.

---

#### `Q-CC-4` — Two `Settings` classes and three version strings

**What the code does today.** `app/core/config.py` and `app/settings.py` both
define a class named `Settings`, both export a module-level `settings`, both read
`.env`, with disjoint fields, different naming conventions (SCREAMING_CASE vs
snake_case) and live consumers on both sides. `app/settings.py` additionally
exposes a module singleton **and** a separately-`lru_cache`d `get_settings()`
that returns a *different* instance. Three version strings coexist:
`core.config.VERSION = "1.0.0"`, `settings.version = "0.1.0"` (the one `/health`
reports) and `FastAPI(version="2.0.0")`. Three more settings escape both classes
via bare `os.getenv`: `SQLALCHEMY_DATABASE_URL`, `LOG_LEVEL`,
`DISPLAY_CONSTRUCTION_STEP`.

**Why it's ambiguous.** The spec currently has to document both classes as
equally real, and `/health` reports a version nothing else uses.

**Candidates.**
- **(a) Merge into one `Settings` (snake_case); one `__version__` sourced from
  `pyproject.toml`; keep `SQLALCHEMY_DATABASE_URL` as a documented bootstrap
  exception.** Clean; touches every consumer.
- **(b) Merge the classes, keep three versions with distinct documented meanings**
  (API version vs release version vs schema version) — only defensible if they
  genuinely mean different things.
- **(c) Leave both; document both.**

**Recommendation.** (a). Two identically-named classes with a duplicated
singleton is a plain defect, and the corpus already shows the cost of nobody
owning config: `settings.base_url` defaults to `http://localhost:8000` while the
service listens on 8001, so the MCP asset-URL fallback is wrong out of the box
(`Q-MC-3`).

---

#### `Q-CC-13` — Should the `cad_designer/**` quality-gate exclusion be narrowed?

**What the code does today.** ADR 0002 freezes `airplane/aircraft_topology/**`
and `GeneralJSONEncoderDecoder.py`. But `sonar.exclusions`
(`sonar-project.properties:10`) and ruff's `extend-exclude`
(`pyproject.toml:122-129`) cover the whole of `cad_designer/**` — including
`geometry/`, `creator/`, `cq_plugins/` and `aerosandbox/`, where the actively
developed #1008/#1030/#1075/#1076 spar pipeline lives. ≈22 000 LOC is neither
linted nor coverage-measured.

**Why it's ambiguous.** It decides whether new geometry code is spec'd as gated
or ungated — and it is the real reason the four `cad-designer-topology` questions
feel closed: "we don't touch this layer" is currently justified by the tooling
exclusion, which is broader than ADR 0002's actual boundary.

**Candidates.**
- **(a) Narrow both to `aircraft_topology/**` + `GeneralJSONEncoderDecoder.py`.**
  New spar/turbulator code returns to the gate; hundreds of findings appear on
  first run; a baseline or `# noqa` pass is needed, and SonarCloud's
  new-code coverage threshold starts applying to geometry code.
- **(b) Narrow ruff only; keep Sonar broad.** Cheap and mechanical: formatting
  and lint on new code, no coverage cliff.
- **(c) Status quo.** ADR 0002's boundary and the tooling's boundary stay
  different — itself a documented inconsistency.

**Recommendation.** (b) as a staged first step. It matches ADR 0002's real
boundary for the linter at near-zero cost, and defers the coverage cliff, which
is the only expensive part of (a).

---

#### `Q-CC-11` — Should a generated TypeScript client replace the hand-written mirrors?

**What the code does today.** 48 SWR hooks each redeclare their own response
interfaces; only `types/versioning.ts` and `types/versionGraph.ts` are shared,
and nothing is generated from `/openapi.json` (which the backend publishes).
`npx tsc --noEmit` against hand-written test fixtures is the only detector of a
backend schema change — which is precisely why that CI gate exists.

**Why it's ambiguous.** Is the hand-mirroring a deliberate cost (it keeps the
frontend independent of a generator's output shape), or simply never automated?

**Candidates.**
- **(a) Generate types only** into `types/api.d.ts`; hooks import from it. A
  backend rename becomes a compile error instead of a runtime `undefined`; adds a
  codegen step to CI; the `tsc` gate keeps its value.
- **(b) Generate a full client** (typed fetch functions + types) — this also
  answers `Q-FW-2`'s "one HTTP client" question in the same move.
- **(c) Keep hand-mirroring; document it as deliberate.**

**Recommendation.** No evidence-backed default between (a) and (b) — that is a
frontend-architecture preference. But the evidence is against (c): the
`tsc --noEmit` CI gate exists specifically because hand-mirrors drift, which
says the drift is real and recurring rather than hypothetical.

---

#### `Q-CC-15` — Do the five ownerless schema files belong to a shared contracts unit?

**What the code does today.** `app/schemas/spar_plan.py`, `spar_insert.py`,
`section_geometry.py`, `flight_profile.py` and `WingAnalysisRequest.py` are each
imported by handlers in more than one module, so the import graph yields no
single owner and the traceability matrix scores them `n/a`. Their behaviour *is*
documented in the consuming modules' `contracts.md`, but no unit owns the file.

**Why it's ambiguous.** The consequence is already visible: `SparPlanResult`'s
real field names are still unknown (`Q-CP-4`), and `_metrics_payload` became a
de-facto public contract with a private name (`Q-VS-7`). The file nobody owns is
the file nobody read.

**Candidates.**
- **(a) A `shared-contracts` unit in the spec** owning all five. Clean
  traceability; invents a module with no code of its own.
- **(b) Assign each to its dominant consumer** — `spar_plan.py` + `spar_insert.py`
  → construction-plans, `section_geometry.py` → wing-design, `flight_profile.py`
  → mission-and-sizing, `WingAnalysisRequest.py` → aero-analysis.
- **(c) Leave them `n/a`.**

**Recommendation.** (b), evidence-backed by the failure mode itself: ownership,
not location, is what was missing. (a) becomes the better answer if more shared
schemas appear — it is worth revisiting once there are, say, ten.

---

#### `Q-CC-5` — Should the German user-facing strings be translated?

**What the code does today.** In an otherwise English product with an explicit
English-only UI rule: `"name existiert bereits"` (IntegrityError → 409) and
`"Ungültige Eingabedaten"` (RequestValidationError → 422) in `app/main.py`; the
`PolarRejection.hint` strings surfaced to the UI whenever `category == "design"`;
the seeded component-type labels (`"Durchmesser"`, `"Steigung"`, `"Blätter"`,
`"Dauerstrom"`) rendered directly in the component editor; and the
`flight_profiles` handler docstrings, which appear verbatim in the OpenAPI
document.

**Why it's ambiguous.** Changing the two handler messages is a client-visible
change; changing the seeded labels needs a data migration. So "just translate it"
is not free in either place.

**Candidates.**
- **(a) Translate all four groups**, with an Alembic data migration for the seeded
  labels. Consistent product; one breaking-ish change to messages that nothing
  should be string-matching anyway.
- **(b) Translate everything except the seeded labels**; defer the migration.
- **(c) Treat the `PolarRejection.hint` strings as developer-facing and leave
  them** (this is `Q-AA-7`'s question).

**Recommendation.** (a). The project has an explicit English-only UI rule, and
(c) is unavailable for the hints specifically: gh-956's entire purpose was
surfacing design-category rejections *to the user*.

---

### Wave 2

#### `Q-MB-1` — Two mass producers write one column: which one wins?

**What the code does today.** `weight_items` and the component tree both write
`design_assumptions["mass"].calculated_value`, with no arbitration. An aircraft
populated in both ends up with whichever source was touched last;
`calculated_source` records the winner and nothing warns that the other estimate
was discarded. Replaying the same edits in a different order yields a different
aircraft mass. Compounded by the absence of a `component_id` on `weight_items`:
the same battery entered in both places is two unrelated rows, double-counted,
with nothing to detect it.

**Why it's ambiguous.** Mass drives retrim, `V_stall`, the matching chart, the
solution space and endurance — every sizing surface reads it.

**Candidates.**
- **(a) Component tree authoritative; `weight_items` becomes a read-only view.**
  Single source; loses the ability to record a mass without a tree node; needs a
  migration path for existing weight items.
- **(b) `weight_items` authoritative; the tree only fills in when weight items
  are empty.** Smaller change, but the tree is the richer model (materials,
  quantity, print resolution).
- **(c) Sum both, with a `component_id` link for de-duplication.** Most faithful
  to "some things live in the tree, some don't"; most complex; requires the dedup
  key that does not exist today.
- **(d) Keep both; emit a divergence warning** (`P-WARN-0`). Cheapest; does not
  make the number deterministic.

**Recommendation.** No evidence-backed default between (a) and (c) — this is a
product-model call. But (b) is weakly contraindicated: `Q-MB-4` records that only
`weight_items` carry positions, so a tree-built aircraft already has a mass and a
`null` CG. The two models are not interchangeable in either direction today, and
whichever is chosen, the other needs an explicit story.

---

#### `Q-AA-1` — `_auto_populate_cd0` writes total CD into the `cd0` assumption

**What the code does today.** `stability_service._auto_populate_cd0` (`:257-281`)
writes `result.CD` — the **total** CD at the operating point — into the `cd0`
design assumption with `calculated_source="stability_analysis"`, whenever an
AeroBuildup stability summary is requested. `recompute_assumptions` writes the
**parasite** CD0 (`CD_total − CL²/(π·AR·e)`) — the quantity gh-924 / ADR 0004
made authoritative. The two run on different triggers, so the stored `cd0` flips
between a parasite and a total value between recomputes.

**Why it's ambiguous.** On a cambered wing (CL(α=0) ≈ 0.55 on a glider) the
total-CD value collapses (L/D)max from ~24 to ~17 — a plausible-looking number,
not an error — and nine consumers read it.

**Candidates.**
- **(a) Delete `_auto_populate_cd0`.** The assumption then has exactly one
  producer. Anyone relying on the stability path to seed `cd0` on a cold-start
  aircraft loses that seeding.
- **(b) Rewrite it to publish the parasite split via `_parasite_cd0`** (the same
  formula `recompute_assumptions` uses). Keeps cold-start seeding; the two paths
  must then agree on `e` and `AR` or they diverge again by a smaller amount.
- **(c) Keep it, tag `calculated_source`, and warn on divergence** (`P-WARN-0`).
  Preserves both behaviours; leaves a user staring at two `cd0` values.

**Recommendation.** ADR 0004 ("one aero truth per aircraft") argues directly for
(a): two writers to one authoritative field is exactly what the ADR removes. Take
(b) only if something genuinely depends on the stability path to seed `cd0` — so
the concrete thing to confirm is whether any cold-start flow has no other route
to a `cd0`.

---

#### `Q-MS-1` — `power_to_weight`: W/kg or T/W?

**What the code does today.** The assumption catalogue's default is `220.0`
**W/kg**. `motor_glider` and `flying_wing` use `100.0` W/kg, pinned by the
gh-580/gh-582 tests. The other seven presets carry `0.0`–`1.4`, dimensionless and
T/W-shaped. Selecting `trainer` therefore declares a **0.5 W/kg** aircraft. Both
the matching chart's power-loading constraint and the `is_glider` test
(`P/W ≤ 0`) consume the value.

**Why it's ambiguous.** Seven of nine shipped presets seed a physically absurd
value into a sizing input, and nothing in the code says which reading is meant.

**Candidates.**
- **(a) W/kg is canonical; backfill the seven presets** to realistic values
  (trainer ≈ 150, sport ≈ 200, aerobatic ≈ 300+ W/kg). A seed rewrite plus a data
  migration for aircraft that already applied a preset; the `is_glider` test
  stays valid.
- **(b) T/W is canonical** — change the catalogue default, the two W/kg presets
  and their two pinned tests. Contradicts the parameter's own name and its unit
  metadata.
- **(c) Split into two parameters** (`power_to_weight_w_kg` and
  `thrust_to_weight`). Physically cleanest — they are different constraints, and
  the matching chart arguably wants both — and the largest change.

**Recommendation.** (a). Three independent sources of truth (the catalogue
default, two presets, two pinned tests) say W/kg; only seven preset literals say
otherwise. The majority of *code* agrees on W/kg, so the presets are the defect.
Note that (a) does not answer whether the matching chart also needs a real T/W —
that is `Q-MS-2`/`Q-MS-9` territory.

---

#### `Q-FD-2` — What unit is an uploaded STEP assumed to be in?

**What the code does today.** Verified during review: `slice_step_to_fuselage`
(`cad_designer/aerosandbox/slicing.py:856-865`) takes **no** scale or unit
parameter, and `app/services/fuselage_slice_service.py` performs no scaling. The
emitted `a` / `b` / `xyz` are the STEP's **native** coordinate values, persisted
as metres. That is safe on the OpenVSP path only because BR-OV13 forces
`STEPSettings.LenUnit = LEN_M`. On the user-upload route nothing constrains the
unit — and millimetres are both the normal CAD authoring convention and the
convention `cad_designer` itself uses (ADR 0001). A millimetre STEP yields a
fuselage **1000× too large**, silently: `volume_ratio` / `area_ratio` stay ≈1.0
because they are reconstruction-to-original ratios. The same applies to
construction parts, where the columns are `volume_mm3` / `area_mm2` / `bbox_*_mm`
so millimetres are assumed and `_extract_geometry` verifies nothing — a metre
STEP records a volume 10⁹× too small.

**Why it's ambiguous.** Two upload paths assume opposite units, and neither
checks. This is the most reachable silent-1000× path in the system.

**Candidates.**
- **(a) Required explicit `source_unit` parameter** (`mm|m|in|ft`) on both upload
  routes. Unambiguous; breaking for existing clients; puts the burden on the user.
- **(b) Read the unit from the STEP header** (`SI_UNIT` / `CONVERSION_BASED_UNIT`
  in AP203/AP214) with an explicit override, and 422 when absent. Most files
  carry it; fails closed.
- **(c) Plausibility detection** (bounding-box span against an RC-scale prior)
  plus a warning. Same family as `_detect_source_scale_to_meters`.
- **(d) Document "metres only" and reject anything whose bbox reads as
  millimetres.**

**Recommendation.** (b) with (a) as the override, and **the two upload paths must
give the same answer**. Evidence: the STEP header is authoritative data the file
already carries, and (c) has a demonstrated blind spot on this exact system —
`Q-VI-3` records that the existing measured detection returns `None` for a
wing-only model and applies no conversion at all.

---

#### `Q-WD-1` — Who should own the gh-772 mixing-name mapping (bug #955)?

**What the code does today.** The canonical control name is
`[{role}]{axis}_{wing_key}_{xsec_index}`. Three consumers still key on the raw
TED name from the DB: `trim_enrichment_service.build_deflection_limits_from_schema`,
`retrim_service._find_pitch_control_name`, and `stability_service._find_trim_elevator`
— the last a substring match on `"elevator"`, which never matches
`[ruddervator]pitch_…`. On any V-tail / elevon / flaperon aircraft the lookup
misses, authority is computed against a hard-coded **±25°**, and a **phantom 0°
surface** is injected under the DB name.

**Why it's ambiguous.** Fixing the three call sites fixes #955 once. The question
is what makes it structurally impossible to recur. There is also a ±25°
collision: the topology layer *also* defaults `positive/negative_deflection_deg`
to 25°, so a report cannot distinguish "the real limit is 25°" from "the lookup
failed".

**Candidates.**
- **(a) `control_surface_mixing` exports `resolve_control_name(...)` that
  trim/retrim/stability are required to call**, plus a test asserting no consumer
  reads `ted.name` directly. Divergence becomes structurally impossible.
- **(b) Key deflection limits by `(role, surface_suffix)`** instead of by name.
  Removes the name from the lookup entirely; larger schema change.
- **(c) Fix the three call sites only.** Recurs at the next consumer.

Independently: **the fallback should use a distinguishable sentinel** (`None`
plus a `P-WARN-0` warning), never 25°.

**Recommendation.** (a) plus the sentinel. Evidence: three independent consumers
already drifted from the canonical name, which is the definition of a missing
shared resolver — and the catalogue states outright that the structural answer is
what stops #955 recurring. Sequence this **before** `Q-VI-1`: turning on
`SS_CONTROL` while the resolver is still broken means every newly imported
aircraft inherits the phantom-surface behaviour.

---

#### `Q-VS-1` — Snapshots are not actually immutable

**What the code does today.** Verified during review: `_guard_immutable` is
defined at `app/services/aeroplane_version_service.py:65` and called from
**exactly one** place — line 151, inside `snapshot()`. Nothing stops
`PUT /aeroplanes/{snapshot_uuid}/wings/…` from mutating a frozen node through the
ordinary wing / fuselage / spar CRUD routes.

**Why it's ambiguous.** This is the guarantee that ADR 0006 (row-copy versioning)
and ADR 0007 (copilot propose/adopt) both rest on. It is currently a convention
that one code path checks.

**Candidates.**
- **(a) Move the guard into the aeroplane resolver** (the `get_aeroplane_or_404`
  dependency) so every write path inherits it. One place; covers routes not yet
  written; needs a read/write distinction in the resolver.
- **(b) A SQLAlchemy `before_flush` listener** rejecting writes to any row whose
  aeroplane is frozen. Also catches services that bypass the resolver; harder to
  produce a good error message.
- **(c) Add the guard at each write service.** The current pattern, extended.

**Recommendation.** (a), with (b) as a test-only assertion so a bypass is caught
in CI rather than in production. Evidence against (c): the same per-call-site
convention has a demonstrated failure rate in this codebase — three consumers
drifted in `Q-WD-1`, two writers in `Q-MB-1`, four writers in `Q-CC-9`.

---

#### `Q-MC-1` — MCP writes are discarded: fix or formalise as read-only?

**What the code does today.** Verified during review: `_call_endpoint`
(`app/mcp_server.py:96-107`) opens `with SessionLocal() as db:`, calls the
endpoint and returns — **no `commit()`**. `Session.__exit__` rolls back. ~40 of
the 76 tools are mutations returning a convincing payload built from
flushed-but-uncommitted ORM state (readable only because `expire_on_commit=False`)
while persisting nothing. Durability is *inconsistent*, not merely absent:
services that commit themselves (`retrim_service`,
`operating_point_generator_service`, `tessellation_service`) **do** persist. No
test can catch it — the tool tests monkeypatch `_call_endpoint`, and the
`_call_endpoint` tests use fake local functions.

**Why it's ambiguous.** Fix versus formalise changes the module's entire
contract; and fixing it makes ~40 unauthenticated destructive tools genuinely
work (`Q-CC-1`).

**Candidates.**
- **(a) Add a `get_db()`-equivalent context manager** (commit on success,
  rollback on exception). Matches ADR 0009's transaction boundary. Then the
  self-committing services need review for nested-commit behaviour — this is not
  a one-line change.
- **(b) Formalise MCP as read-only; remove the ~40 write tools.** Smallest risk
  surface, consistent with `Q-CC-1(b)`; loses agent-driven design edits entirely.
- **(c) Fix the boundary but gate the write tools behind `MCP_ALLOW_WRITES`.**
  Keeps both options open; the flag is the identity substitute `Q-CC-1` lacks.

**Recommendation.** (c). ADR 0009 says `get_db()` owns the transaction boundary,
so the current behaviour is a straightforward violation of an accepted decision;
ADR 0016 says there is no auth, so making 40 destructive tools work
unconditionally is a real regression. Whichever is chosen, add a test that
exercises a **real** session — no current test can see this defect.

---

#### `Q-CP-1` — Should plan execution move into the CAD process pool?

**What the code does today.** `cad_service`'s module docstring records the root
cause verbatim: OCCT is not thread-safe, and the same `.intersect().clean()` call
that takes ~100 ms on the main thread **hangs indefinitely** in a worker thread.
That is why every CAD build goes through a spawned `ProcessPoolExecutor` (ADR
0005). Yet `execute_plan` (step 7) calls `root_node.create_shape()` **on the
FastAPI request thread**, and `execute_plan_streaming` runs it on a
`threading.Thread` — both driving the same CadQuery/OCCT stack. Streaming also
arms `set_display_callback` and `os.environ["DISPLAY_CONSTRUCTION_STEP"]`, both
process-global with no lock and no per-execution context, so two concurrent
streams cross-deliver shape events and can clobber each other's display gate.

**Why it's ambiguous.** Either the process isolation is unnecessary or plan
execution is exposed to the documented hang. A re-implementation must not pick
one silently.

**Candidates.**
- **(a) Move plan execution into the CAD process pool.** Consistent with ADR
  0005; streaming then needs a pipe or queue for progress events instead of a
  process-global callback — which also fixes the cross-delivery.
- **(b) ADR 0005 is over-broad** — the hang is specific to `.intersect().clean()`
  in a *worker thread*, and the request thread is the main thread, so
  `execute_plan` is arguably safe. Narrow the ADR.
- **(c) Keep both paths; document the hang risk.**

**Recommendation.** (a). Even under (b), `execute_plan_streaming` uses exactly
the construct the docstring names as fatal (`threading.Thread`), so the streaming
path is a live bug either way. Whether concurrent executions are in scope at all
is a separate product call — if they are not, say so explicitly, because the
process-global `DISPLAY_CONSTRUCTION_STEP` currently assumes they are not.

---

#### `Q-CG-1` — 3MF export is broken and a test pins the bug

**What the code does today.** Verified during review. `map_exporter_type`
(`cad_service.py:196`) returns `"ExportTo3MFCreator"`; the real class is
`ExportTo3mfCreator` (`.../ExportTo3mfCreator.py:10`). The `$TYPE` decoder uses
`getattr`, so every 3MF export raises `AttributeError` in the worker and the task
ends `FAILURE`. `app/tests/test_cad_service_extended.py:130` asserts the
**wrong** string, so the suite is green and stays green through a partial fix.
`construction_plan_service.py:559` already uses the correct spelling. Same rule:
`ExporterUrlType.AMF = "amf"` exists with **no** mapping entry, so every AMF
request 422s.

**Why it's ambiguous.** The enum is the public contract, so both fixing and
removing are client-visible changes.

**Candidates.**
- **(a) Fix the mapping and the test; keep both formats.** Two advertised formats
  start working. The test is pinning the bug, so it must be corrected (the
  project rule is "fix the code, not the tests"), and 3MF/AMF then need a real
  smoke test since nothing has ever exercised them.
- **(b) Remove 3MF and AMF from `ExporterUrlType`.** Honest but breaking; the
  export surface shrinks.
- **(c) Fix 3MF (a one-character change plus the test), drop AMF.**

**Recommendation.** (c). 3MF has a working creator *and* a correct call site
already (`construction_plan_service.py:559`), so it is a typo, not a missing
feature. AMF has no mapping entry and no evidence of a creator, so it is an
unimplemented enum member — different problem, different answer.

---

#### `Q-VI-1` — Wiring the `SS_CONTROL` post-pass changes what an import produces

**What the code does today.** Verified during review: the gh-644 post-pass is dead
**twice over**. `openvsp_ss_control.register()` has exactly one caller in the
repository (`app/tests/test_openvsp_ss_control.py:24`) and is absent from
`_ensure_handlers_loaded`; and even if it ran, `_persist_aeroplane` writes wings
through `AsbWingGeometryWriteSchema` (`extra="forbid"`), whose
`WingXSecGeometryWriteSchema` has **no `trailing_edge_device` field at all**.
Fixing only the registration changes nothing.

**Why it's ambiguous.** Every aircraft imported so far arrived with **no** control
surfaces. Turning this on starts creating TEDs with role `OTHER`. Whether
anything downstream — trim, operating points, the copilot — assumes their
absence is unconfirmed.

**Candidates.**
- **(a) Wire both halves** (register + extend the write schema). Matches the
  spec's stated intent for RF-29 ("the user can re-tag control surfaces in the UI
  afterwards, which was always the intent"). Interacts with `Q-WD-1` (role
  `OTHER` has no axis mapping) and `Q-MS-12` (`has_pitch_control` would start
  firing on imported aircraft).
- **(b) Wire it behind an import option** (`import_control_surfaces: bool =
  False`). Existing users' imports stay reproducible; new users opt in.
- **(c) Delete both halves**; document that control surfaces are always
  user-authored.

**Recommendation.** No evidence-backed choice between (a), (b) and (c) — but
(b) is the lowest-regret **ordering**, and in any case this must be sequenced
after `Q-WD-1`. Creating role-`OTHER` TEDs while the naming/limit lookup is still
broken means every newly imported aircraft picks up the ±25° phantom-surface
behaviour that #955 describes.

---

#### `Q-CO-12` — Should the proposal branch be typed rather than string-matched?

**What the code does today.** A proposal is identified by
`name LIKE 'copilot-proposal%'` plus `created_by = 'copilot'`. Five consequences:
a human renaming the branch **orphans** it (the next AI edit opens a second
proposal); `_find_open_proposal` takes the newest by `id DESC` and
`create_branch` has no collision check, so an older proposal is silently
abandoned with its edits; `created_by = 'ai'` is documented by `BranchRequest`
and **would break reuse** because the query filters on `'copilot'`; a
fully-rejected op batch still leaves the branch open, so the UI shows a proposal
containing no changes; and adopt-during-turn is unspecified and untested — once
the proposal becomes `main`, a later tool call in the same turn opens a *second*
proposal from the adopted design.

**Why it's ambiguous.** Five failure modes with one root cause, and the fix
interacts with `Q-CC-9`'s `created_by` vocabulary decision.

**Candidates.**
- **(a) `branches.branch_kind` enum column** (`user` | `copilot_proposal`) plus a
  unique partial index on (lineage, open proposal). Removes the shared root;
  needs a migration and a backfill from the name pattern.
- **(b) Keep string matching; add a collision check and a rename guard.**
  Patches three of five.
- **(c) (a) plus an explicit proposal state machine** (`open` → `adopted` |
  `discarded`), which defines adopt-during-turn.

**Recommendation.** (c). Adopt-during-turn is the one failure mode a collision
check alone cannot fix, and a typed column simultaneously settles `Q-CC-9` for
branches. Note the interaction: if `Q-CC-9` picks `'human' | 'ai'`, the
`'copilot'` filter must change in the same commit or proposal reuse breaks.

---

#### `Q-WD-8` — Spar-sizing factor ownership *(numerically load-bearing)*

**What the code does today.** Four unconfirmed points, each of which changes the
computed spar diameter. (1) `moment_fn` provenance — which service produces the
bending-moment distribution, at which load case, and whether it already applies
`g_limit` / `j`; a double application would be silent and would oversize every
spar by 4.5×. (2) `packing_factor` may be applied twice: it scales `outer(y)` in
the sizing formula (`spar_sizing.py:13`) *and* derives the containment band
during station sampling. (3) Every station's `required_od` is solved as a **rod**
regardless of the requested shape, so the band check is conservative for capped
and rectangular spars. (4) `_MIN_REAR_X_C = 0.05` can defeat hinge clearance:
when `hinge_x_c − 0.03 < 0.05` the floor wins and the computed rear spar sits
**inside** the control surface, with no warning.

**Why it's ambiguous.** This feeds a structural safety output consumed directly
by the builder, and none of the four can be inferred from the code that was read.

**What the interviewer needs** (these are confirmations, not choices):
1. The producing service and load case for `moment_fn`, and whether `g_limit`/`j`
   are already inside it.
2. Yes/no on the double `packing_factor`.
3. Rod-equivalent OD intentional, or should it use the requested shape's actual
   height?
4. Should the `_MIN_REAR_X_C` floor warn (`P-WARN-0`), or yield to hinge
   clearance?

**Recommendation.** No evidence-backed default — this needs the code. Whatever the
answers, add a regression test that computes one spar by hand at a known load
case, so a double application can never be reintroduced silently.

---

#### `Q-AF-3` — What are the confidence *tier* boundaries used for ranking?

**What the code does today.** BR-C25 says ranking sorts by
`(confidence tier, −score)` so a high-scoring low-confidence airfoil never
outranks a trustworthy one. `low_re_low_confidence_flag = 0.85` is the documented
UI badge threshold — but whether the ranking tier uses that same value, and how
many tiers exist, is unconfirmed.

**Why it's ambiguous.** A re-implementation cannot reproduce the ranking order
without it. It is the single most load-bearing unknown in `airfoil-catalog`.

**Candidates.** (a) two tiers at 0.85, reusing the badge threshold; (b) three
tiers (e.g. ≥0.95 / ≥0.85 / below); (c) no tiers — the "tier" is a boolean
derived from `low_re_low_confidence_flag`.

**Recommendation.** No evidence-backed default. **This is a lookup, not a
decision** — paste the sort key from the suitability service and the question
closes. If the answer turns out to be (a), it is also worth recording explicitly
that the badge threshold and the ranking tier are deliberately the same number,
because otherwise they will drift.

---

#### `Q-CP-4` — What are `SparPlanResult`'s actual field names?

**What the code does today.** Only `front_no_spar_from_y` and
`rear_no_spar_from_y` are confirmed by name (from the gh-1076 test mocks); the
remaining fields were inferred from behaviour. `app/schemas/spar_plan.py` has no
home unit (`Q-CC-15`), which is why this was never pinned down.

**Why it's ambiguous.** The response shape cannot be reproduced exactly from the
spec alone — the module's one hard blocker for re-implementation.

**Recommendation.** **Lookup, not a decision** — paste
`app/schemas/spar_plan.py`. Pair it with `Q-CC-15(b)`, which gives the file an
owning unit so the same gap cannot recur for the other four ownerless schemas.

---

#### `Q-CG-3` — Is the viewer relying on per-part bounds, or is camera-fit silently wrong?

**What the code does today.** Verified during review. The worker writes
`shapes["bb"] = combined_bb(shapes).to_dict()`, which `ocp_tessellate` returns as
`{xmin, xmax, ymin, ymax, zmin, zmax}`; `_expand_bounding_box` (`cad.py:91-95`)
returns early unless the dict carries `"min"` **and** `"max"`. So
`GET /aeroplanes/{id}/tessellation` always answers
`bb = {"min":[0,0,0],"max":[0,0,0]}`.

**Why it's ambiguous.** Whether this is a cosmetic camera issue or a visible bug
depends entirely on whether `three-cad-viewer` computes its own bounds from the
parts — which was not determined from the source.

**Candidates.**
- **(a) Fix `_expand_bounding_box`** to accept the `xmin/xmax/…` key set.
  Smallest change; correct camera fit for multi-wing scenes.
- **(b) Normalise at the producer** (`combined_bb` → `{min:[…], max:[…]}`). One
  key set on the wire; breaking for any client reading `xmin`.
- **(c) Leave it if the viewer self-fits**, and delete the dead `bb` field.

**Recommendation.** (b) if a fix is wanted, but the **first step is empirical**:
open a multi-wing aircraft in the workbench and check whether camera-fit is
actually wrong. A unit test cannot answer this — shape-only assertions in jsdom
cannot verify viewer layout or camera behaviour, so this needs a real browser.

---

*Sources: [`questions.md`](questions.md) · [`gaps.md`](gaps.md) ·
[`adrs/`](adrs/)*
