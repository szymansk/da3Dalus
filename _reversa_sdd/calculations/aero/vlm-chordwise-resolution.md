---
name: vlm-chordwise-resolution
symbol: chordwise_resolution
kind: parameter
unit: panels
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# VLM chordwise panels per strip

**Definition.** Number of chordwise VLM panels making up one spanwise strip.

**Value.** `8`

**Formula — as the code writes it.**

```
chordwise_resolution: int = 8
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/vlm_strip_forces.py:171` — `compute_vlm_strip_forces`

**Consumed by.**

- outside it: `app/services/vlm_strip_forces.py:compute_vlm_strip_forces (n_chordwise output field)` · `app/schemas/strip_forces.py:SurfaceStripForces.n_chordwise`

**Source.** 🟡 PARTIAL

> AeroSandbox docs_aero_3d.md (chordwise_resolution default = 10); AVL User Primer avl_doc.txt L1122-1131 (Rule 4)
>
> — via `aerosandbox-expert, avl-advisor`

**The source states it as.**

```
chordwise_resolution default 10 (ASB); AVL Rule 4: refine spanwise AND chordwise together
```

**⚠️ Divergence from the source.** 8 is close to the ASB default of 10 and in the plausible band, but no source names 8. Rule 4 warns that refining only spanwise (40 vs 8) may not converge, especially at dihedral breaks and swept-wing centrelines.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:171`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
