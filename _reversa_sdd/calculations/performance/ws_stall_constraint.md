---
name: ws_stall_constraint
symbol: (W/S)_max,stall
kind: quantity
unit: N/m^2
cluster: perf-matching
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Stall constraint W/S_max

**Definition.** Maximum wing loading that keeps the clean stall speed at or below the target.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return 0.5 * rho * v_s_target * v_s_target * cl_max_clean
```

**Inputs.**

- [[mode_default_v_s_target|Mode default stall-speed target]]  — *⤵ fallback*
- [[cl_max_clean_mc|Clean CL_max (matching chart)]]  — *⊣ limit*
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*

**Produced by.** `app/services/matching_chart_service.py:439` — `_stall_constraint`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `ws_stall_max:868` · `constraints_raw 'Stall':944` · `MatchingChartResponse.constraints`

**Source.** 🟢 SOURCED

> Sadraey 2013 Eq. 4.30/4.31 §4.3.2 (landing-field-length-constraint): L = W = 0.5*rho*V_s^2*S*CL_max (4.30), hence (W/S)_Vs = 0.5*rho*V_s^2*CL_max (4.31). Acceptable region is to the LEFT of this vertical line.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
(W/S)_Vs = 0.5*rho*V_s^2*CL_max
```

**⚠️ Divergence from the source.** Citation error only: hover_text credits 'Anderson §5.4'; the equation is Sadraey Eq. 4.31. The code's use of clean CL_max and sea-level rho both match the source's explicit guidance (Scholz: sea level is the conservative choice; Sadraey: the limit is met flap-up, flaps only relax it).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"L = ½·ρ·V_s²·S·CL_max_clean = W → W/S_max = ½·ρ·V_s²·CL_max_clean" ; hover_text:953 cites "Anderson §5.4"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
