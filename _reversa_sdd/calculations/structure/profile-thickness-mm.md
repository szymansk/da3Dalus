---
name: profile-thickness-mm
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
  - flag/divergence
---

# Local airfoil profile thickness

**Definition.** Vertical depth of the airfoil at the station — chord times t/c. When the real built section is available (gh-1022), t/c is back-computed from it so this reproduces the real built thickness.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
profile_thickness_mm = chord_mm * tc_ratio
```

**Inputs.**

- [[chord-mm|Local chord in millimetres]]
- [[tc-ratio|Thickness-to-chord ratio at station]]

**Produced by.** `app/services/spar_sizing.py:322` — `compute_spar_sizing`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Spar outer dimension`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:323` · `app/services/spar_sizing.py:337` · `app/schemas/spar_sizing.py:59` · `frontend/hooks/useSparSizing.ts:19`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §7.9.3, Eq. (7.26); RC-Network Wiki, "Profil - charakteristische geometrische Größen", https://wiki.rc-network.de/wiki/Profil (relative thickness = max thickness / chord)
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Sadraey Eq. (7.26): t_r = (t/C)_max_r · C_r — "the wing thickness at the root (or fuselage intersection) is the wing root maximum thickness-to-chord ratio times the wing root chord".
```

**⚠️ Divergence from the source.** Sadraey states it for the root station; the code applies the identical relation at every spanwise station (app/services/spar_sizing.py:322). That is a straightforward and correct generalisation of the definition of t/c.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
