---
name: q_dynamic_pressure
symbol: q
kind: quantity
unit: Pa
cluster: perf-matching
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Dynamic pressure

**Definition.** Dynamic pressure at the relevant flight speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
q = 0.5 * rho * v_cruise * v_cruise
```

**Inputs.**

- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*
- [[v_cruise_resolved|Resolved cruise speed]]

**Produced by.** `app/services/matching_chart_service.py:372` — `_cruise_constraint`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `tw_cruise_constraint:374` · `tw_climb_constraint:412` · `tw_vertical_climb:584`

**Source.** 🟢 SOURCED

> Sadraey 2013 Eq. 4.36/4.37 §4.3.3.1: D = 0.5*rho*V^2*S*C_D, L = 0.5*rho*V^2*S*C_L.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
q = 0.5*rho*V^2
```

**Cited in the code itself.** `# with q = ½·ρ·V_cruise²`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
