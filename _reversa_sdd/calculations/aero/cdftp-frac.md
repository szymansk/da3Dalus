---
name: cdftp-frac
symbol: frac
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/divergence
---

# Span fraction of a section

**Definition.** Normalised spanwise position used to blend the root and tip trip positions.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
frac = (sec.y_m - y_min) / y_span if y_span > 0 else 0.0
```

**Inputs.**

- [[saoa-y|Panel spanwise position]]
- [[cdftp-y-span|Span extent for trip interpolation]]

**Produced by.** `app/services/turbulator_optimizer_service.py:687` — `compute_delta_cd0_from_turbulator_position`

**Consumed by.**

- in this graph: `Section trip position from the installed turbulator`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.3 (spanwise station parameterisation); Sadraey, Aircraft Design (Wiley 2013) §5.14 Step 2 (Glauert transformation y = (b/2) cos(theta) as the standard spanwise parameter)
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
eta = y / (b/2), normalised spanwise station
```

**⚠️ Divergence from the source.** Linear normalised station is standard for GEOMETRY. Note the cited aerodynamic parameterisation (Glauert cosine) is different — but that applies to circulation, not to where you stick tape, so linear is the right choice here.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:687`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
