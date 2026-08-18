---
name: curve-p-available-elec
symbol: P_available_elec
kind: quantity
unit: W
cluster: powertrain
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Electrical power ceiling

**Definition.** The binding electrical power limit: the smaller of the motor's estimated burst-power ceiling and the battery's C-rate discharge ceiling. If both are unknown it is re-derived from the pack voltage times a current fallback.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_available_elec = min(p_motor_max_elec, p_battery_max) ; if math.isinf(p_available_elec): p_available_elec = V_bat * (battery.max_current_a if not math.isinf(battery.max_current_a) else 100.0)
```

**Inputs.**

- [[motor-max-electrical-power|Motor maximum electrical input power (estimated)]]  — *⊣ limit*
- [[battery-max-continuous-discharge|Battery maximum continuous discharge power]]
- [[curve-v-bat|Battery voltage used for the curve]]  — *⊣ limit*
- [[battery-max-current|Battery maximum continuous discharge current]]
- [[battery-current-fallback-100a|Unknown-battery current fallback]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_performance.py:653` — `compute_performance_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Reported power ceiling` · `Shaft power ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:663` · `app/services/powertrain_performance.py:800`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Motorsteller' establishes that the current capacity of each component is the binding specification and that continuous and peak ratings must be distinguished. The min() composition of a motor limit and a battery limit is engineering common sense, not a cited method.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P = V I (elementary)
```

**⚠️ Divergence from the source.** No source supports the both-limits-unknown fallback branch. The code comment claims a 'conservative 500 W placeholder' but computes V_bat x 100 A, which is 1110 W at 3S and 2220 W at 6S.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The comment says "use a conservative 500 W placeholder" but the code computes V_bat * 100.0 A, which for a 3S pack is 1110 W and for a 6S pack 2220 W. The comment describes a value that does not exist in the code.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Take the tighter constraint / # Both limits unknown — use a conservative 500 W placeholder`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
