---
name: ss-eta-prop-lo
symbol: eta_prop_lo
kind: parameter
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Propeller efficiency band lower bound

**Definition.** Pessimistic end of the assumed propeller efficiency band.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.65`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:29` — `SolutionSpaceAssumptions.eta_prop_lo`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Mid-band propeller efficiency` · `Electrical cruise power at low prop efficiency` · `Electrical power required` · `Electrical peak power at low prop efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:357` · `app/services/powertrain_solution_space_service.py:364` · `app/services/powertrain_solution_space_service.py:370` · `frontend/components/workbench/PowertrainTab.tsx:1051`

**Source.** 🟢 SOURCED

> Deters, R.W., Ananda, G.K. & Selig, M.S. (2014), §VI: maximum achievable efficiency for small-scale low-Reynolds propellers is constrained to roughly 60-70%; a 9-inch NR640 at Re ~ 49,000 stays below 65% while the full-scale 10-ft version at Re ~ 1.8e6 exceeds 80%. Brandt & Selig, AIAA 2011-1255, §III: 'Typical values range from 0.28 (poor design) to 0.65 (efficient design) for small RC and UAV propellers.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_max ~ 0.60-0.70 (low-Re, UAV/MAV scale); 0.28-0.65 typical small RC/UAV props
```

**⚠️ Divergence from the source.** 0.65 is the best-attributed engineering constant in this cluster: it is simultaneously the top of Brandt & Selig's typical band and inside Deters' plateau, and it is measured at RC/UAV scale rather than transferred from transport literature.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 0.65 duplicates DEFAULT_ETA_PROP (endurance_service.py:53), prop_efficiency (design_assumption.py:88) and DEFAULT_ETA_PROP (powertrain_sizing_modal_service.py:31) — four declarations. Only the endurance_service one carries any attribution.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `NO_SOURCE_FOUND — field description is only "Lower bound of propeller efficiency band"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
