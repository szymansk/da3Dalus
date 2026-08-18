---
name: ss-band-energy-lo
symbol: energy_wh (lo band)
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

# Mission energy at low prop efficiency

**Definition.** Energy budget recomputed with the pessimistic propeller efficiency — the branch that produces capacity_mah_min_hi.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
energy_wh=p_cruise_lo_e * t_target_h / assumptions.dod
```

**Inputs.**

- [[ss-p-cruise-lo-e|Electrical cruise power at low prop efficiency]]
- [[ss-t-target-h|Target flight time in hours]]
- [[ss-dod|Depth of discharge]]

**Produced by.** `app/services/powertrain_solution_space_service.py:400` — `compute_solution_space`

**Consumed by.**

- outside it: `app/services/powertrain_solution_space_service.py:443` · `frontend/components/workbench/PowertrainTab.tsx:129`

**Source.** 🟡 PARTIAL

> E = P x t elementary; the low-efficiency endpoint 0.65 is supported by Deters/Ananda/Selig (2014) §VI and Brandt & Selig (2011) §III. The /DoD divisor has no source.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
E = P x t
```

**⚠️ Divergence from the source.** Same constant-cruise-power mission model as ss-energy-wh.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** SolutionRow.energy_wh (line 440) always carries the MID-band energy while capacity_mah_min_hi carries the LO-band energy — the Wh column and the mAh column in the same rendered table row are derived from different efficiency assumptions.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Low-η band extreme (lo η_prop → higher currents/more capacity needed)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
