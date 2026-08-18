---
name: cg-agg
symbol: x_cg,agg
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
---

# Aggregate CG (default scenario)

**Definition.** Single-value mass CG for backward-compatible clients: the CG of the is_default loading scenario, or — for pre-migration aeroplanes with no scenarios — the plain mass-weighted CG of the weight items.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return compute_scenario_cg(base_mass_kg=base_mass, base_cg_x=base_cg_x, adhoc_items=..., mass_overrides=..., toggles=..., position_overrides=..., components=components or None)   # legacy branch: _, cg_x, _, _ = aggregate_weight_items(items)
```

**Inputs.**

- [[scenario-cg-x|Loading-scenario CG_x]]
- [[base-mass-default|Fallback base mass for scenario CG]]  — *⤵ fallback*
- [[base-cg-x-default|Fallback base CG_x for scenario CG]]  — *ε tolerance*

**Produced by.** `app/services/loading_scenario_service.py:345` — `compute_cg_agg_for_aeroplane`

**Consumed by.**

- in this graph: `Published aggregate CG (computation context)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:469` · `app/services/assumption_compute_service.py:729 (ctx['cg_agg_m'])` · `frontend/components/workbench/StabilityChipRow.tsx:27-35` · `frontend/lib/metricsAdapters.ts:200-234` · `frontend/lib/metricsAdapters.ts:343-344` · `frontend/components/workbench/stability-overlay/buildStabilityTraces.ts:79` · `frontend/hooks/useComputationContext.ts:87`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 Eq. (11.1), X_cg = ΣW_i·x_cg,i / ΣW_i, evaluated for one loading condition; §11.3.2 requires the designer to "compute weight and balance for the start and end of flight and for every weight scenario in between", of which the default/design condition is one. Same construction in Scholz, D. et al., PreSTo (EWADE 2011) §1, which computes x_CG separately for the empty aircraft, OEW and the maximum-payload configuration.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
X_cg = ΣW_i·x_cg,i / ΣW_i   (Sadraey Eq. 11.1)
```

**Cited in the code itself.** `"Spec (gh-488): cg_agg_m MUST equal the CG of the ``is_default`` scenario." — app/services/loading_scenario_service.py:348`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
