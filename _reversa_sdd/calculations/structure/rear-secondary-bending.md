---
name: rear-secondary-bending
kind: quantity
unit: N·m
cluster: structure
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - flag/divergence
---

# Rear-spar secondary bending share

**Definition.** Genuine secondary bending the rear spar carries, added on top of the torsion reaction: a user-set fraction of the local bending moment.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
secondary = secondary_fraction * bending_fn(y_span)
```

**Inputs.**

- [[rear-secondary-bending-fraction|Rear secondary bending fraction]]
- [[front-moment-fn|Front-spar bending moment interpolator]]  — *⊣ limit*

**Produced by.** `app/services/spar_plan_service.py:454` — `_make_rear_moment_fn`

**Consumed by.**

- in this graph: `Rear-spar sizing moment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:455`

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf, 07_WingDesign §7.4 / [[wing-box-spars]] — the rear spar "carries secondary bending loads and provides torsional constraint"; Lennon, The Basics of R/C Model Aircraft Design (1996), Ch. 13 — "An aft spar carries flap or aileron hinge loads and lift increments when flaps deflect"
>
> — via `aircraft-design-scholz (lead) + rc-aircraft-designer`

**The source states it as.**

```
Both sources confirm the rear spar carries genuine secondary bending in addition to its torsional role. Lennon names the physical mechanism at RC scale: hinge loads and the lift increment from flap deflection.
```

**⚠️ Divergence from the source.** The CONCEPT is well sourced by both authorities. Expressing it as a user-set FRACTION of the primary bending moment M(y) is not: Lennon's mechanism (flap/aileron hinge loads and deflected-flap lift increment) has no fixed proportionality to the wing's primary bending moment, so the parametrisation does not follow from either source.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
