---
name: reinforcement-length
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Reinforcement length

**Definition.** Total length of the root reinforcement, spanning symmetrically across y=0 from -reach to +reach.

**Formula — as the code writes it.**

```
length=2.0 * reach,  # spans symmetrically across the root (y=-reach → +reach)
```

**Inputs.** [[reinforcement-reach|Reinforcement half-reach]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:649` — `_reinforcement_piece`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:495` · `cad_designer/airplane/geometry/spar_cad_insertion.py:65`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (inherits the unattributed reach; symmetric span across y=0 is geometrically implied by Sadraey §7.9.3's carry-through principle but the LENGTH has no source)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `# spans symmetrically across the root (y=-reach → +reach)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
