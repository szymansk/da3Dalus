---
name: at-over-a-ratio
symbol: a_t/a
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: PARTIAL
---

# Tail-to-wing lift-curve-slope ratio

**Definition.** Ratio of horizontal-tail lift-curve slope to wing lift-curve slope, hardcoded to unity.

**Value.** `1.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:121` — `_alpha_vh`

**Consumed by.**

- in this graph: [[alpha-vh|Tail efficiency factor]] · [[dsm-dsh|SM sensitivity to horizontal tail area]]
- outside it: `app/services/sm_sizing_service.py:122` · `app/services/sm_sizing_service.py:161,162 (_dsm_dsh, second independent literal)`

**Source.** 🟡 PARTIAL

> The ratio is a real quantity in the literature: Sadraey (Wiley 2013) §6.7.4 Eq. 6.57 gives the 3-D tail lift-curve slope C_Lα_h = C_lα_h/(1 + C_lα_h/(π·AR_h)), i.e. a_t is an explicit function of tail aspect ratio; Sadraey §6.7 places tail AR at 4–6 versus typical wing AR 6+. No source states a_t/a = 1.0.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_Lα_h = C_lα_h / (1 + C_lα_h/(π·AR_h))  (Sadraey Eq. 6.57) — evaluated separately for tail and wing
```

**⚠️ Divergence from the source.** The code assumes unity. Eq. 6.57 makes a_t/a < 1 whenever AR_h < AR_w, which is the normal case (Sadraey: tail AR 4–6, PreSTo: horizontal tail AR 4.5–5.5). The code's own TODO at sm_sizing_service.py:121 acknowledges this. Declared twice as separate literals (:121 and :161).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** An unvalidated assumption of 1.0 for a ratio that is typically 0.7–0.9 (the tail has lower AR); the TODO acknowledges it. Declared twice as separate literals (lines 121 and 161) rather than once.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `at_over_a = 1.0  # TODO: split tail/wing CL_α when separable`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
