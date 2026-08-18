---
name: combo-cruise-current
symbol: cruise_current_a
kind: quantity
unit: A
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Cruise current draw

**Definition.** Battery current in level cruise: required power over nominal pack voltage. Also the value the ESC must match.

**Formula — as the code writes it.**

```
cruise_current_a = actual_cruise_power / voltage if voltage > 0 else 999
```

**Inputs.** [[combo-cruise-power|Estimated cruise power]] · [[combo-battery-voltage|Resolved battery voltage (sizing)]]

**Produced by.** `app/services/powertrain_sizing_service.py:251` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: [[combo-flight-time-h|Estimated flight time (hours)]]
- outside it: `app/services/powertrain_sizing_service.py:252` · `app/services/powertrain_sizing_service.py:256` · `app/services/powertrain_sizing_service.py:259`

**Source.** 🟡 PARTIAL

> I = P/V is elementary (Drela, 'DC Motor / Propeller Matching' §1.2 uses P_in = V*I). RC-Network Wiki 'Nennspannung' supplies V_nom. No source prescribes sizing the ESC against cruise current at nominal voltage.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
I = P / V
```

**⚠️ Divergence from the source.** RC-Network Wiki 'Motorsteller' identifies maximum continuous current as the sizing specification for the ESC, and the peak case for an RC aircraft is full-throttle climb, not cruise. The code sizes the ESC against the cruise point at nominal (not sagged) voltage, which is the least demanding case in the flight envelope.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The 999 A sentinel is a magic number with no explanation, and the branch is unreachable because line 230 already returns None when voltage <= 0. Separately, the ESC is sized against CRUISE current at NOMINAL voltage (line 259), never against a climb/full-throttle case at sag voltage.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
