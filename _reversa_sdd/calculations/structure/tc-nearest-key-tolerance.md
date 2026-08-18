---
name: tc-nearest-key-tolerance
kind: constant
unit: m
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/no-source-found
---

# t/c nearest-key lookup tolerance

**Definition.** Spanwise tolerance within which a t/c map key is accepted as matching the station y before falling back to 0.12.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.01`

**Formula — as the code writes it.**

```
if nearest is not None and abs(nearest - y_m) < 0.01:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:399` — `_get_tc`

**Consumed by.**

- in this graph: `Thickness-to-chord ratio at station`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:399`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (numerical lookup tolerance, not an engineering quantity)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `Tries exact match then nearest key within 1 cm tolerance.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
