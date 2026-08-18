---
name: min-cd-point
symbol: CDmin
kind: quantity
unit: mixed (deg, -, -)
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Minimum drag coefficient point

**Definition.** Sweep point with the smallest CD.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
i = int(np.argmin(cd))
```

**Inputs.**

- [[cd-values|Drag coefficient array]]
- [[alpha-array|Alpha sweep array]]

**Produced by.** `app/services/analysis_service.py:120` — `_compute_cl_cd_points`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Characteristic points dict`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `alpha-sweep PNG` · `copilot_tools 'min_drag'` · `API alpha_sweep response`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 (drag polar: C_D = C_D,0 + C_L^2/(π e AR), 'C_D,0 = zero-lift drag coefficient (parasite drag at C_L = 0)')
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_D = C_D,0 + C_L^2/(π ẽ AR); for this parabolic form min(C_D) occurs at C_L = 0
```

**⚠️ Divergence from the source.** For the idealised parabolic polar CD_min and CD-at-zero-lift coincide. For a real cambered wing (and for AeroBuildup, which resolves the drag bucket) they do NOT — CD_min sits at C_L > 0. The code produces both points independently and labels the second one 'CD0'; they will differ, and neither is the parasite-drag CD0 the app owns elsewhere (gh-924).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Labelled CD0 nowhere but is the sweep minimum of TOTAL CD, not parasite drag; distinct from the drag-at-zero-lift point which the plot labels 'CD0'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
