---
name: vlm-strip-cp-xc
symbol: C.P.x/c
kind: constant
unit: x/c
cluster: aero-strips
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/vlm
---

# Strip centre of pressure x/c

**Definition.** Centre of pressure pinned to the quarter chord on the VLM path.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.25`

**Formula — as the code writes it.**

```
"C.P.x/c": 0.25,
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:297` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/schemas/strip_forces.py:StripForceEntry.cp_xc`

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §4.7 (x_cp = c/4 for a SYMMETRIC thin airfoil), §4.9 (aerodynamic centre at c/4 for any thin airfoil), §1.6 (x_cp = -M'_LE / N'); AVL 3.40 source, Avl/src/aoutput.f:307-308
>
> — via `aerodynamics-expert, avl-advisor`

**The source states it as.**

```
AVL: XCP = 0.25 - CMC4(J)/CL_LSTRP(J), with a 999 sentinel when cl = 0 or XCP leaves (-1, 2)
```

**⚠️ Divergence from the source.** 0.25 is the centre of pressure only for an uncambered section. Anderson §1.6 shows x_cp migrates with lift and runs to infinity as cl -> 0; §4.9 puts the AERODYNAMIC centre at c/4 but the two points coincide only when cm_c/4 = 0. The app is internally consistent (it also hardcodes cm_c/4 = 0) but reports the thin-airfoil symmetric-section result as a computed centre of pressure, and unlike AVL it never emits the 'undefined' sentinel.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic 0.25 returned as if computed; thin-airfoil AC assumption is asserted, not derived, and carries no marker in the response.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:297`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
