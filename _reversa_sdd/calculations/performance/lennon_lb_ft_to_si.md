---
name: lennon_lb_ft_to_si
symbol: c_WCL
kind: constant
unit: claimed N/m^4.5 per lb/ft^4.5
cluster: perf-matching
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Lennon WCL conversion factor

**Definition.** Factor applied to convert Lennon's lb/ft^4.5 WCL into an SI-ish quantity.

**Value.** `47.88`

**Formula — as the code writes it.**

```
_LENNON_LB_FT_TO_SI: float = 47.88
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/matching_chart_service.py:479` — `_LENNON_LB_FT_TO_SI`

**Consumed by.**

- in this graph: [[wcl_ws_max|WCL-derived W/S ceiling]]
- outside it: `_wcl_constraint:528`

**Source.** 🔴 NO SOURCE FOUND

> No source. 47.88 is exactly the lbf/ft^2 -> Pa conversion (47.8803 Pa per lbf/ft^2), which is a PRESSURE conversion.
>
> — via `aircraft-design-scholz (no coverage)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Dimensionally invalid. It is applied to a wing-cube-loading value whose real unit is oz/ft^3 (weight / area^1.5), not lbf/ft^2. The code's own comment admits the unit is wrong and states the exponent inconsistently (N/m^3 vs N/m^4.5) within the same paragraph, then proceeds anyway. Nothing downstream of this factor can be trusted numerically.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 47.88 is the lbf/ft²→Pa factor being applied to lb/ft^4.5; the comment itself admits the unit is wrong and even the exponent of WCL is stated inconsistently (N/m^3 vs N/m^4.5) in the same paragraph.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"1 lb = 4.4482 N; 1 ft^2 = 0.09290 m^2; so 1 lb/ft^3 (used as a stand-in here) isn't quite the right unit — WCL has units N/m^3 in SI, lb/ft^4.5 in Lennon. Numerically: WCL[lb/ft^4.5] · 47.88 ≈ WCL[N/m^4.5] -- but the standard practice is to apply WCL_SI = ρ · g · 0.5 · CL · V^? — instead we use the pragmatic conversion factor"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
