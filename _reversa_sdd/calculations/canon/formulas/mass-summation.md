---
canon: mass-summation
entry: formula
kind: law
shape: law
status: draft
output: aircraft-mass
source_status: SOURCED
dimensional_check: UNPARSEABLE
tags:
  - canon/formula
  - source/sourced
  - dim/unparseable
  - shape/law
  - kind/law
  - status/draft
---

# Aircraft mass as the sum of component masses

**Canonical form**

```
m = sum_i m_i
```

**Produces** [[aircraft-mass]]  ·  **from** [[component-mass]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

ℹ️ **Reclassified** from `procedure` by the trial of 2026-08-18. m = Σ m_i is a sum. It was classified as a procedure only because the summand set is gathered by a recursive database tree-walk, which the parser could not read as a formula. The traversal is an enumeration of the index set, not a numerical method: no iterate, no residual, no tolerance, nothing to converge. The genuine risk here is not method error but index-set error, and that belongs to the law's premise, not to a solver.

> 🔴 **An assumption of this entry is broken in the code.**
>
> app/services/component_tree_service.py:402 and :491 — `(own or 0.0)` breaks the sum's completeness assumption silently. A node with no `weight_override_g`, no COTS link and no CAD-derivable mass is returned as `(None, "none")` at :474 and then added as zero, so "I don't know this mass" and "this mass is zero" produce the same total, and the shortfall is unbounded and unmarked. Consequence chain, all read: mass_cg_service.py:160-171 writes that total to `mass.calculated_value` with `source="component_tree"` and `auto_switch_source=True`, making it the effective mass; assumption_compute_service.py:531-566 then derives V_stall, the per-configuration V_S/V_S0, V_md and V_min-sink from it, and V ∝ √m, so a tree missing (say) covering, wiring and hardware reports every user-visible speed low by √(m_sum/m_true) with no indication. Second, ADR 0022: mass_cg_service.py:211-221 `sync_weight_items_to_assumptions` writes the same `mass.calculated_value` from a *different* index set (`weight_items`, `source="weight_items"`), also with `auto_switch_source=True`. Two producers of one user-visible number, last writer wins, nothing reconciles them — an aircraft whose tree sums to 5 kg and whose weight items sum to 6 kg reports whichever synced last.

**Evaluated by.** Depth-first recursive traversal of the `parent_id` tree, one DB query per level, summing grams. app/services/component_tree_service.py:381-403 `get_aircraft_total_weight_kg` selects the roots (`parent_id IS NULL`, :389-396) and adds each root's own weight plus `_calculate_children_weight`; :477-492 recurses. Per-node weight resolution is a three-branch precedence chain at :461-474 — `weight_override_g`, else COTS, else CAD-derived, else `(None, "none")`. Result is `total_g / 1000.0` (:403).

**Accuracy.** Not applicable — a finite, exact sum. It terminates in O(N) queries provided assumption (1) holds; a cycle in `parent_id` would recurse until Python's RecursionError rather than diverge numerically. There is no criterion to configure and none is configured.

**On failure.** Three undeclared substitutions, none surfaced to the user. (a) component_tree_service.py:402 `(own or 0.0)` and :491 `(own or 0)` convert a node whose weight is unknown — `_calculate_own_weight` returning `(None, "none")` at :474 — into a 0 g node. (b) :403 `return total_g / 1000.0 if total_g > 0 else None` collapses "no tree" and "tree whose every node is unweighed" into the same None; the caller then clears `mass.calculated_value` and `get_effective_assumption_value` (mass_cg_service.py:126-128) silently reverts to `estimate_value`. (c) `_sync_aircraft_mass` (component_tree_service.py:362-379) swallows every exception with a server-side `logger.warning`, so a failed sync leaves a stale mass in the DB with the UI showing nothing. `grep -n DesignWarning` over component_tree_service.py and mass_cg_service.py returns zero hits — none of this is declared (ADR 0020).

**Dimensional check.** ⚪ not machine-checkable as written

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf, 02_DesignSequence §2.2 (design step 13, take-off mass iteration): m_TO = m_OE + m_F + m_PL. Sadraey Ch. 10 builds MTOW from the same component summation. RC: Lennon, Basics of R/C Model Aircraft Design, Ch. 26 tracks gross weight, wing area, wing loading, engine, prop and power loading as a coherent six-number design point.

**The source writes it as**

```
Scholz sums three mass GROUPS (operating empty, fuel, payload) rather than an arbitrary component tree; the tree is the app's generalisation.
```

**Validity at 0.5–15 kg.** Exact - summation is scale-free. One RC-specific note from Lennon Ch. 26: the discipline that matters is recording the design point as a SET (gross weight, wing area, wing loading, power loading, prop) rather than a single total, because the total alone does not tell you whether the airframe/propulsion combination will fly the mission. Also relevant to this project's stated design philosophy that mass starts as a manual estimate: the summation is only an authority once the tree is populated, so it must not silently override a user-supplied design mass (ADR 0022 - two producers of aircraft mass).

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[aircraft-total-weight-kg]] | DEVIATES | 🟢 | Sums only what the user actually placed in the component tree. There is no closed enumerat |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

