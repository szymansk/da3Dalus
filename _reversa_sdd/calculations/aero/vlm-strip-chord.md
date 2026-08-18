---
name: vlm-strip-chord
symbol: Chord
kind: quantity
unit: m
cluster: aero-strips
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Local strip chord

**Definition.** Streamwise chord of the strip taken as the x-distance between LE and TE midpoints.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
chord = float(abs(te_pt[0] - le[0]))
```

**Inputs.**

- [[vlm-strip-le|Strip leading-edge point]]
- [[vlm-strip-te|Strip trailing-edge point]]

**Produced by.** `app/services/vlm_strip_forces.py:262` — `compute_vlm_strip_forces`

**Consumed by.**

- in this graph: `Chord × cl product` · `Normalised strip lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spanwise_loads.py:75` · `frontend/hooks/useStripForces.ts`

**Source.** 🟡 PARTIAL

> AVL 3.40 source, Avl/src/aoutput.f:312 (CHORD(J), the geometric section chord); Anderson, Fundamentals of Aerodynamics 6e, §4.2 (chord = straight-line LE-to-TE distance)
>
> — via `avl-advisor, aerodynamics-expert`

**The source states it as.**

```
c = |TE - LE| (full 3-D straight-line distance)
```

**⚠️ Divergence from the source.** Real. The code uses abs(te_x - le_x), the x-projection only. For a section at twist theta the true chord is under-reported by a factor cos(theta); at 5 deg twist that is -0.4%, but for a large dihedral/twist tip section the error grows. Everything downstream (c_cl, cl_norm, spanwise_loads) inherits it.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Chord is the x-projection only; a twisted or dihedral section's true chord is under-reported (z-difference discarded).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:262`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
