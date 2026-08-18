---
name: telescope-bore
kind: quantity
unit: mm
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
  - flag/divergence
---

# Telescoping bore demand

**Definition.** Minimum bore an inner (root-side) tube piece needs so the adjacent outboard piece can slide into it with clearance.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
telescope_bore = ods[i + 1] + 2.0 * spec.telescope_clearance_mm
```

**Inputs.**

- [[piece-outer-diameter|Spar piece outer diameter]]
- [[telescope-clearance-mm|Telescoping radial clearance]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:423` — `plan_spar`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Spar piece inner diameter`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `cad_designer/airplane/geometry/spar_solver.py:425`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, "Steckung (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Steckung — telescoping/plug spar joints in model aircraft, "the bending moment must be efficiently transferred from one main spar to the other, requiring robust materials such as steel, fiberglass (GFK) or carbon fiber (CFK) tubes and sleeves"; RC-Network Wiki, "Holm" (Rohrholm)
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
The source establishes the tube-in-tube joint as standard RC practice and states the fit must be precise, but gives no dimensional relation.
```

**⚠️ Divergence from the source.** The bore = outer-piece-OD + 2 × clearance relation is geometrically necessary and correct; only the clearance VALUE is unattributed (see `telescope-clearance-mm`).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# gh-1080: bore-propagation is TUBE-ONLY. Non-tube shapes (rod/rectangular/capped) connect via discrete joiners — they have no hollow bore to telescope into.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
