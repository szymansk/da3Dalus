---
name: curve-diameter-m
symbol: D_m
kind: quantity
unit: m
cluster: powertrain
user_visible: false
source_status: PARTIAL
---

# Propeller diameter in metres

**Definition.** Propeller diameter converted from the polar header's inch value.

**Formula — as the code writes it.**

```
D_m = request.propeller_diameter_in * 0.0254
```

**Inputs.** [[inch-to-metre|Inch-to-metre conversion factor]] · [[request-propeller-diameter-in|Propeller diameter input]]

**Produced by.** `app/services/powertrain_performance.py:646` — `compute_performance_curve`

**Consumed by.**

- in this graph: [[curve-advance-ratio|Advance ratio per velocity sample]] · [[curve-p-shaft|Shaft power per velocity sample]] · [[curve-thrust|Thrust per velocity sample]]
- outside it: `app/services/powertrain_performance.py:733` · `app/services/powertrain_performance.py:748` · `app/services/powertrain_performance.py:756` · `app/services/powertrain_performance.py:719`

**Source.** 🟡 PARTIAL

> Roxxy Motoren-Fibel, Ch. 1, pp. 6-7 (propeller sizes are Diameter x Pitch in inches). Unit conversion only; no engineering content to attribute.
>
> — via `rc-aircraft-designer`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
