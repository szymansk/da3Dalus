---
name: sm-classification
symbol: classification
kind: quantity
unit: enum (dimensionless)
cluster: mass
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Static-margin classification

**Definition.** 5-tier severity label of a static margin relative to the design target: error \| warn \| ok \| unknown.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if sm is None: return "unknown"; if sm < _SM_UNSTABLE_LIMIT: return "error"; if sm < target_sm: return "warn"; if sm <= _SM_HEAVY_NOSE_WARN: return "ok"; if sm <= _SM_ELEVATOR_LIMIT: return "warn"; return "error"
```

**Inputs.**

- [[mass--sm-unstable-limit|Static-margin lower (unstable) limit]]  — *⊣ limit*
- [[mass--sm-heavy-nose-warn|Static-margin heavy-nose warning limit]]  — *⊣ limit*
- [[sm-elevator-limit|Static-margin elevator-authority limit]]  — *⊣ limit*
- [[target-static-margin|Target static margin]]
- [[sm-at-fwd-api|Static margin at forward loading CG (API)]]
- [[sm-at-aft-api|Static margin at aft loading CG (API)]]

**Produced by.** `app/services/loading_scenario_service.py:61` — `classify_sm`

**Consumed by.**

- in this graph: `Overall CG-envelope classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/loading_scenario_service.py:600 / :601 (get_cg_envelope)` · `app/schemas/loading_scenario.py:31 (CG_CLASSIFICATION)` · `app/api/v2/endpoints/aeroplane/loading_scenarios.py:165` · `frontend/components/workbench/LoadingScenariosCard.tsx:85`

**Source.** 🟡 PARTIAL

> The QUANTITY being classified is sourced: Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18), SM = (x_np − x_cg)/C̄, with "a positive SM corresponds to a stable aircraft". The 5-TIER BAND itself is unattributable — no consulted source publishes a graded ok/warn/error scale for static margin.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
SM = (x_np − x_cg) / C̄   (Sadraey Eq. 11.18)
```

**⚠️ Divergence from the source.** The docstring at loading_scenario_service.py:62 claims "5-tier SM classification relative to target_sm (Scholz §4.2)". The Scholz Box Wing Systematic §4.2 material contains no tiering — only "typical stability margin requirement: 5-10% mean aerodynamic chord". The tiering is the app's own. Separately, the classification is class-independent while every RC source makes the acceptable band strongly mission-dependent (see scale_warning) — which is exactly what LoadingScenario.aircraft_class promises in its description (app/schemas/loading_scenario.py:104-106) and never delivers, since aircraft_class never reaches classify_sm.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** A single class-independent band cannot be right at RC scale. rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin' publishes three DISJOINT mission bands: Trainer 5/10/15% MAC, Sport 3/4/5% MAC, Acrobatic 0/1.5/3% MAC, with the note "These values define mission-consistent ranges, not fixed targets" and a first-flight floor of 5% MAC. Under the code's single band an Acrobatic design at its recommended 1.5% MAC is ERROR and a Sport design at its recommended 4% MAC is WARN. The 0.02/0.20/0.30 constants are GA/transport-derived (Sadraey §11.4, §11.6.1) and unvalidated at 0.5–15 kg (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The thresholds are class-independent although LoadingScenario.aircraft_class is documented as "Aircraft class for template selection and SM thresholds" (app/schemas/loading_scenario.py:104-106). aircraft_class only reaches loading_template_service.get_templates_for_class; classify_sm never sees it — the field name/description contradicts the behaviour.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"5-tier SM classification relative to target_sm (Scholz §4.2)." — app/services/loading_scenario_service.py:62`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
