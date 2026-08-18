---
name: cg-stability-fwd-stub
symbol: x_cg,fwd,stub
kind: quantity
unit: m
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

# Forward CG stability limit (0.30·MAC stub)

**Definition.** Conservative forward-CG limit placeholder: the CG at which the static margin reaches the elevator-authority ceiling of 0.30·MAC.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
cg_stability_fwd_m = x_np - _SM_ELEVATOR_LIMIT * mac
```

**Inputs.**

- [[x-np|Neutral point]]  — *⊣ limit*
- [[mac|Mean aerodynamic chord (main wing)]]
- [[sm-elevator-limit|Static-margin elevator-authority limit]]  — *⊣ limit*

**Produced by.** `app/services/loading_scenario_service.py:116` — `compute_stability_envelope`

**Consumed by.**

- in this graph: `CG envelope violation distance`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/assumption_compute_service.py:797 (fed into enrich_context, then overwritten at :485 by elevator_authority)` · `app/services/loading_scenario_service.py:217 (validate_cg_envelope)` · `app/services/loading_scenario_service.py:588/625 (CgEnvelopeRead — API response)` · `app/services/sm_sizing_service.py:483 (reads ctx['cg_stability_fwd_m'])` · `frontend/hooks/useLoadingScenarios.ts:88`

**Source.** 🟡 PARTIAL

> MECHANISM sourced: Sadraey, M.H., Wiley 2013, §11.6.3 — the forward cg limit is set by elevator effectiveness, and §11.6.3's summary table assigns 'Take-off rotation → forward cg limit, driving physics: elevator effectiveness'. Governing relation Sadraey Eqs. (11.23)–(11.25); elevator sizing case Sadraey §12.5.3. VALUE (0.30·MAC) NO_SOURCE_FOUND.
>
> — via `aircraft-design-scholz + aerodynamics-expert`

**The source states it as.**

```
δ_E = − ( C_Lα·C_mo + C_mα·C_L ) / ( C_Lα·C_mδE − C_LδE·C_mα )   (Sadraey Eq. 11.23), solved for the cg at which the available δ_E is exhausted
```

**⚠️ Divergence from the source.** Same three problems as sm-elevator-limit: the cited "Anderson §7.7" does not exist as stability material (Fundamentals of Aerodynamics 6e §7.7 is the Summary of 'Compressible Flow: Some Preliminary Aspects'); Sadraey's forward-limit case is take-off rotation, not landing stall; and Sadraey never reduces it to a fixed SM number — it is a function of elevator geometry via Eqs. (11.23)–(11.25). The code itself already knows this (gh-500 replaced it with elevator_authority_service.compute_forward_cg_limit at assumption_compute_service.py:485), but GET /cg-envelope re-derives the unsourced stub from scratch at loading_scenario_service.py:587-588 and publishes it, so the API and the context report different forward limits for the same aircraft.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Sadraey §11.6.3's forward-limit criteria are tricycle-gear runway-rotation criteria (nose lift at 80% V_TO, 6–8 deg/s², 3–4 s) drawn from GA/transport practice; many 0.5–15 kg RC/UAV aircraft never perform a nosewheel rotation. 0.30·MAC is 2–6× every RC static-margin recommendation (rcplanedesigner Trainer max 15% MAC; Lennon Ch. 6 'healthy' 10%). Unvalidated at RC/UAV scale (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** TWO PRODUCERS, DIVERGENT VALUES for the same user-visible quantity. recompute_assumptions overwrites ctx['cg_stability_fwd_m'] with elevator_authority_service.compute_forward_cg_limit (app/services/assumption_compute_service.py:485), but the REST endpoint GET /cg-envelope re-derives the stub from scratch (loading_scenario_service.py:587-588) and never reads the cached physics value. The API and the computation context therefore report different forward CG limits for the same aircraft (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"cg_stability_fwd = x_NP - 0.30 * MAC               (stub — conservative; TODO: replace with full elevator-authority calculation per Anderson §7.7 as follow-up ticket)" — app/services/loading_scenario_service.py:11-13; "Note: As of gh-500, the cg_stability_fwd_m value returned here (0.30·MAC stub) is overridden by assumption_compute_service.recompute_assumptions with a physics-based value from elevator_authority_service.compute_forward_cg_limit." — lines 93-97`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
