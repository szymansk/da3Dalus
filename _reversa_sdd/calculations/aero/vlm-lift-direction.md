---
name: vlm-lift-direction
symbol: l_hat
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Unit lift direction

**Definition.** Lift direction constructed by rotating the freestream direction 90° in the x–z plane only.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
l_hat = np.array([-d_hat[2], 0.0, d_hat[0]]); l_hat = l_hat / np.linalg.norm(l_hat)
```

**Inputs.**

- [[vlm-drag-direction|Unit freestream (drag) direction]]

**Produced by.** `app/services/vlm_strip_forces.py:229` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Strip lift force`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 (lift = component of resultant force PERPENDICULAR to V_inf)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
L = R . l_hat with l_hat perpendicular to V_inf
```

**⚠️ Divergence from the source.** Real. The code builds l_hat = [-d_hat[2], 0, d_hat[0]], discarding d_hat[1]. That is perpendicular to the freestream only when beta = 0. At beta != 0, l_hat . d_hat = -d_hat[2]*d_hat[0] + d_hat[0]*d_hat[2] = 0 holds in x-z but the normalisation is against the FULL d_hat, so the lift axis is no longer orthogonal to the actual freestream and both strip lift and strip drag are mis-projected. Contradicts the cited definition.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The y-component of d_hat is discarded, so at beta != 0 l_hat is not perpendicular to the freestream and strip lift/drag are mis-projected.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:229-230`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
