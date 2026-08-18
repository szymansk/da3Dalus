---
name: section-modulus-rectangular
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

# Section modulus, solid rectangle

**Definition.** Elastic section modulus of a solid rectangular spar of width b and height h, bending about the horizontal axis.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return b * h**2 / 6.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:45` — `section_modulus_rectangular`

**Consumed by.**

- outside it: `app/tests/test_spar_sizing_service.py:33`

**Source.** 🟡 PARTIAL

> No source read states this closed form. Nearest attributable: Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm (gives the two-flange form W = b·(H³−h³)/(6·H), of which b·h²/6 is the solid limit h→0); RC-Network Wiki, "Mechanische Spannung (Materialkunde)", https://wiki.rc-network.de/wiki/Mechanische_Spannung (beam bending: tension above, compression below, minimal at mid-depth)
>
> — via `rc-aircraft-designer (RC-Network Wiki vault) + direct verification of the kirch source cited in the module docstring`

**The source states it as.**

```
Kirch states only W = (b × (H³ − h³)) / (6 × H). Setting h = 0 gives b·H²/6, i.e. the code's form. Kirch never writes the solid-rectangle case separately.
```

**⚠️ Anomaly.** No production consumer — only the unit test. The real sizing path inlines the inverted form at _solve_rectangular (spar_sizing.py:182).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Reference: kirch Hauptholm (https://www.flugmodellbau-kirch.de/Hauptholm.htm) and the user's section-modulus scan.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
