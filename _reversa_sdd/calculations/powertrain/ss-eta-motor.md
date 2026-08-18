---
name: ss-eta-motor
symbol: eta_motor
kind: parameter
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Motor efficiency (solution space)

**Definition.** Flat motor efficiency assumed for the whole envelope.

**Value.** `0.85`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:41` — `SolutionSpaceAssumptions.eta_motor`

**Consumed by.**

- in this graph: [[ss-p-cruise-hi-e|Electrical cruise power at high prop efficiency]] · [[ss-p-cruise-lo-e|Electrical cruise power at low prop efficiency]] · [[ss-p-cruise-mid|Electrical cruise power (mid band)]] · [[ss-p-elec|Electrical power required]] · [[ss-p-top-hi-e|Electrical peak power at high prop efficiency]] · [[ss-p-top-lo-e|Electrical peak power at low prop efficiency]] · [[ss-p-top-mid|Electrical peak power (mid band)]]
- outside it: `app/services/powertrain_solution_space_service.py:360` · `app/services/powertrain_solution_space_service.py:361`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 3, pp. 28-29: 'For typical hobby BLDC motors, peak efficiency typically falls between 75-85% in the flight-typical operating range. Roxxy motors achieve high efficiency levels of 80-85%.'
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_m,peak = 0.75-0.85 (hobby BLDC)
```

**⚠️ Divergence from the source.** 0.85 is the top of the source's PEAK band. The source further states that peak efficiency occurs mid-range at a power 'significantly lower than the rated power', and Drela §1.2 gives the closed form eta_m = [1/(1 + i R Kv/Omega)](Kv/Kq) showing efficiency falls as current rises. The code holds 0.85 constant from cruise to top speed, i.e. exactly where the sources say it degrades most.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Fourth declaration of 0.85 (notes F3). Assumed constant from cruise to top speed, where real motor efficiency falls off sharply with current.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Motor efficiency (brushless outrunner typical)" — NO_SOURCE_FOUND`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
