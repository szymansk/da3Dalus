---
name: default-cd0-sizing
symbol: _DEFAULT_CD0
kind: constant
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: WRONG_FORMULA
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/wrong-formula
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Default zero-lift drag coefficient (sizing)

**Definition.** RC-typical parasite drag coefficient used when neither the request nor the aeroplane's computation context supplies cd0.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.03`

**Formula — as the code writes it.**

```
_DEFAULT_CD0 = 0.03
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:44` — `_DEFAULT_CD0`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_FORMULA`. 

**Consumed by.**

- in this graph: `Resolved zero-lift drag coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_sizing_service.py:168`

**Source.** 🟢 SOURCED

> Sadraey, M., Aircraft Design: A Systems Engineering Approach (Wiley 2013), Table 4.12, cited in §4.6 (maximum-speed sizing): typical turboprop transport C_Do ~ 0.025-0.035; the worked matching-plot example uses C_Do = 0.025.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_D = C_Do + K C_L^2 ;  C_Do ~ 0.025-0.035 (turboprop transport, Table 4.12)
```

**⚠️ Divergence from the source.** 0.03 sits at the mid-point of Sadraey's band, so the value is consistent with the source — but the source's band is for a transport-category turboprop, not for the aircraft class this app targets.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023 exposure. Sadraey's Table 4.12 C_Do = 0.025-0.035 is a transport-category figure. The RC vault gives no C_D0 number at all: Lennon (Basics of R/C Model Aircraft Design, Ch. 12) treats model parasite drag only qualitatively, emphasising that 'typical sport RC models carry far more parasite drag than builders realize' (exposed gear legs, fat tires, dowels, thick trailing edges), and the Roxxy Motoren-Fibel (Ch. 2, pp. 17-18) replaces C_D0 entirely with a measured lumped model constant MK = c_w x rho x A, giving MK ~ 0.04 (AcroMaster), 0.036 (FunCub), 0.02 (EasyGlider), 0.014 (Heron), 0.01 (Alpina). A clean transport C_D0 adopted at 0.5-15 kg scale is likely optimistic in exactly the direction Lennon warns about.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** NO_SOURCE_FOUND for 0.03. Also declared independently at powertrain_sizing_modal_service.py:33 and app/schemas/design_assumption.py:76 — three producers of the same default (ADR 0022). See notes F9: the guard test in test_endurance_service.py checks only for the old name DRAG_COEFF_ESTIMATE.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# RC-typical defaults used when neither request nor aeroplane context provides a value.`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
