---
name: section-modulus-tube
symbol: W
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - flag/anomaly
---

# Section modulus, circular tube

**Definition.** Elastic section modulus of a hollow circular tube, outer diameter Da, inner diameter Di.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return math.pi * (Da**4 - Di**4) / (32.0 * Da)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:70` — `section_modulus_tube`

**Consumed by.**

- outside it: `app/tests/test_spar_sizing_service.py:54` · `app/tests/test_spar_sizing_service.py:62`

**Source.** 🟡 PARTIAL

> No source read states this formula. Searched: Sadraey (Wiley 2013) full text — the string "section modulus" returns ZERO hits; rc-aircraft-designer vault (RC-Network Wiki, Lennon 1996, rcplanedesigner) — no Widerstandsmoment/section-modulus formula; Kirch "Hauptholm" — gives the two-flange and rod cases only, not the tube. Nearest attributable context: RC-Network Wiki, "Holm (Flugzeugkonstruktion)", https://wiki.rc-network.de/wiki/Holm (Rohrholm: a single CFK tube carries bending and torsion together).
>
> — via `aircraft-design-scholz + rc-aircraft-designer (both vaults searched exhaustively; neither contains beam section-modulus formulas)`

**⚠️ Anomaly.** No production consumer — only the unit test. A second, independent producer of the identical formula exists at app/services/spar_plan_service.py:76 (_w_stock).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Reference: kirch Hauptholm (https://www.flugmodellbau-kirch.de/Hauptholm.htm) and the user's section-modulus scan.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
