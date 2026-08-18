---
name: capped-inner-height
symbol: h
kind: quantity
unit: mm
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

# Capped-spar inner gap height

**Definition.** Inner (web-gap) height of the capped I/C-beam section.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
h = inner_cube ** (1.0 / 3.0)
```

**Inputs.**

- [[capped-inner-cube|Capped-spar inner-height cube]]

**Produced by.** `app/services/spar_sizing.py:208` — `_solve_capped`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Capped-spar flange (gurt) thickness`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:209` · `app/services/spar_sizing.py:216`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — inversion of the stated two-flange formula; h is the source's own variable name ("height between flanges")
>
> — via `direct verification of the kirch source`

**The source states it as.**

```
From W = b(H³−h³)/(6H): h = (H³ − 6·H·W/b)^(1/3).
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
