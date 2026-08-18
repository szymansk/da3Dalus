---
name: s-v-recommended-mm2
symbol: S_V,rec
kind: quantity
unit: mm²
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Recommended vertical tail area

**Definition.** Vertical tail area that would place V_V at the midpoint of the class target band, converted to mm².

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
v_v_mid = (v_v_range[0] + v_v_range[1]) / 2.0
result.s_v_recommended_mm2 = round(v_v_mid * s_ref_m2 * b_ref_m / l_v * 1e6, 0)
```

**Inputs.**

- [[aircraft-class-tail-targets|Tail-volume target ranges by aircraft class]]
- [[l-v-m|Vertical tail moment arm]]

**Produced by.** `app/services/tail_sizing_service.py:263` — `compute_tail_volumes`

**Consumed by.**

- outside it: `app/api/v2/endpoints/aeroplane/tail_sizing.py:86` · `frontend/hooks/useTailSizing.ts`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7.1 — same inversion applied to the vertical tail: S_v = V_V · b · S / l_v, from V̄_V = S_v·l_v/(S·b). Sadraey §6.7.1 also lists the fix-it levers when V_V is inadequate (extend aft fuselage, increase S_v, dorsal fin, ventral fin, twin fins).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
S_v = V_V · b · S / l_v
```

**⚠️ Divergence from the source.** Because V_V is computed from a possibly doubled fin area (see v-v-current), a single-fin aircraft can be classified 'above_range' and told to shrink a fin that was never that large. Sadraey §6.7.1 also imposes a spin-recovery geometric constraint on the vertical tail (≥50 % of fin planform outside the horizontal-tail wake, bounded by 30°/60° lines) that no area recommendation here accounts for.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Inherits the symmetric-doubling issue from _wing_area_approx via V_V but is itself computed from the target band, so a design shown as 'above_range' will be told to shrink a fin that was never that large.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
