---
name: aero-spanwise--g-limit-default
symbol: n_limit
kind: constant
unit: g
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Default manoeuvre load factor

**Definition.** Load factor used for spar sizing when the aeroplane has no g_limit design assumption.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `3.0`

**Formula — as the code writes it.**

```
_G_LIMIT_DEFAULT = 3.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2099` — `_G_LIMIT_DEFAULT`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Effective manoeuvre load factor` · `Limit load factor (plan path)` · `Manoeuvre limit load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_spar_sizing`

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §10.4.1 Table 10.9 'Maximum positive load factor for various aircraft'
>
> — via `aircraft-design-scholz, rc-aircraft-designer`

**The source states it as.**

```
Table 10.9: GA normal n_max = 2.5–3.8 | GA utility 4.4 | GA acrobatic 6 | Home-built 2.5–5 | Remote-controlled model n_max = 1.5–2 | Transport 3–4 | Supersonic fighter 7–10
```

**⚠️ Divergence from the source.** MATERIAL. The code's 3.0 is NOT in Sadraey's remote-controlled-model band (1.5–2); it sits in the GA-normal band (2.5–3.8). No source was found for 3.0 at any scale. Cross-check from the hobbyist side contradicts it in the other direction: Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 19 gives G = 1 + (1.466·V_mph)²/(R_ft·32.2), which yields 12.1 g at 100 mph in a 60 ft radius turn — real RC manoeuvre loads far exceed 3. So 3.0 is neither the sizing convention nor the manoeuvre reality: it is unattributed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** ADR 0023. The literal is used unchanged for the whole 0.5–15 kg class. Note also that Sadraey's Table 10.9 values feed his WING-WEIGHT REGRESSION (Eq. 10.3), not a manoeuvre-load prediction, so adopting the RC row as a design load factor would itself need justification. A second copy of the 3.0 literal lives at app/services/spar_plan_service.py:36 (ADR 0022).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number with NO_SOURCE_FOUND, and a second copy of the same literal lives at app/services/spar_plan_service.py:36 whose comment points back here instead of importing it (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
