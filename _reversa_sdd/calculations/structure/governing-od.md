---
name: governing-od
kind: quantity
unit: mm
cluster: structure
user_visible: false
source_status: SOURCED
---

# Governing required OD of a piece

**Definition.** The strength-required outer diameter that governs a whole straight piece: the maximum required_od across the stations it covers, which by the spec is the most inboard (highest-moment) one.

**Formula — as the code writes it.**

```
return max(s.required_od for s in stations)
```

**Inputs.** [[station-required-od|Station strength-required OD]]

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:303` — `_governing_od`

**Consumed by.**

- in this graph: [[piece-outer-diameter|Spar piece outer diameter]]
- outside it: `cad_designer/airplane/geometry/spar_solver.py:356` · `cad_designer/airplane/geometry/spar_solver.py:403` · `cad_designer/airplane/geometry/spar_solver.py:501`

**Source.** 🟢 SOURCED

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm, procedure step 5; Scholz, Flugzeugentwurf, 07_WingDesign §7.4 / [[wing-box-spars]]
>
> — via `direct verification of the kirch source + aircraft-design-scholz`

**The source states it as.**

```
Kirch step 5: "Taper flange dimensions linearly outboard from root" — i.e. the root (inboard) station governs and the section is reduced outboard. Scholz §7.4: wing-box structural depth "increases toward the root (where bending moments are largest) and decreases toward the tip".
```

**⚠️ Divergence from the source.** Both sources agree the inboard station governs, which is exactly the code's `max(s.required_od for s in stations)` premise. The code discretises into constant-OD straight pieces with telescoping joints; the kirch source instead tapers CONTINUOUSLY. That is a manufacturing-method difference (bought carbon tube stock vs built-up tapered flanges), not an error, but it means the code's part-count/joint behaviour has no basis in the cited source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `By the spec the inboard (root-side) station carries the highest moment, so its strength-required OD governs the whole straight piece.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
