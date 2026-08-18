---
name: target-sm-default-cg-envelope
symbol: SM_target,default
kind: constant
unit: fraction of MAC
cluster: mass
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/mass
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Target static margin fallback (CG envelope)

**Definition.** Fallback target static margin used by get_cg_envelope when the design assumption row is absent.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.08`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/loading_scenario_service.py:585` — `get_cg_envelope`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/loading_scenario_service.py:587 (compute_stability_envelope)` · `app/services/loading_scenario_service.py:600-601 (classify_sm)`

**Source.** 🟡 PARTIAL

> The BAND is sourced, the specific 0.08 is not. RC (authoritative for 0.5–15 kg): rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin' — Trainer 5%/10%/15% MAC (min/avg/max), Sport 3%/4%/5%, Acrobatic 0%/1.5%/3%; "First-flight floor is 5% of MAC." Lennon, A., "Basics of R/C Model Aircraft Design", Air Age 1996, Ch. 6 'CG Location' — NP 35% MAC power-on, CG 25% MAC ⇒ "stability margin is a healthy 10 percent"; "the minimum suggested margin is 5 percent." Academic: Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10 — "positive static margin required for stability (typically 5–10% of MAC)".
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**⚠️ Divergence from the source.** 0.08 falls inside the sourced 5–10% MAC band, so the value is defensible — but it corresponds to no named RC mission (above Sport max 5%, below Trainer avg 10%) and, more importantly, it is one of THREE mutually inconsistent defaults for the same parameter in this app: 0.08 here (loading_scenario_service.py:585), 0.12 in PARAMETER_DEFAULTS (app/schemas/design_assumption.py:75) and 0.10 in sm_suggestions.py:74. Since cg_stability_aft = x_np − target_sm·MAC, the aft CG limit the user is shown depends on which code path answered.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three different defaults exist for the same parameter: 0.08 here, PARAMETER_DEFAULTS['target_static_margin'] = 0.12 (app/schemas/design_assumption.py:75, used by assumption_compute_service._load_effective_assumption:1720), and 0.10 in app/api/v2/endpoints/aeroplane/sm_suggestions.py:74. Whichever path the user hits determines the aft CG limit.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
