---
name: mass-kg-ctx
symbol: m
kind: quantity
unit: kg
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/not-verified
---

# Published aircraft mass (computation context)

**Definition.** The effective mass republished into assumption_computation_context so downstream consumers do not have to fall back to the frequently-null AeroplaneModel.total_mass_kg column.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"mass_kg": round(mass, 3) if mass is not None and mass > 0 else None
```

**Inputs.**

- [[mass-effective|Effective aircraft mass]]  — *⤵ fallback*

**Produced by.** `app/services/assumption_compute_service.py:714` — `recompute_assumptions`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- outside it: `app/services/mission_kpi_service.py:451 (_kpi_wing_loading)` · `app/services/field_length_service.py:516` · `app/api/v2/endpoints/aeroplane/field_lengths.py:147` · `app/api/v2/endpoints/aeroplane/speed_polar.py:92` · `app/services/suitability_service.py:326` · `app/services/matching_chart_service.py:618`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 — ΣW_i = W_TO; the aircraft mass is the single quantity that feeds performance (Scholz, D., "Flugzeugentwurf" (HAW Hamburg), Design Sequence §2.2 Step 10, 'Connection to Other Design Steps': mass and balance outputs feed the performance iteration and the final performance checks).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΣW_i = W_TO   (Sadraey §11.2)
```

**Cited in the code itself.** `"gh-625 Bug B: publish the effective `mass` design assumption to the context so consumers (mission KPI _kpi_wing_loading, field_length_service.compute_field_lengths_for_aeroplane introduced in gh-548, _kpi_field_friendliness) can find it without falling back to the AeroplaneModel.total_mass_kg column that is None on most aeroplanes." — app/services/assumption_compute_service.py:708-713`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
