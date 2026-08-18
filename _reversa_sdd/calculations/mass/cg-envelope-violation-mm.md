---
name: cg-envelope-violation-mm
symbol: Δx_violation
kind: quantity
unit: mm
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
---

# CG envelope violation distance

**Definition.** How far the loading CG lies outside the stability envelope, converted to millimetres for the warning text.

**Derived quantity.** Computed from the inputs below.

**Value.** `1000 (m→mm factor, lines 211 and 218)`

**Formula — as the code writes it.**

```
excess_mm = round((cg_loading_aft_m - cg_stability_aft_m) * 1000, 1)   # forward branch: excess_mm = round((cg_stability_fwd_m - cg_loading_fwd_m) * 1000, 1)
```

**Inputs.**

- [[cg-loading-aft|Aft loading CG]]
- [[cg-stability-aft|Aft CG stability limit]]  — *⊣ limit*
- [[cg-loading-fwd|Forward loading CG]]
- [[cg-stability-fwd-stub|Forward CG stability limit (0.30·MAC stub)]]  — *⊣ limit*

**Produced by.** `app/services/loading_scenario_service.py:211` — `validate_cg_envelope`

**Consumed by.**

- outside it: `app/services/loading_scenario_service.py:212-222 (warning strings)` · `app/services/loading_scenario_service.py:611 → CgEnvelopeRead.warnings` · `frontend/hooks/useLoadingScenarios.ts:93 (warnings)`

**Source.** 🟡 PARTIAL

> The CONTAINMENT TEST is sourced: Sadraey, M.H., Wiley 2013, §11.3.2 — "Any point outside the polygon is forbidden and can lead to an unavoidable crash. Loading the cg or total weight outside the envelope is one of the most common causes of cg-related accidents." The reporting of the violation as a signed distance in mm has no source.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Δx_cg = (x_cg_aft − x_cg_for) / C̄   (Sadraey Eq. 11.16) — the source's way of expressing a cg distance
```

**⚠️ Divergence from the source.** Sadraey consistently non-dimensionalises longitudinal cg distances by MAC: Eq. (11.11)–(11.13) for cg positions, Eq. (11.16) for the cg range, and the §11.6.1 class table entirely in % MAC. A violation reported in millimetres is not comparable across designs and cannot be read against any of the published limits; the natural unit is Δx/C̄ (i.e. an SM excess). The warning text is also stale on one path: it says "(stub limit)" at loading_scenario_service.py:222 regardless of whether the forward limit came from the 0.30·MAC stub or from elevator_authority_service.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The forward-branch warning text says "(stub limit)" (line 222) even when ctx already holds the physics-based elevator-authority limit — but validate_cg_envelope is called (assumption_compute_service.py:611 path via get_cg_envelope) with the stub value, so the text is accurate there and stale in the ctx path.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
