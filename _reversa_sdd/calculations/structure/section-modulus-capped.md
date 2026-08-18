---
name: section-modulus-capped
symbol: W
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: SOURCED
---

# Section modulus, capped (I/C-beam)

**Definition.** Elastic section modulus of a capped spar: flange width b, outer height H, inner gap height h.

**Formula — as the code writes it.**

```
return b * (H**3 - h**3) / (6.0 * H)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:54` — `section_modulus_capped`

**Consumed by.**

- outside it: `app/tests/test_spar_sizing_service.py:40`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — section-modulus formula for the two-flange (Kastenholm) spar. This is the source already named in the module docstring app/services/spar_sizing.py:6 and it is verified: the page states this formula.
>
> — via `direct verification of the kirch source named in the code (RC/German model-building), cross-checked against rc-aircraft-designer vault`

**The source states it as.**

```
W = (b × (H³ − h³)) / (6 × H), with b = flange width (mm), H = total spar height (mm), h = height between the flanges (mm).
```

**⚠️ Divergence from the source.** None. The code at app/services/spar_sizing.py:54 (`return b * (H**3 - h**3) / (6.0 * H)`) reproduces the source formula exactly, including variable naming (b, H, h). This is the ONE formula in the whole cluster that is an exact, verified match to a named external source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No production consumer — only the unit test. The sizing path inlines the inverted form at _solve_capped (spar_sizing.py:196).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Reference: kirch Hauptholm (https://www.flugmodellbau-kirch.de/Hauptholm.htm) and the user's section-modulus scan.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
