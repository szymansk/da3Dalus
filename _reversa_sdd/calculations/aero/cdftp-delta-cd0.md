---
name: cdftp-delta-cd0
symbol: delta_cd0
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Installed-turbulator 3D drag increment

**Definition.** Area-weighted ΔCD0 added to the aircraft's parasite cd0 for an enabled turbulator.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_cd0 = compute_turbulator_delta_cd0(section_results, s_ref, wing_symmetric=wing_symmetric)
```

**Inputs.**

- [[cdftp-delta-cd|Section drag delta (installed turbulator)]]
- [[bwsd-section-area-normalised|Normalised section area]]
- [[tos-symmetry-factor|Symmetric-wing doubling factor]]

**Produced by.** `app/services/turbulator_optimizer_service.py:723` — `compute_delta_cd0_from_turbulator_position`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/assumption_compute_service.py:2141 apply_turbulator_delta_to_cd0` · `app/services/assumption_compute_service.py cd0 calculated value (user-visible)`

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 and §5.3; Scholz, Flugzeugentwurf 05_PreliminarySizing §5.4 (parasite-drag increments referenced to S_ref)
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
delta_CD0 = (1/S_ref) integral delta_cd(y) c(y) dy, doubled for a symmetric wing
```

**⚠️ Divergence from the source.** Same status as tos-delta-cd0 (drag strip integral is an extension of the cited lift integral). The additional concern here is authority, not form: this value MUTATES the user-visible cd0 that AeroBuildup already produced (assumption_compute_service.py:2153-2169), so one displayed number has two producers.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** This is a second producer of the user-visible cd0: AeroBuildup produces raw_cd0 and this path mutates it before storage (assumption_compute_service.py:2153-2169) — ADR 0022 one-authority risk.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:723-724`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
