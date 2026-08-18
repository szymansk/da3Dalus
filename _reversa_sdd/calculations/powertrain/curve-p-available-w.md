---
name: curve-p-available-w
symbol: p_available_w
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
---

# Reported power ceiling

**Definition.** The electrical power ceiling returned to the client, rounded to two decimals.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
p_available_w=round(p_available_elec, 2)
```

**Inputs.**

- [[curve-p-available-elec|Electrical power ceiling]]  — *⤵ fallback*

**Produced by.** `app/services/powertrain_performance.py:800` — `compute_performance_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/api/v2/endpoints/aeroplane/powertrain_performance.py:255` · `app/tests/test_powertrain_performance_endpoint.py:264`

**Source.** 🟡 PARTIAL

> Same as curve-p-available-elec: RC-Network Wiki 'Motorsteller' on current ratings; P = V I elementary. Rounding is presentation only.
>
> — via `rc-aircraft-designer`

**⚠️ Anomaly.** No UI consumer (notes F1).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Electrical power ceiling (min of motor + battery limits) [W]"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
