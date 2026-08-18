---
name: end_battery_deviation
symbol: dev
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Battery-mass deviation

**Definition.** Relative gap between predicted and user-supplied battery component mass.

**Formula — as the code writes it.**

```
deviation = abs(predicted_kg - battery_mass_kg) / battery_mass_kg
```

**Inputs.** [[end_battery_mass_predicted|Capacity-implied battery mass]] · [[end_battery_component_mass|Battery component mass]] · [[end_battery_dev_threshold|Battery-mass deviation threshold]]

**Produced by.** `app/services/endurance_service.py:189` — `_check_battery_mass_consistency`

**Consumed by.**

- outside it: `EnduranceCard.tsx warnings list`

**Source.** 🔴 NO SOURCE FOUND

> Ratio is definitional; the 30% alert threshold is unsourced (see end_battery_dev_threshold).
>
> — via `rc`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Compares a predicted mass built on a contested E* (180 vs 153 Wh/kg) against a measured component mass. An 18% disagreement in E* alone consumes more than half the 30% alert budget, so the check can fire on the constant rather than on the design.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
