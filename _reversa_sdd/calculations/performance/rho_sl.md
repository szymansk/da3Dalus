---
name: rho_sl
symbol: ρ
kind: constant
unit: kg/m^3
cluster: perf-matching
user_visible: false
source_status: SOURCED
node_class: physical-constant
tags:
  - cluster/perf-matching
  - class/physical-constant
  - source/sourced
  - flag/anomaly
  - flag/divergence
  - flag/physical
---

# Sea-level ISA density

**Definition.** Air density used as the default for every field-length and matching-chart formula.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: sea-level air density.*

**Value.** `1.225`

**Formula — as the code writes it.**

```
_RHO_SL: float = 1.225
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:68` — `_RHO_SL`

**Consumed by.**

- in this graph: `Reynolds-dependent CD0` · `Dynamic pressure` · `Landing ground roll` · `Takeoff ground roll` · `Climb constraint T/W` · `Cruise constraint T/W` · `Takeoff constraint T/W` · `Vertical-climb T/W` · `Minimum-drag speed` · `Landing constraint W/S_max` · `Stall constraint W/S_max`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `field_length_service (all helpers)` · `matching_chart_service.py:41 (imported)` · `compute_chart default rho`

**Source.** 🟢 SOURCED

> ISA sea-level density; Scholz, Flugzeugentwurf 05_PreliminarySizing §5.1 and Sadraey 2013 §4.3.2 both prescribe rho_0 = 1.225 kg/m^3 as the conservative (worst-case) choice for stall/landing/ROC sizing
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
rho_0 = 1.225 kg/m^3
```

**⚠️ Divergence from the source.** Sources carry an altitude factor sigma = rho/rho_0 through every field-length and cruise equation (Sadraey Eq. 4.38, 4.47; Scholz Loftin forms). The code hard-wires sigma = 1 and has no altitude/temperature model, so every constraint is sea-level-only. Harmless for a sea-level user, silently wrong for a mountain field.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No altitude/temperature model anywhere — every field length and constraint line is hard-wired to sea-level ISA.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# kg/m³ — sea-level ISA density`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
