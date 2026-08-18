---
name: tos-delta-cd0
symbol: delta_cd0
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
code_audit: WRONG_LINE
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/wrong-line
  - flag/anomaly
  - flag/divergence
---

# Area-weighted 3D drag increment

**Definition.** Wing-level ΔCD0 from per-section drag deltas weighted by section area over S_ref.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
half_span_sum += sec.delta_cd * sec.section_area_m2 / s_ref; return symmetry_factor * half_span_sum
```

**Inputs.**

- [[tos-delta-cd|Section drag delta]]
- [[bwsd-section-area-normalised|Normalised section area]]
- [[tos-symmetry-factor|Symmetric-wing doubling factor]]

**Produced by.** `app/services/turbulator_optimizer_service.py:331` — `compute_turbulator_delta_cd0`

🟠 **Corrected by the audit** — the extraction claimed `WRONG_LINE`. Original line was `328`. 

**Consumed by.**

- in this graph: `Tripped total drag coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorOptimizerSummarySchema.delta_cd0` · `app/services/assumption_compute_service.py:apply_turbulator_delta_to_cd0 (via compute_delta_cd0_from_turbulator_position)` · `frontend/components/workbench/TurbulatorEditDialog.tsx`

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §5.1 (C_D = c_d + C_D,i, with c_d the section profile drag from airfoil data) and §5.3 (C_L = (2/(V_inf*S)) * integral Gamma dy, which with c_l = 2*Gamma/(V*c) gives C_L = (1/S) * integral c_l(y) c(y) dy); Scholz, Flugzeugentwurf 05_PreliminarySizing §5.4 (parasite-drag increments referenced to S_ref)
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
Anderson's spanwise integral is stated for LIFT; the drag analogue CD_p = (1/S) * integral c_d(y) c(y) dy follows by the same strip construction but is not quoted verbatim in the consulted sources
```

**⚠️ Divergence from the source.** The area-weighted, S_ref-referenced form is standard drag-buildup practice and the lift version of the integral is directly cited, so the construction is sound. Marked PARTIAL because the drag form itself is an extension, not a quoted equation. Note the inventory's suspicion that this mixes normalisations is unfounded FOR SYMMETRIC WINGS: since bwsd-section-area-normalised forces sum(A_i) = S_ref/2, the expression 2 * sum(delta_cd_i * A_i)/S_ref reduces exactly to the area-weighted mean, matching cd_clean_avg. The real defect is the non-symmetric case (see bwsd-section-area-normalised). Sections with non-finite delta_cd or zero area are dropped silently, understating the increment.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Sections with non-finite delta_cd or zero area are dropped silently (line 327), so a partially failed sweep understates ΔCD0 with no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:322-331`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
