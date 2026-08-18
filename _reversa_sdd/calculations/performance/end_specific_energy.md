---
name: end_specific_energy
symbol: E*
kind: constant
unit: Wh/kg
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
---

# Default pack specific energy

**Definition.** Pack-level LiPo energy density used to predict battery mass from capacity.

**Value.** `180.0`

**Formula — as the code writes it.**

```
DEFAULT_BATTERY_SPECIFIC_ENERGY_WH_PER_KG = 180.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:58` — `DEFAULT_BATTERY_SPECIFIC_ENERGY_WH_PER_KG`

**Consumed by.**

- in this graph: [[end_battery_mass_predicted|Capacity-implied battery mass]]

**Source.** 🟡 PARTIAL

> Hepperle, M., 'Electric Flight - Potential and Limitations', NATO STO-MP-AVT-209 (2012) — real, specific, correctly named in the module header. Counter-reference: RC-Network Wiki 'Energiedichte' lists LiPo at 0.55 MJ/kg = 153 Wh/kg.
>
> — via `rc`

**The source states it as.**

```
E* = 180 Wh/kg (pack level)
```

**⚠️ Divergence from the source.** The code's own distinction (pack ~180 vs cell ~220 Wh/kg) is exactly the right distinction to draw, but the RC community reference puts LiPo at 153 Wh/kg — below the code's PACK figure, let alone its cell figure. 180 Wh/kg at pack level is ~18% more optimistic than the RC-Network number and should be reconciled or explicitly justified as a modern high-discharge chemistry. Duplicated at design_assumption.py:94.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated as PARAMETER_DEFAULTS['battery_specific_energy_wh_per_kg'] = 180.0 (design_assumption.py:94, comment 'Hepperle 2012').

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"Pack-level E* (≈ 180 Wh/kg LiPo) not cell-level (220 Wh/kg)"; module header cites "Hepperle 2012: Electric endurance with constant mass"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
