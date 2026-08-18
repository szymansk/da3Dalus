---
name: mass-effective
symbol: m
kind: quantity
unit: kg
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Effective aircraft mass

**Definition.** The mass value actually used by the compute pass: the calculated value when active_source == CALCULATED, otherwise the user's estimate; PARAMETER_DEFAULTS when the row is missing.

**Derived quantity.** Computed from the inputs below.

**Value.** `1.5 fallback (PARAMETER_DEFAULTS['mass'], app/schemas/design_assumption.py:73)`

**Formula — as the code writes it.**

```
if row.active_source == "CALCULATED" and row.calculated_value is not None: return row.calculated_value; return row.estimate_value
```

**Inputs.**

- [[aircraft-total-weight-kg|Aircraft total weight from component tree]]

**Produced by.** `app/services/assumption_compute_service.py:531` — `recompute_assumptions (_load_effective_assumption, def at line 1709)`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Published aircraft mass (computation context)` · `Weight force`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:538/545/546 (_stall_speed)` · `app/services/assumption_compute_service.py:548-558 (V_md, V_min_sink, w_min)` · `app/services/assumption_compute_service.py:564 (_max_level_speed)` · `app/services/assumption_compute_service.py:714 (ctx['mass_kg'])` · `app/services/assumption_compute_service.py:772 (_compute_landing_field_length)` · `app/services/mass_cg_service.py:277`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 — ΣW_i = W_TO at maximum take-off weight; §10.4 establishes the two admissible provenances for a component mass (measured/published actual weight, Table 10.5; or the calibrated empirical equation), which is the same estimate-vs-calculated distinction the code models.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣW_i = W_TO   (Sadraey §11.2)
```

**⚠️ Divergence from the source.** Sadraey's weight statement has one value per component and therefore one aircraft mass. The code permits two independent writers of mass.calculated_value — sync_component_tree_to_mass (mass_cg_service.py:160, source='component_tree') and sync_weight_items_to_assumptions (mass_cg_service.py:174, source='weight_items') — with last-writer-wins and no reconciliation. No consulted source describes two parallel weight statements for one aircraft; §10.4's four sources are inputs to ONE equation, not competing totals.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two independent writers of mass.calculated_value (see aircraft-total-weight-kg anomaly): sync_component_tree_to_mass and sync_weight_items_to_assumptions.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Return the effective value of a design assumption (calculated or estimate)." — app/services/assumption_compute_service.py:1710`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
