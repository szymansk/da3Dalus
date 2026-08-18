---
name: mass--g-limit
symbol: n_limit
kind: parameter
unit: g
cluster: mass
user_visible: true
source_status: SOURCED
node_class: user-input
tags:
  - cluster/mass
  - class/user-input
  - source/sourced
  - surface/user-visible
  - flag/divergence
  - flag/scale
---

# Design load factor limit

**Definition.** User-chosen structural load-factor limit. Pure design choice (DESIGN_CHOICE_PARAMS) — never auto-calculated.

**User input.** Supplied from outside the calculation (assumption store or request), not derived.

**Value.** `3.0 (app/schemas/design_assumption.py:78)`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/assumption_compute_service.py:645` — `recompute_assumptions (_load_effective_assumption)`

**Consumed by.**

- in this graph: `Design bending moment` · `Design limit load factor (published)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:646 (_compute_v_a: V_a = V_s1·√n_max)` · `app/services/assumption_compute_service.py:719 (ctx['flight_envelope_n_max'])` · `frontend design-assumptions panel`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §10.4.1, Table 10.9 ('Maximum Load Factor by Aircraft Category'): GA normal 2.5–3.8; GA utility 4.4; GA acrobatic 6; Home-built 2.5–5; Remote-controlled model 1.5–2; Transport 3–4; Supersonic fighter 7–10. Eq. (10.4): n_ult = 1.5 · n_max. Sadraey's stated rationale for the RC row: "RC model: low maneuvering loads but designers often use n_max = 1.5–2 to keep structure light." Real RC manoeuvre loads for contrast: Lennon, A., "Basics of R/C Model Aircraft Design", Air Age 1996, Ch. 19 — G = 1 + (1.466·V_mph)²/(R_ft·32.2), giving 12.1 g at 100 mph in a 60 ft radius turn; Ch. 21 — a 45° coordinated level turn gives sqrt(1²+1²) = 1.414 g.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
n_ult = 1.5 · n_max   (Sadraey Eq. 10.4);  n_max by category, Table 10.9;  G = 1 + (1.466·V_mph)² / (R_ft · 32.2)   (Lennon Ch. 19)
```

**⚠️ Divergence from the source.** The parameter is sourced but the DEFAULT VALUE is taken from the wrong row. PARAMETER_DEFAULTS['g_limit'] = 3.0 (app/schemas/design_assumption.py:78) sits in Sadraey's GA-normal band (2.5–3.8) and above his Remote-controlled model row (1.5–2). Unlike its neighbours power_to_weight and prop_efficiency, it carries no source comment. Sadraey's RC value is moreover a structural-sizing convention feeding the weight regressions, not a statement about achievable flight loads — Lennon Ch. 19's own RC formula produces 12.1 g in a realistic model manoeuvre. So 3.0 is simultaneously above Sadraey's RC sizing figure and far below Lennon's RC manoeuvre loads; neither source supports it. Separately, nothing in this cluster applies Sadraey's mandatory ×1.5 to reach n_ult.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** The adopted value 3.0 corresponds to Sadraey Table 10.9's GA-normal category (2.5–3.8), not to the Remote-controlled model row (1.5–2) that covers this app's 0.5–15 kg target. That is precisely the ADR 0023 failure mode: a transport/GA-category number adopted where the same table offers an RC row. It is also unsafe in the opposite direction — Lennon Ch. 19 (an RC source) computes 12.1 g for a 100 mph / 60 ft-radius model turn, so a structure sized to 3.0 g (n_ult 4.5) is under-designed for real RC aerobatics. The constant needs an explicit RC/UAV provenance note stating which of the two RC interpretations it encodes.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
