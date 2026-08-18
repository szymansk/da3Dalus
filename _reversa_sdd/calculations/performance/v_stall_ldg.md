---
name: v_stall_ldg
symbol: V_S0
kind: quantity
unit: m/s
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

# Landing-configuration stall speed

**Definition.** Stall speed in landing configuration, falling back to the clean V_S.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_stall_ldg: float = float(aircraft.get("v_s0_mps") or v_stall)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:368` — `compute_field_lengths`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Approach speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_v_app:370`

**Source.** 🟢 SOURCED

> Scholz 05_PreliminarySizing §5.1 (maximum-lift-coefficient-landing): V_S,L = sqrt(2*m_ML*g/(rho*S_W*CL_max,L)); Sadraey Eq. 4.30/4.31.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
V_S,L = sqrt(2*(W/S)/(rho*CL_max,L))
```

**Cited in the code itself.** `# gh-526 (see v_stall_to)`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
