---
name: capped-cross-section-area
symbol: A
kind: quantity
unit: mm²
cluster: structure
user_visible: true
source_status: SOURCED
---

# Capped-spar cross-section area

**Definition.** Area of the two flanges of the capped spar (the web is neglected), used for mass integration.

**Formula — as the code writes it.**

```
area = 2.0 * b * gurt  # two flanges (upper + lower)
```

**Inputs.** [[capped-gurt-thickness|Capped-spar flange (gurt) thickness]] · [[cap-width-mm|Cap/flange width]]

**Produced by.** `app/services/spar_sizing.py:210` — `_solve_capped`

**Consumed by.**

- in this graph: [[spar-mass-half|Half-span spar mass]]
- outside it: `app/services/spar_sizing.py:347` · `app/services/spar_sizing.py:356`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — material area implied by the section whose W the source states
>
> — via `direct verification of the kirch source, with the identity checked numerically`

**The source states it as.**

```
The source's W = b(H³−h³)/(6H) is the section modulus of a rectangle b×H with a b×h void of ZERO web thickness. The material area of that exact section is b·H − b·h = b·(H−h) = 2·b·(H−h)/2 = 2·b·gurt.
```

**⚠️ Divergence from the source.** CORRECTION TO THE INVENTORY'S RECORDED ANOMALY. The inventory states "the web is excluded from the area, so the capped-spar mass estimate is systematically low". Verified arithmetic (b=10, H=20, h=14): b·H − b·h = 60.0 and 2·b·gurt = 60.0 — identical. The area A = 2·b·gurt is EXACTLY consistent with the section the source's W formula describes, because that formula already assumes a zero-thickness web. There is no mass understatement relative to the source. A real spar with a finite web would need BOTH a larger W and a larger A; the code is self-consistent, not low.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The web is excluded from the area, so the capped-spar mass estimate is systematically low. The omission is not stated as a limitation anywhere in the result or schema.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# two flanges (upper + lower)`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
