---
name: sizing-half-span-selection
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Design half-span selection

**Definition.** The half-span with the larger absolute root bending moment supplies the sizing stations.

**Formula — as the code writes it.**

```
if abs(surface.root_bending_moment_Nm_starboard) >= abs(surface.root_bending_moment_Nm_port): entries = surface.starboard else: entries = surface.port
```

**Inputs.** [[root-bm-starboard|Starboard root bending moment]] · [[root-bm-port|Port root bending moment]]

**Produced by.** `app/services/analysis_service.py:2206` — `_surface_to_stations`

**Consumed by.**

- in this graph: [[spar-sizing-block|Per-surface spar sizing block]]
- outside it: `compute_spar_sizing`

**Source.** 🔴 NO SOURCE FOUND

> Sizing on max(\|M_starboard\|, \|M_port\|) is a conservative engineering choice referenced in-code to 'spec §5', but no consulted source (Scholz §7.4, Sadraey §5.8, RC-Network 'Holm') states it.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Conservative and defensible, but the asymmetry it guards against (sideslip-induced spanwise load asymmetry) is never surfaced to the user.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
