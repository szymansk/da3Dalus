---
name: target-static-margin-input
symbol: SM_target
kind: parameter
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
---

# Target static margin

**Definition.** User's design target for static margin; drives every SM sizing suggestion.

**Value.** `0.10`

**Formula — as the code writes it.**

```
target_sm = ctx.get("target_static_margin", 0.10)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:311` — `suggest_corrections`

**Consumed by.**

- in this graph: [[sm-delta-needed|SM shortfall to target]]
- outside it: `app/services/sm_sizing_service.py:344,374,398,402,411` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:74,77` · `app/services/assumption_compute_service.py:107,108 (cg_x = x_np - target_sm * mac)`

**Source.** 🟢 SOURCED

> rcplanedesigner.com, "Airplane Balance — Finding the First-Flight CG" § Center of Gravity and Static Margin, Mission-Consistent Static Margin table: Trainer 5 / 10 / 15 % MAC, Sport 3 / 4 / 5 %, Acrobatic 0 / 1.5 / 3 %. 0.10 is the Trainer average. Corroborated: Lennon Ch. 6 ("With CG at 25 percent MAC and NP at 35 percent, the stability margin is a healthy 10 percent"); Sadraey §6.7.1 ("Typical design practice: SM = 0.05 to 0.10").
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
SM = (x_NP − x_CG)/MAC; mission bands per table above
```

**⚠️ Divergence from the source.** The default 0.10 is a Trainer figure applied to every mission. rcplanedesigner's Sport average is 0.04 and Acrobatic 0.015 — a 0.10 default over-stabilises those by 2.5–7×. The app also carries three different defaults for the same parameter (0.10 here and at sm_suggestions.py:74, 0.12 in PARAMETER_DEFAULTS), and design_assumption.py:54 declares the unit as '% MAC' while every consumer treats it as a fraction.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three different defaults for the same parameter: 0.10 here and at sm_suggestions.py:74, but PARAMETER_DEFAULTS['target_static_margin'] = 0.12 (app/schemas/design_assumption.py:75). Its declared unit is '% MAC' (design_assumption.py:54) while every consumer treats it as a fraction.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
