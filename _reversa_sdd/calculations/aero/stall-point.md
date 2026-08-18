---
name: stall-point
kind: quantity
unit: mixed (deg, -, -)
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Stall point

**Definition.** First post-CLmax sweep point where CL drops and CD rises simultaneously.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if cl[i] < cl[i - 1] and cd[i] > cd[i - 1]: i_stall = i
```

**Inputs.**

- [[cl-values|Lift coefficient array]]
- [[cd-values|Drag coefficient array]]
- [[max-cl-point|Maximum lift coefficient point]]  — *⊣ limit*

**Produced by.** `app/services/analysis_service.py:173` — `_find_stall_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Characteristic points dict`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `alpha-sweep PNG` · `_render_summary_panel 'Stall-Indiz'` · `copilot_tools 'stall'`

**Source.** 🟢 SOURCED

> Anderson 6e §4.x 'Airfoil Stall and Advanced Aerodynamic Phenomena' ('c_l reaches maximum at α_stall, then decreases precipitously; flow separation … large increase in drag')
>
> — via `aerodynamics-expert`

**The source states it as.**

```
stall: α > α_stall where dc_l/dα < 0 and c_d rises sharply due to separation
```

**⚠️ Divergence from the source.** The code's test (CL drop AND CD rise on consecutive grid points) matches Anderson's qualitative description well. Anderson also distinguishes leading-edge stall (sharp peak) from trailing-edge stall (soft bend-over) — the soft case may never trip the two-condition test on a coarse grid.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
