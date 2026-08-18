---
name: scenarios-eval
symbol: scenarios_eval
kind: quantity
unit: m (list)
cluster: mass
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Per-scenario CG list

**Definition.** The list of CG values, one per loading scenario, from which the loading envelope min/max are taken.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"scenarios_eval": cg_values
```

**Inputs.**

- [[scenario-cg-x|Loading-scenario CG_x]]

**Produced by.** `app/services/loading_scenario_service.py:447` — `compute_loading_envelope_for_aeroplane`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> The per-loading-case CG list is the documented INPUT to a balance envelope in both lead sources: Sadraey, M.H., Wiley 2013, §11.3.2 — the weight-vs-cg envelope is a polygon enclosing the allowable (weight, cg) combinations, and "the designer must compute weight and balance for the start and end of flight and for every weight scenario in between"; Scholz, D. et al., PreSTo (EWADE 2011) §1 — the loading diagram plots CG position against aircraft weight for each mission phase (departure fully loaded, mid-cruise, arrival light, empty). The list as an isolated named quantity has no citation of its own.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Both sources use the per-case list to DRAW an envelope; the code reduces it to min/max and discards the list (no reader found for 'scenarios_eval' anywhere in the repo). The information needed for Sadraey §11.3.2's polygon and PreSTo's loading diagram is computed and then thrown away.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO CONSUMER. Repo-wide search for 'scenarios_eval' returns only the docstring (line 408) and the two assignments (lines 424, 447). Both callers read exclusively cg_loading_fwd_m / cg_loading_aft_m.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"scenarios_eval: list of per-scenario CG values" — app/services/loading_scenario_service.py:408`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
