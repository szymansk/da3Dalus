---
name: spar-spacing-fraction
symbol: Δx/c
kind: quantity
unit: dimensionless (fraction of chord)
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

# Front–rear spar chordwise spacing

**Definition.** Chordwise distance between the front and rear spars as a fraction of chord — the lever arm over which the torsion couple is reacted.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
front_x = request.front_x_over_chord
if front_x is None:
    front_x = _DEFAULT_FRONT_X_C
spacing = request.rear_x_over_chord - front_x
return max(abs(spacing), _MIN_SPAR_SPACING)
```

**Inputs.**

- [[default-front-x-c|Assumed front-spar chord fraction]]  — *⤵ fallback*
- [[min-spar-spacing|Minimum front–rear spar spacing fraction]]  — *⊣ limit*
- [[rear-x-over-chord|Rear-spar chord fraction (requested)]]

**Produced by.** `app/services/spar_plan_service.py:413` — `_spar_spacing_fraction`

**Consumed by.**

- in this graph: `Rear-spar torsion reaction`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:437` · `app/services/spar_plan_service.py:453`

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf, 07_WingDesign §7.4, p. 7-42 (front spar 15-30% chord, rear spar 65-75% chord — the two locations whose difference this is); RC-Network Wiki, "Torsion (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Torsion
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Scholz gives the two spar locations; no source read forms their difference as a torsion lever arm.
```

**⚠️ Divergence from the source.** DIMENSIONAL DEFECT CONFIRMED against elementary statics, which both expert vaults presuppose (RC-Network "Mechanische Spannung": σ = F/A, N/mm²). A couple of moment T reacted by two parallel forces at separation d gives a FORCE F = T/d, where d is a LENGTH. This function returns a DIMENSIONLESS chord fraction, and app/services/spar_plan_service.py:453 divides a torsion moment in N·m by it, then feeds the result to build_stations_from_geometry as a bending moment in N·m. The physically correct lever arm is spacing × chord(y) in metres. Because the local chord never enters, the rear-spar sizing moment does not scale with chord as a real couple would — the error is not a constant offset, it varies along the span with the taper.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Scholz's spar-location bands are CS-25 transport-category (chosen for slat and spoiler-drive compatibility). ADR 0023.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Dimensionally inconsistent with its use: this is a DIMENSIONLESS chord fraction, but at line 453 it divides a torsion moment in N·m to produce what the code calls a 'reaction' that is then treated as a bending moment in N·m by build_stations_from_geometry. A real lever arm would be spacing · chord(y) in metres; the local chord never enters, so the rear-spar sizing moment scales wrongly with chord.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `The torsion couple T(y) is reacted by the front+rear pair over this spacing, so the rear-spar reaction force ∝ T(y) / spacing.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
