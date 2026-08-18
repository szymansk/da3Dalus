---
name: qprop-rpm-free
symbol: rpm_free
kind: quantity
unit: rpm
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Free-running RPM

**Definition.** Upper bracket of the RPM search: the no-load speed where back-EMF equals terminal voltage and current is zero.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
rpm_free = V_terminal * kv_si * 60.0 / (2.0 * math.pi)
```

**Inputs.**

- [[curve-v-terminal|Motor terminal voltage]]
- [[motor-kv-si|Motor speed constant in SI]]

**Produced by.** `app/services/powertrain_performance.py:540` — `solve_qprop_operating_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Solved operating RPM`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_performance.py:552`

**Source.** 🟢 SOURCED

> Drela, 'DC Motor / Propeller Matching', §1.1 (V = iR + Omega/Kv at i = 0) and Roxxy Motoren-Fibel, Ch. 1, pp. 15-16: 'No-load RPM = KV x Battery Voltage (volts)'.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
RPM_no-load = KV x V  (equivalently Omega = V * Kv_si at i = 0)
```

**Cited in the code itself.** `# Upper RPM bound: free-running speed (I=0) where back-EMF == V_terminal.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
