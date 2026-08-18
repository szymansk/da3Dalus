---
name: request-throttle
symbol: throttle
kind: parameter
unit: dimensionless (0..1]
cluster: powertrain
user_visible: true
source_status: SOURCED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
---

# Throttle fraction

**Definition.** User-supplied throttle setting, applied linearly to both the fixed RPM and the QPROP terminal voltage.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:223` — `PowertrainPerformanceRequest.throttle`

**Consumed by.**

- in this graph: `Fixed operating RPM (non-QPROP branch)` · `Motor terminal voltage`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:643` · `app/services/powertrain_performance.py:702` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:251`

**Source.** 🟢 SOURCED

> Roxxy Motoren-Fibel, ESC control chapter (PWM switching): duty cycle maps linearly to effective terminal voltage, 0-100%.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
V_eff = duty x V_bat
```

**Cited in the code itself.** `field description: "Throttle fraction (0..1]"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
