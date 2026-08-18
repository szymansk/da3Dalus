---
name: tw_cruise_constraint
symbol: (T/W)_cruise
kind: quantity
unit: dimensionless
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

# Cruise constraint T/W

**Definition.** T/W required for level cruise at V_cruise.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return q * cd0 / ws + ws * k / q
```

**Inputs.**

- [[ws_range_mc|W/S sweep vector]]
- [[v_cruise_resolved|Resolved cruise speed]]
- [[ar_resolved|Resolved aspect ratio]]  — *⤵ fallback*
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*

**Produced by.** `app/services/matching_chart_service.py:374` — `_cruise_constraint`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `cruise_tw:853` · `constraints_raw 'Cruise':914` · `MatchingChartResponse.constraints`

**Source.** 🟢 SOURCED

> Sadraey 2013 Eq. 4.47 §4.3.3.1 (sadraey-maximum-speed-jet-aircraft): (T/W)_Vmax = (1/sigma)[ rho_o*V^2*C_Do/(2*(W/S)) + (2K/(rho*V^2))*(W/S) ]; compact form Eq. 4.48. With q = 0.5*rho*V^2 and sigma = 1 this is exactly q*CD0/(W/S) + (W/S)*K/q.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
(T/W) = q*C_Do/(W/S) + (W/S)*K/q, K = 1/(pi*e*AR)
```

**⚠️ Divergence from the source.** The code drops the 1/sigma altitude factor, making the constraint sea-level-only. Legitimate given the module has no altitude model, but undeclared. Also: the docstring credits 'Anderson 6e §6.7 / Scholz §5.4'; the exact equation is Sadraey Eq. 4.47. Note the source treats this as the MAXIMUM-SPEED constraint (V_max ~ 1.2-1.3*V_cruise, since cruise runs at 75-80% thrust), whereas the code applies it at V_cruise - so the code's line is less demanding than the source's.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"T/W required for level cruise at V_cruise — Anderson 6e §6.7 / Scholz §5.4. T/W = q·CD0/(W/S) + (W/S)/(q·π·e·AR)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
