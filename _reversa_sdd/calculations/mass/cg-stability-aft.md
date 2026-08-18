---
name: cg-stability-aft
symbol: x_cg,aft
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
---

# Aft CG stability limit

**Definition.** Aft-most longitudinal CG position the aerodynamics permits, i.e. the CG at which the static margin equals the design target.

**Formula — as the code writes it.**

```
cg_stability_aft_m = x_np - target_sm * mac
```

**Inputs.** [[x-np|Neutral point]] · [[mac|Mean aerodynamic chord (main wing)]] · [[target-static-margin|Target static margin]]

**Produced by.** `app/services/loading_scenario_service.py:112` — `compute_stability_envelope`

**Consumed by.**

- in this graph: [[cg-envelope-violation-mm|CG envelope violation distance]]
- outside it: `app/services/assumption_compute_service.py:798 (→ enrich_context_with_cg_envelope → ctx['cg_stability_aft_m'])` · `app/services/loading_scenario_service.py:210 (validate_cg_envelope)` · `app/services/loading_scenario_service.py:589/626 (CgEnvelopeRead)` · `app/schemas/loading_scenario.py:175` · `frontend/hooks/useLoadingScenarios.ts:89`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.6.2 Eq. (11.18), SM = (x_np − x_cg)/C̄ — algebraically inverted, x_cg = x_np − SM·C̄. The aft bound itself is Sadraey §11.6.2 Eq. (11.22), x_np − x_cg > 0 ("the most-aft cg is therefore bounded by the neutral point"), which follows from Eq. (11.17) C_mα = C_Lα·(X_cg − X_np) < 0. RC statement of the same relation: rcplanedesigner.com, "Airplane Balance — How to Find the Center of Gravity for an RC Airplane", §'Center of Gravity and Static Margin': "SM = (x_NP - x_CG) / MAC, positive value means CG ahead of neutral point."
>
> — via `aircraft-design-scholz + rc-aircraft-designer + aerodynamics-expert`

**The source states it as.**

```
SM = (x_np − x_cg)/C̄  (Eq. 11.18)  ⇒  x_cg = x_np − SM·C̄;  aft limit condition x_np − x_cg > 0  (Eq. 11.22)
```

**⚠️ Divergence from the source.** Two points. (1) The code's inline citation "cg_stability_aft = x_NP - target_sm * MAC (Anderson §7.5)" (loading_scenario_service.py:10) is void: Anderson, "Fundamentals of Aerodynamics" 6e §7.5 is "Definition of Total (Stagnation) Conditions" in the compressible-flow chapter; the book contains no static-margin or neutral-point material at all. The correct citation is Sadraey Eq. (11.18)/(11.22). (2) Sadraey's HARD aft limit is the neutral point (SM = 0, Eq. 11.22); the design static margin is a separate margin held against it. The code sets the aft LIMIT at the design TARGET, which conflates 'the CG I am aiming for' with 'the CG beyond which the aircraft is unstable'. That is conservative and defensible, but it means the reported aft limit moves whenever the user changes target_static_margin — the physical boundary does not.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Numerically identical to the cg_x design assumption (assumption_compute_service.py:108, cg_x = x_np - target_sm * mac) — the same formula is evaluated in two places and published under two different names (design CG vs. aft stability limit).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"cg_stability_aft = x_NP - target_sm * MAC          (Anderson §7.5)" — app/services/loading_scenario_service.py:10`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
