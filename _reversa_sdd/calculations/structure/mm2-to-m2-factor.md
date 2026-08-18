---
name: mm2-to-m2-factor
kind: constant
unit: m²/mm²
cluster: structure
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/structure
  - class/numerical-tolerance
  - source/sourced
  - audit/confirmed
---

# Square-millimetre to square-metre factor

**Definition.** Unit conversion from mm² to m² inside the mass integral.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-6`

**Formula — as the code writes it.**

```
avg_area_m2 = avg_area_mm2 * 1e-6  # mm² → m²
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:248` — `spar_mass_half_kg`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Half-span spar mass` · `Linear mass of a stock cross-section`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:248` · `app/services/spar_plan_service.py:87`

**Source.** 🟢 SOURCED

> BIPM, The International System of Units (SI), 9th edition 2019, §3.1 Table 7 — SI prefixes: milli = 10⁻³, hence 1 mm² = 10⁻⁶ m²
>
> — via `none required (SI definition)`

**Cited in the code itself.** `# mm² → m²`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
