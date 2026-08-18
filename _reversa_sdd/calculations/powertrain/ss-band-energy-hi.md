---
name: ss-band-energy-hi
symbol: energy_wh (hi band)
kind: quantity
unit: Wh
cluster: powertrain
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Mission energy at high prop efficiency

**Definition.** Energy budget recomputed with the optimistic propeller efficiency — produces capacity_mah_min_lo.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
energy_wh=p_cruise_hi_e * t_target_h / assumptions.dod
```

**Inputs.**

- [[ss-p-cruise-hi-e|Electrical cruise power at high prop efficiency]]
- [[ss-t-target-h|Target flight time in hours]]
- [[ss-dod|Depth of discharge]]

**Produced by.** `app/services/powertrain_solution_space_service.py:412` — `compute_solution_space`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:442`

**Source.** 🟡 PARTIAL

> E = P x t elementary. The high-efficiency endpoint 0.78 is NOT supported at RC scale (see ss-eta-prop-hi). The /DoD divisor has no source.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
E = P x t
```

**⚠️ Divergence from the source.** Produces the smallest capacity floor from the least-supported efficiency assumption in the band.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Its output field capacity_mah_min_lo is never rendered (notes F6).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# High-η band extreme (hi η_prop → lower currents/less capacity needed)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
