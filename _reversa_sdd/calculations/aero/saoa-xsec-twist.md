---
name: saoa-xsec-twist
symbol: xsec_twist
kind: quantity
unit: deg
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# Cross-section twist array

**Definition.** Absolute geometric twist of each cross-section relative to the body x-axis.

**Formula — as the code writes it.**

```
xsec_twist = np.array([float(xs.twist) for xs in xsecs])  # degrees
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:321` — `compute_section_aoa`

**Consumed by.**

- in this graph: [[saoa-twist-at-y|Interpolated twist at panel y]]

**Source.** 🟡 PARTIAL

> AeroSandbox tutorial 06, VLM point analysis ('twist is in degrees by convention', defined per WingXSec)
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** API read-through. Whether xsec.twist is absolute or relative to a wing incidence is the open question flagged under saoa-alpha-geom.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:320-321`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
