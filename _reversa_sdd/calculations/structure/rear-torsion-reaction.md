---
name: rear-torsion-reaction
kind: quantity
unit: N·m (see anomaly)
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Rear-spar torsion reaction

**Definition.** The share of the torsion couple the rear spar carries, as a moment: torsion divided by the front–rear spacing fraction.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
reaction = torsion_fn(y_span) / spacing
```

**Inputs.**

- [[torsion-proxy|Torsion proxy from bending moment]]
- [[spar-spacing-fraction|Front–rear spar chordwise spacing]]

**Produced by.** `app/services/spar_plan_service.py:453` — `_make_rear_moment_fn`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Rear-spar sizing moment`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_plan_service.py:455`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Torsion (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Torsion — "loads on the spar boxing during torsion are pure shear forces"; RC-Network Wiki, "Mechanische Spannung (Materialkunde)", https://wiki.rc-network.de/wiki/Mechanische_Spannung — σ = F/A
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
RC-Network "Torsion" states that torsion in a wing structure is reacted as FORCES ("pure shear forces"), consistent with elementary statics: a couple of moment T reacted at separation d gives F = T/d with d a length.
```

**⚠️ Divergence from the source.** CONFIRMED DIMENSIONAL DEFECT. The source's own statement — torsion is reacted by FORCES — is what the code's arithmetic violates. `reaction = torsion_fn(y_span) / spacing` divides N·m by a dimensionless chord fraction, yielding N·m, and app/services/spar_plan_service.py:455 then feeds it to build_stations_from_geometry (cad_designer/airplane/geometry/spar_solver.py:764) as a BENDING MOMENT. The correct chain is force F = T/(spacing · chord(y)) [N], then a rear-spar bending moment from that force distribution. As written the rear spar's sizing moment is independent of chord, so it mis-scales along a tapered span.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Dividing a moment (N·m) by a dimensionless chord fraction yields N·m, but the physical couple reaction is a FORCE (T / lever-arm-in-metres). The result is then consumed as a bending moment by build_stations_from_geometry. The local chord never enters, so the rear spar's sizing moment does not scale with chord as a real couple would.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `The front+rear pair forms a couple against wing twist: the rear member carries a reaction ≈ ``T(y) / spacing`` where ``spacing`` is the chordwise front–rear distance (fraction of chord).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
