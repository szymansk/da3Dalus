---
name: station-design-moment
symbol: M_design
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
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Station design moment (plan path)

**Definition.** Design moment at a solver station: the driver moment (bending for the front spar, torsion reaction for the rear) times the limit load factor times the safety factor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
m_design = abs(moment_fn(y_span)) * g_limit * safety_factor_j
```

**Inputs.**

- [[front-moment-fn|Front-spar bending moment interpolator]]  — *⊣ limit*
- [[rear-moment-fn|Rear-spar sizing moment]]
- [[resolved-g-limit-plan|Limit load factor (plan path)]]  — *⊣ limit*
- [[structure--safety-factor-j|Safety factor j]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:764` — `build_stations_from_geometry`

**Consumed by.**

- in this graph: `Station required section modulus (plan path)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:765`

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design (Wiley 2013), §10.4.1, Eq. (10.4) — n_ult = 1.5 · n_max; Kirch, "Hauptholm", https://www.flugmodellbau-kirch.de/Hauptholm.htm, procedure step 1 (M = P × l with P the G-scaled load)
>
> — via `aircraft-design-scholz + direct verification of the kirch source`

**The source states it as.**

```
Sadraey Eq. (10.4): n_ult = 1.5 · n_max. Kirch: M = P × l.
```

**⚠️ Divergence from the source.** Identical composition and identical provenance limits as `design-bending-moment` (see that entry) — this is a SECOND independent producer of the same formula, at cad_designer/airplane/geometry/spar_solver.py:764. Unlike the sizing path it is never surfaced, so the plan endpoint reports no design moment at all. For the REAR spar the `moment_fn` fed in here is `rear_moment_fn`, which carries the dimensional defect documented at `rear-torsion-reaction`.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey's 1.5 is attributed by Sadraey to FAR 23 / FAR 25 and presupposes A/B-basis statistical allowables unavailable at 0.5-15 kg (project record BR-W17, gh-1079). ADR 0023.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Second independent producer of the identical formula: app/services/spar_sizing.py:315. Unlike that one it is never surfaced in the response, so the plan endpoint reports no design moment at all.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `compute the strength-required OD from #1008 sizing using the station's design moment ``M_design = \|M\| · g · j``.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
