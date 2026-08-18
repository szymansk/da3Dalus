---
name: atmosphere-scale-height-perf
symbol: 8500.0
kind: constant
unit: m
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Isothermal atmosphere scale height (performance)

**Definition.** Scale height of the exponential (isothermal) atmosphere approximation.

**Value.** `8500.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:348` — `_air_density`

**Consumed by.**

- in this graph: [[air-density-perf|Air density at altitude (performance)]]
- outside it: `app/services/powertrain_performance.py:385` · `app/services/powertrain_performance.py:524` · `app/services/powertrain_performance.py:695`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz / aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**The source states it as.**

```
Sadraey (2013) Eq. 4.94a gives the ISA density ratio as sigma = (1 - 6.873e-6 h)^4.26 for 0 <= h <= 36,000 ft (h in ft) — a power law from the troposphere lapse rate, not an exponential. Anderson 6e §1.9 gives only the hydrostatic equation dp/dy = -rho g, from which an isothermal exponential follows, but no scale-height value is stated.
```

**⚠️ Divergence from the source.** The 8500 m scale height itself is unattributed in every vault consulted. Neither authority uses an exponential atmosphere at all: Sadraey's Eq. 4.94a is a 4.26-power lapse-rate law, and Anderson stops at the hydrostatic differential equation. The exponential form is a different model, not a restatement of either.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic number with no explanation, and duplicated verbatim at powertrain_sizing_service.py:52 (two independent producers of air density).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `NO_SOURCE_FOUND — docstring says only "ISA air density approximation [kg/m³]"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
