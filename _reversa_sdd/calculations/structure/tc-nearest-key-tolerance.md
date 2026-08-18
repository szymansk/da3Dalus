---
name: tc-nearest-key-tolerance
kind: constant
unit: m
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
---

# t/c nearest-key lookup tolerance

**Definition.** Spanwise tolerance within which a t/c map key is accepted as matching the station y before falling back to 0.12.

**Value.** `0.01`

**Formula — as the code writes it.**

```
if nearest is not None and abs(nearest - y_m) < 0.01:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:399` — `_get_tc`

**Consumed by.**

- in this graph: [[tc-ratio|Thickness-to-chord ratio at station]]
- outside it: `app/services/spar_sizing.py:399`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (numerical lookup tolerance, not an engineering quantity)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `Tries exact match then nearest key within 1 cm tolerance.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
