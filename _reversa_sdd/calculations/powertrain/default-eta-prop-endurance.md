---
name: default-eta-prop-endurance
symbol: DEFAULT_ETA_PROP
kind: constant
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Default propeller efficiency

**Definition.** Flat propeller efficiency used by the sizing sweep when the request does not override it.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.65`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:53` — `DEFAULT_ETA_PROP`

**Consumed by.**

- in this graph: `Combo total propulsive efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:235`

**Source.** 🟢 SOURCED

> Deters, R.W., Ananda, G.K. & Selig, M.S. (2014), §VI (maximum-efficiency plateau for small-scale propellers): eta_max is constrained to roughly 60-70% at the low Reynolds numbers typical of UAVs and MAVs; a 9-inch model of the NR640 stays below 65% while the full-scale 10-ft version at Re ~ 1.8e6 exceeds 80%. Brandt & Selig, AIAA 2011-1255, §III: 'Typical values range from 0.28 (poor design) to 0.65 (efficient design) for small RC and UAV propellers.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_max ~ 0.60-0.70 at low Re (Deters §VI); 0.28-0.65 typical for small RC/UAV props (Brandt & Selig §III)
```

**⚠️ Divergence from the source.** 0.65 is well supported at RC/UAV scale — it is exactly the top of Brandt & Selig's typical band and inside Deters' 0.60-0.70 plateau. The code comment 'APC/Folding RC-Scale, Drela/Hepperle' name-drops the wrong authorities for this number; the attributable sources are the UIUC low-Re propeller measurements (Brandt & Selig 2011; Deters, Ananda & Selig 2014), not Drela or Hepperle.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The only literature attribution in the whole cluster, and it is a bare name-drop with no work, year, page or equation — not a citable source (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# APC/Folding RC-Scale, Drela/Hepperle`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
