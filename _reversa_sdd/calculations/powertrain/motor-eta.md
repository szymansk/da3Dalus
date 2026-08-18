---
name: motor-eta
symbol: eta_motor
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Motor + gearbox efficiency

**Definition.** Combined motor and gearbox electrical-to-shaft efficiency, from the datasheet percentage when available, else the 0.85 default.

**Formula — as the code writes it.**

```
if self.efficiency_pct is not None: return self.efficiency_pct / 100.0 ; return _DEFAULT_ETA_MOTOR
```

**Inputs.** [[motor-efficiency-pct-input|Datasheet motor efficiency]] · [[default-eta-motor-perf|Default motor efficiency (performance module)]]

**Produced by.** `app/services/powertrain_performance.py:147` — `MotorSpec.eta_motor`

**Consumed by.**

- in this graph: [[curve-p-shaft-max|Shaft power ceiling]]
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
