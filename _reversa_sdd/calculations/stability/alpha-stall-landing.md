---
name: alpha-stall-landing
symbol: α_stall,landing
kind: quantity
unit: deg
cluster: stability
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - flag/divergence
---

# Landing stall alpha

**Definition.** Angle of attack at which the flapped CL_max occurs; the operating point at which Cm_δe is then evaluated.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
alpha_at_cl_max = float(alpha)
```

**Inputs.**

- [[cl-max-landing-flap|Swept flapped CL_max]]  — *⊣ limit*
- [[flap-alpha-sweep|Flap CL_max alpha sweep]]  — *⊣ limit*
- [[stall-alpha-fallback|Stall alpha fallback]]  — *⤵ fallback*

**Produced by.** `app/services/elevator_authority_service.py:893` — `_run_flap_analysis`

**Consumed by.**

- in this graph: `Baseline pitching moment (zero deflection)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:646,658,683 (op_stall_landing alpha)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.4 — the critical elevator case must be evaluated at the actual flight condition, and the tail angle there follows Eq. 12.91, α_h_TO = α_TO(1 − dε/dα) + i_h − ε_o; evaluating the control derivative at the condition where CL_max occurs is the correct realisation of that requirement. Scholz 05_PreliminarySizing §5.1 ties V_S,L to C_L,max,L at the same point.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Critical condition evaluated at the stall/approach point, not at an arbitrary alpha (Sadraey §12.5.4 Eq. 12.91)
```

**⚠️ Divergence from the source.** The code correctly re-evaluates the baseline and TE-UP runs at this alpha (the 'Scholz B2 fix'), which is the right structure. It does not apply Eq. 12.91's tail-angle check (Sadraey §12.5.5 steps 20–21: verify the horizontal tail itself does not stall, keeping it within 2° of its stall angle) — so a solution can be reported at a condition where the tail has stalled.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `Scholz B2 fix: returns the alpha at which CL_max is achieved (α_stall_landing)
so the caller can re-run the baseline and TE-UP AeroBuildup runs at that alpha.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
