---
name: combo-flight-time-h
symbol: flight_time_h
kind: quantity
unit: h
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Estimated flight time (hours)

**Definition.** Endurance in hours: usable capacity divided by cruise current.

**Formula — as the code writes it.**

```
flight_time_h = (capacity_ah / cruise_current_a) * 0.8 if cruise_current_a > 0 else 0
```

**Inputs.** [[combo-capacity-ah|Battery capacity in amp-hours]] · [[combo-cruise-current|Cruise current draw]] · [[usable-capacity-fraction-sizing|Usable capacity fraction (sizing)]]

**Produced by.** `app/services/powertrain_sizing_service.py:256` — `_evaluate_motor_battery_combo`

**Consumed by.**

- in this graph: [[combo-flight-time-min|Estimated flight time]]
- outside it: `app/services/powertrain_sizing_service.py:257`

**Source.** 🟡 PARTIAL

> Sadraey (2013), §8.7 provides only an order-of-magnitude anchor for electric endurance ('a typical 2-hp electric motor ... operating it for 15 minutes requires about 400 g of battery'); no source states the constant-current endurance model t = (capacity_Ah / I) x DoD.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
t = capacity_Ah / I_draw (constant-current), scaled by usable fraction
```

**⚠️ Divergence from the source.** The constant-current model assumes cruise current is drawn for the whole flight, with no takeoff or climb allowance and no voltage sag over the discharge. Sadraey's §8.7 statement is a full-power figure, so it cannot validate a cruise-only budget.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Constant-current endurance model — assumes cruise current is drawn for the whole flight, with no takeoff/climb allowance and no voltage sag over discharge.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
