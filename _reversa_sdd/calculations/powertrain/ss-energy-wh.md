---
name: ss-energy-wh
symbol: energy_wh
kind: quantity
unit: Wh
cluster: powertrain
user_visible: true
source_status: PARTIAL
---

# Required mission energy

**Definition.** Energy the pack must store: mid-band cruise power times mission time, divided by usable depth of discharge. Independent of cell count.

**Formula — as the code writes it.**

```
energy_wh = p_cruise_mid * t_target_h / assumptions.dod
```

**Inputs.** [[ss-p-cruise-mid|Electrical cruise power (mid band)]] · [[ss-t-target-h|Target flight time in hours]] · [[ss-dod|Depth of discharge]]

**Produced by.** `app/services/powertrain_solution_space_service.py:377` — `compute_solution_space`

**Consumed by.**

- in this graph: [[ss-cap-mah|Minimum battery capacity]]
- outside it: `app/services/powertrain_solution_space_service.py:388` · `app/services/powertrain_solution_space_service.py:440` · `app/services/powertrain_solution_space_service.py:494` · `frontend/components/workbench/PowertrainTab.tsx:587` · `frontend/components/workbench/PowertrainTab.tsx:1143`

**Source.** 🟡 PARTIAL

> E = P x t is elementary. Sadraey (2013), §8.7 gives the only class-specific anchor found: 'A typical 2-hp electric motor weighs about 300 g. Operating it for 15 minutes requires about 400 g of battery.' No source states the /DoD divisor.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
E = P x t
```

**⚠️ Divergence from the source.** The whole mission is modelled as constant cruise power — no takeoff, no climb, no reserve. Lennon (Basics of R/C Model Aircraft Design, Ch. 18) explicitly notes that level-flight figures are minimums and that ~25% should be added for climb and maneuvers; the energy budget that produces the capacity floor excludes the highest-power phase of the flight. The DoD divisor is separately unattributed (see ss-dod).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The whole mission is modelled as constant cruise power — no takeoff, no climb, no reserve. The energy that produces the capacity floor therefore excludes the highest-power phase of the flight.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `module docstring: "Energy  E_Wh = P_elec(V_cruise) · (t_target_h) / DoD"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
