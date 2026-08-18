---
name: drag-at-zero-lift-point
symbol: CD0
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

# Drag at zero lift point

**Definition.** CD interpolated linearly at the first CL sign change (labelled 'CD0' in the diagram).

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
t = 0.0 if abs(cl1 - cl0) <= 1e-12 else -cl0 / (cl1 - cl0); alpha_deg = alpha[i] + t * (alpha[i+1] - alpha[i]); CD = cd[i] + t * (cd[i+1] - cd[i])
```

**Inputs.**

- [[cl-values|Lift coefficient array]]
- [[cd-values|Drag coefficient array]]
- [[alpha-array|Alpha sweep array]]
- [[divide-guard-epsilon|Division guard epsilon]]  — *ε tolerance*

**Produced by.** `app/services/analysis_service.py:149` — `_interpolate_zero_crossing`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Characteristic points dict`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `alpha-sweep PNG polar panel` · `API alpha_sweep response`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 ('C_D,0 = zero-lift drag coefficient (parasite drag at C_L = 0)')
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_D = C_D,0 + r*C_L^2 + C_L^2/(π e AR)  ⇒  C_D(C_L=0) = C_D,0
```

**⚠️ Divergence from the source.** Anderson's C_D,0 is the PARASITE term of the fitted polar. The code reports the solver's TOTAL C_D linearly interpolated at the CL sign change, which additionally contains any residual induced/trim drag at C_L=0 and, for a cambered aircraft, is not the minimum. Labelling it 'CD0' in the diagram makes it a second producer of a quantity the app already owns (ADR 0022 / gh-924).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Labelled 'CD0' (_LABEL_NAMES:59) but is CD at CL=0 of the whole aircraft including induced/zero-lift terms — a second producer of a 'cd0' the app already owns elsewhere (memory: gh-924 single cd0 authority).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
