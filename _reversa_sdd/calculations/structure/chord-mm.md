---
name: chord-mm
symbol: c
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: SOURCED
---

# Local chord in millimetres

**Definition.** Station chord converted from the metre-based loads result into the millimetre unit context of the sizing formulas.

**Formula — as the code writes it.**

```
chord_mm = chord_m * 1000.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:321` — `compute_spar_sizing`

**Consumed by.**

- in this graph: [[profile-thickness-mm|Local airfoil profile thickness]]
- outside it: `app/services/spar_sizing.py:322`

**Source.** 🟢 SOURCED

> BIPM, The International System of Units (SI), 9th edition 2019, §3.1 Table 7 — SI prefixes: milli = 10⁻³
>
> — via `none required (unit conversion)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
