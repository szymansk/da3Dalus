---
name: cl-max-landing-flap
symbol: CL_max,flap
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Swept flapped CL_max

**Definition.** Maximum lift coefficient found by sweeping alpha with flaps deployed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if cl > cl_max_flap:
    cl_max_flap = cl
    cm_at_cl_max = cm
    alpha_at_cl_max = float(alpha)
```

**Inputs.**

- [[flap-alpha-sweep|Flap CL_max alpha sweep]]  — *⊣ limit*
- [[flap-default-deflection|Default flap deflection]]  — *⤵ fallback*

**Produced by.** `app/services/elevator_authority_service.py:890` — `_run_flap_analysis`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Landing stall alpha` · `Landing CL_max` · `Flap-induced pitching moment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:646,654`

**Source.** 🟢 SOURCED

> Scholz HAW Hamburg, 08_HighLift §8.2 and 05_PreliminarySizing §5.1 — C_L,max,L is the maximum of the lift curve in the landing configuration; Table 5.1 gives the expected magnitude by aircraft type (single-engine prop 1.6–2.3). Determining it by sweeping alpha to the maximum is the direct numerical realisation of that definition.
>
> — via `aircraft-design-scholz + aerosandbox-expert`

**The source states it as.**

```
C_L,max,L = max over α of C_L(α) with flaps at landing deflection
```

**⚠️ Divergence from the source.** Sound in principle. Two practical caveats: the 1° grid quantises the maximum and its alpha, and the sweep terminates at 19° (see flap-alpha-sweep). AeroSandbox documents AeroBuildup's extreme-attitude predictions as 'order-of-magnitude correct rather than highly accurate', so the CL_max it returns should not be presented at the precision of a measured value. cl_max_flap is initialised to −inf, so a failed sweep silently yields −inf rather than an error.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Initialised to -inf (line 876); AeroBuildup is inviscid-ish strip theory with no stall model, so a monotonically increasing CL curve returns the sweep endpoint as 'CL_max' — an undeclared substitution.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
