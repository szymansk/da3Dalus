---
name: alpha-vh
symbol: alpha_VH
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Tail efficiency factor

**Definition.** Dimensionless tail contribution factor combining lift-slope ratio, downwash and area ratio; used in the SM sensitivities.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
a_vh = at_over_a * _DE_DA_FACTOR * (s_h_m2 / s_ref_m2)
# Clamp to physically meaningful range (spec §A1: 0.05–0.15 typical)
return max(0.01, min(0.20, a_vh))
```

**Inputs.**

- [[at-over-a-ratio|Tail-to-wing lift-curve-slope ratio]]
- [[de-da-factor|Downwash factor (1 − de/dalpha)]]
- [[s-h-m2-fallback|Horizontal tail area fallback]]  — *⤵ fallback*
- [[s-ref-m2-fallback|Reference area fallback]]  — *⤵ fallback*

**Produced by.** `app/services/sm_sizing_service.py:122` — `_alpha_vh`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Clipped wing shift` · `SM sensitivity to wing longitudinal shift` · `Neutral point after wing shift`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:139,140 (_dsm_dx_wing)` · `app/services/sm_sizing_service.py:424,425,431 (forward clip)`

**Source.** 🟡 PARTIAL

> Each factor is individually attributable — a_t/a from Sadraey §6.7.4 Eq. 6.57, (1 − dε/dα) from Sadraey §6.7.4, and the area ratio S_H/S_w from the tail-volume definition Sadraey §6.7.1 Eq. 6.29 / 11.20. The composite product α_VH as defined here is not found in any consulted source. The code's citation "Anderson §7.6" is a misattribution: in Anderson, "Fundamentals of Aerodynamics" 6e, Chapter 7 is "Compressible Flow: Some Preliminary Aspects" and §7.6 covers shock waves — the aerodynamic centre is §4.9 and downwash is §5.1; static margin does not appear in that book at all.
>
> — via `aircraft-design-scholz + aerodynamics-expert`

**The source states it as.**

```
Standard tail contribution to the neutral point uses the tail volume ratio V_H = S_H·l_H/(S·c̄) together with η_h·(a_t/a)·(1 − dε/dα) — Sadraey Eq. 6.29 / Eq. 11.20 — i.e. the moment arm l_H is part of the group, and the tail dynamic-pressure ratio η_h (0.85–0.95, Sadraey §6.7.1) is a separate factor.
```

**⚠️ Divergence from the source.** Two structural differences from the literature group. (a) The moment arm is absent: α_VH uses only the area ratio S_H/S_ref, whereas every source form of the tail's neutral-point contribution carries l_H. (b) The tail dynamic-pressure ratio η_h (Sadraey: 0.85–0.95 conventional, ~1 T-tail) is missing entirely. The docstring also calls α_VH the "tail efficiency factor", a name that in Sadraey §6.7.1 and Lennon Ch. 7 (HTE 40–90 %) denotes η_h — a different quantity with a different value range. The clamp bounds 0.01/0.20 are wider than the 0.05–0.15 the comment cites, and bind silently.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Clamp bounds 0.01/0.20 are wider than the 0.05–0.15 range the comment cites, and the clamp is silent — no DesignWarning is emitted when it binds (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Anderson §7.6: α_VH is a dimensionless ratio.  Earlier versions of this
function incorrectly divided by mac_m (metres), which produced 1/m units and
a ~20% systematic error at model scale (MAC≈0.30 m).  Removed (gh-494 fix).`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
