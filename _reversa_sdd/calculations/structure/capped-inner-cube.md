---
name: capped-inner-cube
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/sourced
  - audit/confirmed
---

# Capped-spar inner-height cube

**Definition.** Cubed inner gap height of a capped spar; negative means the requested flange width b cannot deliver erf_W at height H.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
inner_cube = H**3 - 6.0 * H * erf_w / b
```

**Inputs.**

- [[required-section-modulus|Required section modulus]]
- [[spar-outer-dimension|Spar outer dimension]]
- [[cap-width-mm|Cap/flange width]]

**Produced by.** `app/services/spar_sizing.py:196` — `_solve_capped`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Capped-spar inner gap height`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:197` · `app/services/spar_sizing.py:208`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — algebraic rearrangement of the source's stated two-flange section-modulus formula
>
> — via `direct verification of the kirch source named in the code`

**The source states it as.**

```
W = (b × (H³ − h³)) / (6 × H). Rearranged for h³: h³ = H³ − 6·H·W/b, which is exactly the code's `inner_cube = H**3 - 6.0 * H * erf_w / b` at app/services/spar_sizing.py:196.
```

**Cited in the code itself.** `capped: H = outer, b = cap_width_mm, solve h = (H³-6·H·erf_w/b)^(1/3), gurt = (H-h)/2`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
