---
name: front-moment-fn
symbol: M(y)
kind: quantity
unit: N·m
cluster: structure
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/sourced
  - flag/anomaly
  - flag/divergence
---

# Front-spar bending moment interpolator

**Definition.** Clamped piecewise-linear interpolation of \|bending moment\| over the sampled span fractions; the front spar's sizing driver.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
samples = sorted(request.moments, key=lambda m: m.y_span)
ys = [s.y_span for s in samples]
ms = [abs(s.bending_moment_Nm) for s in samples]
return _make_interpolator(ys, ms)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:398` — `_make_moment_fn`

**Consumed by.**

- in this graph: `Rear-spar secondary bending share` · `Station design moment (plan path)` · `Torsion proxy from bending moment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:560` · `app/services/spar_plan_service.py:439` · `cad_designer/airplane/geometry/spar_solver.py:764`

**Source.** 🟢 SOURCED

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — "The Holm (spar) is the principal structural element in an aircraft wing, bearing the majority of bending loads from lift"; Scholz, Flugzeugentwurf, 07_WingDesign §7.4 / [[wing-box-spars]] — the front spar "carries the primary bending moment from wing lift"; Kirch, "Hauptholm", procedure step 1 (M = P × l)
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
The front/main spar is bending-driven. Both sources state it independently.
```

**⚠️ Divergence from the source.** The engineering premise is sourced. The piecewise-linear interpolation with endpoint clamping is a numerical choice with no cited basis, and the clamp is undeclared (ADR 0020): moments stopping at y_span=0.8 are silently held to the tip.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared clamp: values outside the sampled span range are silently held at the nearest endpoint (spar_plan_service.py:370-373). A request whose moments stop at y_span=0.8 gets the 0.8 moment applied all the way to the tip with no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Linear interpolation over the (sorted) span fractions; clamps outside the sampled range to the nearest endpoint. The front spar stays bending-driven (gh-1038 keeps this unchanged).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
