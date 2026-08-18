---
name: center-z-nearest-key-tolerance
kind: constant
unit: m
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
---

# center_z nearest-key lookup tolerance

**Definition.** Spanwise tolerance within which a center_z map key is accepted as matching the station y; mirrors the t/c tolerance so both maps resolve consistently.

**Value.** `0.01`

**Formula — as the code writes it.**

```
if nearest is not None and abs(nearest - y_m) < 0.01:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:417` — `_lookup_center_z`

**Consumed by.**

- in this graph: [[center-z-mm|Section mid-height (spar placement reference)]]
- outside it: `app/services/spar_sizing.py:417`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (numerical lookup tolerance)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**Cited in the code itself.** `Mirrors :func:`_get_tc`'s nearest-key tolerance so the same station keys resolve consistently across both maps.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
