---
name: s_to_ground
symbol: s_TO_ground
kind: quantity
unit: m
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
  - flag/divergence
---

# Takeoff ground roll

**Definition.** Distance from standstill to lift-off on a runway takeoff.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return _C_TO * wing_loading / (rho * g * cl_max_to * t_over_w)
```

**Inputs.**

- [[c_to_roskam|Roskam takeoff ground-roll coefficient]]
- [[wing_loading_fl|Wing loading (field length)]]
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*
- [[g_gravity|Standard gravity]]
- [[cl_max_to_fl|Takeoff CL_max (field length)]]  — *⊣ limit*
- [[t_over_w_fl|Thrust-to-weight (field length)]]

**Produced by.** `app/services/field_length_service.py:203` — `_compute_s_to_ground`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Obstacle-corrected distance` · `Takeoff distance over 50 ft` · `Bungee partial ground roll`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_field_lengths:424` · `_compute_s_to_bungee_partial:225` · `FieldLengthRead.s_to_ground_m:439`

**Source.** 🟡 PARTIAL

> Form SOURCED: Scholz 05_PreliminarySizing §5.2 simplified ground roll, s_TOG = (1/(rho*CL_LOF)) * (g*m_MTO^2/S_W)/(T_TO/(m_MTO*g)) - i.e. proportional to (W/S)/(rho*CL_max*(T/W)), exactly the code's structure. Exact counterpart Sadraey Eq. 4.66 (log form with C_DG = C_D,TO - mu*C_L,TO, Eq. 4.67a). Coefficient 1.21 only PARTIAL (see c_to_roskam).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
s_TOG proportional to (W/S) / (rho * g * CL_max,TO * (T/W))
```

**⚠️ Divergence from the source.** The code drops everything Sadraey Eq. 4.66 keeps: rolling friction mu, high-lift and landing-gear drag (C_Do_LG = 0.006-0.012, C_Do_HLD_TO = 0.003-0.008 per Sadraey Eq. 4.69a), runway slope and wind. Scholz notes the simplification is only valid when drag and friction are negligible against thrust - defensible for a high-T/W model, not for a heavy UAV on grass.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"Takeoff ground roll (Roskam §3.4 energy method). s_TO = C_TO · (W/S) / (ρ · g · CL_max_TO · (T/W))"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
