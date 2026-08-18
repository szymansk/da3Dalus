---
name: base-mass-default
symbol: m_base,default
kind: constant
unit: kg
cluster: mass
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/mass
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
---

# Fallback base mass for scenario CG

**Definition.** Default used when the 'mass' design assumption row is missing while evaluating loading scenarios.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/loading_scenario_service.py:355` — `compute_cg_agg_for_aeroplane / compute_loading_envelope_for_aeroplane (line 410)`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aggregate CG (default scenario)` · `Loading-scenario CG_x` · `Loading-scenario total mass`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/loading_scenario_service.py:373` · `app/services/loading_scenario_service.py:433`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Disagrees with the single authority PARAMETER_DEFAULTS['mass'] = 1.5 (app/schemas/design_assumption.py:73), which assumption_compute_service._load_effective_assumption (line 1720) uses for the same missing row. Two different fallbacks for the same parameter (ADR 0020/0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
