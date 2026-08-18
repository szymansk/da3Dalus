---
name: capped-gurt-thickness
symbol: gurt
kind: quantity
unit: mm
cluster: structure
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Capped-spar flange (gurt) thickness

**Definition.** Flange thickness of the capped spar; the free dimension reported as solved_mm for shape='capped'.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
gurt = (H - h) / 2.0
```

**Inputs.**

- [[capped-inner-height|Capped-spar inner gap height]]
- [[spar-outer-dimension|Spar outer dimension]]

**Produced by.** `app/services/spar_sizing.py:209` — `_solve_capped`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Capped-spar cross-section area`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:210` · `app/services/spar_sizing.py:344` · `frontend/lib/sparSizingHelpers.ts:59`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm (source defines b, H, h such that the flange thickness is (H−h)/2); RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm — Holmgurte (booms/flanges), upper = Druckgurt (compression), lower = Zuggurt (tension)
>
> — via `rc-aircraft-designer (RC-Network Wiki) + direct verification of the kirch source`

**The source states it as.**

```
Implied by the source's geometry definition: with H the total spar height and h the height between the flanges, each flange is (H−h)/2 thick. The code's German variable name `gurt` matches the RC-Network term Holmgurt exactly.
```

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
