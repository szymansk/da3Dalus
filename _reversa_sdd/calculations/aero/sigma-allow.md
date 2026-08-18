---
name: sigma-allow
symbol: σ_allow
kind: quantity
unit: MPa
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Allowable bending stress

**Definition.** Material allowable bending stress, either overridden by the request or read from the material component specs.

**Formula — as the code writes it.**

```
sigma_allow = spar_params.sigma_allow_mpa_override; if sigma_allow is None: sigma_allow = material_specs.get("allowable_bending_stress_mpa")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2139` — `_compute_spar_sizing_for_surfaces`

**Consumed by.**

- in this graph: [[aero-spanwise--sigma-allow-positivity-guard|σ_allow positivity guard]] · [[spar-sizing-block|Per-surface spar sizing block]]
- outside it: `compute_spar_sizing`

**Source.** 🟡 PARTIAL

> RC-Network Wiki 'Holm (Flugzeugkonstruktion)', https://wiki.rc-network.de/wiki/Holm (compression boom / tension boom carry the bending stress; material selection balsa / spruce / CFK laminate / GFK)
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Concept: bending stress sigma = M·c/I must stay below the material allowable; booms placed at maximum separation carry it
```

**⚠️ Divergence from the source.** The quantity is a material-database lookup, not a computed value — sourced as a concept, not as a number. No RC-specific allowable-stress table was found in the consulted vaults.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
