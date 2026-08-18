---
name: mm2-to-m2-factor
kind: constant
unit: m²/mm²
cluster: structure
user_visible: false
source_status: SOURCED
---

# Square-millimetre to square-metre factor

**Definition.** Unit conversion from mm² to m² inside the mass integral.

**Value.** `1e-6`

**Formula — as the code writes it.**

```
avg_area_m2 = avg_area_mm2 * 1e-6  # mm² → m²
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:248` — `spar_mass_half_kg`

**Consumed by.**

- in this graph: [[spar-mass-half|Half-span spar mass]] · [[stock-linear-mass|Linear mass of a stock cross-section]]
- outside it: `app/services/spar_sizing.py:248` · `app/services/spar_plan_service.py:87`

**Source.** 🟢 SOURCED

> BIPM, The International System of Units (SI), 9th edition 2019, §3.1 Table 7 — SI prefixes: milli = 10⁻³, hence 1 mm² = 10⁻⁶ m²
>
> — via `none required (SI definition)`

**Cited in the code itself.** `# mm² → m²`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
