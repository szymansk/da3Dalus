---
name: motor-continuous-electrical-power
symbol: P_motor_cont_elec
kind: quantity
unit: W
cluster: powertrain
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/partial
  - flag/anomaly
  - flag/divergence
---

# Motor continuous electrical input power (estimated)

**Definition.** Estimated continuous electrical input power from the continuous current rating (falling back to burst current) at loaded pack voltage.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
i_cont = self.continuous_current_a or self.max_current_a ; if i_cont is None: return float("inf") ; return i_cont * _VOLTS_PER_LIPO_CELL * self.cells_lipo_max
```

**Inputs.**

- [[motor-continuous-current-input|Motor continuous current rating]]
- [[motor-max-current-input|Motor burst current limit]]  — *⊣ limit*
- [[volts-per-lipo-cell|Loaded LiPo cell voltage]]
- [[motor-cells-lipo-max-input|Maximum LiPo cell count]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_performance.py:171` — `MotorSpec.continuous_electrical_power_w`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Motorsteller': 'The most important specification: maximum continuous current capacity determines controller size and weight.' P = V*I is elementary.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
P_cont = I_cont * V
```

**⚠️ Divergence from the source.** The source names the continuous rating as the governing specification; the code computes it and then never uses it (dead), sizing instead off the burst rating. That inverts the source's priority.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** NO CONSUMER ANYWHERE. grep for continuous_electrical_power_w across the whole repo (py/ts/tsx) returns only the definition at line 162 — not even a test. Complete but unreachable (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `docstring: "Derived from continuous_current_a × 3.7 V/cell × cells_lipo_max. Tagged as ESTIMATED."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
