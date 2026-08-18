---
name: motor-eta
symbol: eta_motor
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Motor + gearbox efficiency

**Definition.** Combined motor and gearbox electrical-to-shaft efficiency, from the datasheet percentage when available, else the 0.85 default.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if self.efficiency_pct is not None: return self.efficiency_pct / 100.0 ; return _DEFAULT_ETA_MOTOR
```

**Inputs.**

- [[motor-efficiency-pct-input|Datasheet motor efficiency]]
- [[default-eta-motor-perf|Default motor efficiency (performance module)]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_performance.py:147` — `MotorSpec.eta_motor`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Shaft power ceiling`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:663` · `app/services/powertrain_performance.py:793`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, Ch. 3, pp. 28-29 (hobby BLDC peak efficiency 75-85%, Roxxy 80-85%) for the fallback value; Drela, 'DC Motor / Propeller Matching', §1.2 for the definition eta_m = P_shaft/(V*I).
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta_m = P_shaft / (V*I)  (Drela §1.2)
```

**⚠️ Divergence from the source.** Drela's model makes eta_m a FUNCTION of the operating point: eta_m = [1 / (1 + i*R*Kv/Omega)] * (Kv/Kq). The code's MotorSpec.eta_motor is a single scalar (datasheet percentage or 0.85), constant across the whole velocity sweep. The two differ most at low speed / high current, exactly where the power ceiling binds.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
