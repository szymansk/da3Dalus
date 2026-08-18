---
name: sm-tailless-target
symbol: SM_target,tailless
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Tailless SM target

**Definition.** Recommended static margin for tailless / flying-wing configurations, taken as the midpoint of the 5–10 % MAC band.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.075`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:58` — `_SM_TAILLESS_TARGET`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:245` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:95 (target_static_margin field)`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (Air Age 1996) Ch. 23 — CG Range and Static Margin for Tailless Aircraft: "SM = 5% to 10% of wing MAC for tailless designs." 0.075 is the midpoint of that band.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
SM_tailless = 5–10 % MAC (Lennon Ch. 23)
```

**⚠️ Divergence from the source.** Lennon states a band, not a single target; the midpoint is the code's choice. The code's comment credits four authorities ("Anderson + Apogee + Scholz + Lennon") — only the Lennon attribution is verifiable from the consulted vaults, and Anderson's "Fundamentals of Aerodynamics" contains no static-margin treatment at all (see sm-at-aft / dsm-dx-wing).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No frontend consumer — the sm-suggestion endpoint is not called anywhere in frontend/ (see notes F6).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Tailless / flying-wing SM target (gh-579, Anderson + Apogee + Scholz + Lennon)
# All four authorities converge on SM = 5–10% MAC for tailless designs.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
