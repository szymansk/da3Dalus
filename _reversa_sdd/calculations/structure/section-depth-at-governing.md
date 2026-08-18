---
name: section-depth-at-governing
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Section depth at the governing station

**Definition.** Contained band depth at the governing station, quoted in the infeasibility message so a builder can see how far short the section is.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
depth = max(0.0, governing.band_hi - governing.band_lo)
```

**Inputs.**

- [[band-lo|Contained band lower bound]]  — *⊣ limit*
- [[band-hi|Contained band upper bound]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:543` — `_piece_from_run_with_od`

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/spar_solver.py:545` · `app/schemas/spar_plan.py:238` · `frontend/hooks/useSparPlan.ts:65`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — the Kastenholm is "the most efficient use of available wing depth"; Scholz, Flugzeugentwurf, 07_WingDesign §7.3 / [[thickness-ratio]] — bending stiffness ∝ (box height)³, so "a thicker wing requires less material to achieve the same stiffness"
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
Section depth is the governing geometric resource for a bending member; both sources state this.
```

**⚠️ Divergence from the source.** The code's infeasibility message advises "a round tube is the least efficient bending member, consider a capped/box spar" — this is directly corroborated by RC-Network "Holm" (Kastenholm = most efficient use of available wing depth) and by the kirch source, which gives the capped section modulus in closed form. The advice is sound; the irony is that the plan path cannot act on it (see `spar-shape`: a capped request is sized as a rod).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `required OD {od:.1f} mm exceeds section depth {depth:.1f} mm at y={governing.y_mm:.0f} mm; increase root depth/chord or reduce design load — a round tube is the least efficient bending member, consider a capped/box spar`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
