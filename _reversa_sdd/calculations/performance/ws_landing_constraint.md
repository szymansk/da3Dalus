---
name: ws_landing_constraint
symbol: (W/S)_max,LDG
kind: quantity
unit: N/m^2
cluster: perf-matching
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Landing constraint W/S_max

**Definition.** Maximum wing loading that still meets the landing field-length target.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return (s_runway * rho * cl_max_l) / (_K_LDG_HARD * _K_LDG_50FT)
```

**Inputs.**

- [[mode_default_s_runway|Mode default field length]]  — *⤵ fallback*
- [[cl_max_l_mc|Landing CL_max (matching chart)]]  — *⤵ fallback*
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*
- [[k_ldg_hard|Landing ground-roll coefficient]]
- [[k_ldg_50ft|Landing 50-ft obstacle factor]]

**Produced by.** `app/services/matching_chart_service.py:341` — `_landing_constraint`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `ws_ldg_max:850` · `constraints_raw 'Landing':900` · `MatchingChartResponse.constraints`

**Source.** 🟡 PARTIAL

> Form SOURCED: the landing requirement is a vertical W/S limit. Scholz 05_PreliminarySizing §5.1 / Loftin: m_ML/S_W = k_L*sigma*CL_max,L*s_LFL with k_L = 0.107 kg/m^3, then divided by m_ML/m_MTO. Sadraey's stall-speed counterpart is Eq. 4.31. The code's constants (K_LDG_HARD, K_LDG_50FT) are not from either source.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
m_ML/S_W = k_L * sigma * CL_max,L * s_LFL, k_L = 0.107 kg/m^3
```

**⚠️ Divergence from the source.** Inverting the sourced ground-roll relation gives W/S_max = s*rho*CL_max,L*mu*g/(k^2*k_50ft); the code omits mu and g entirely. That is exactly why the `g` parameter sits unused 'for symmetry' - it is the term that belongs there (ADR 0021 dead parameter, but the fix is to use it, not delete it). Separately the belly-land case bypasses the helper by hardcoding float('inf').

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** k_L = 0.107 is a jet-transport statistical fit; the code's substitute constants are a Cessna 172N fit. Neither is valid at 0.5-15 kg (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The `g` parameter is declared and documented as "(unused; kept for symmetry with other helpers)" — dead parameter (ADR 0021); the belly-land case bypasses the helper entirely by hardcoding float('inf') at line 848.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"From Roskam §3.4: W/S_max = s_LDG_50ft · ρ · CL_max_LDG / (K_LDG_HARD · K_LDG_50FT)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
