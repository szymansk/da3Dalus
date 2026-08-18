---
name: tos-global-xtr-opt
symbol: global_xtr_opt
kind: quantity
unit: x/c
cluster: aero-strips
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Whole-wing optimal trip position

**Definition.** A single trip position optimised at the representative (cl, Re) and applied to every section.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
rep_result = optimize_section_xtr(rep_airfoil, cl=cl_rep, re=re_rep, xtr_grid=xtr_grid); global_xtr_opt = rep_result.xtr_opt
```

**Inputs.**

- [[tos-re-rep|Representative Reynolds number (whole scope)]]
- [[tos-cl-rep|Representative lift coefficient (whole scope)]]
- [[tos-xtr-grid|Turbulator trip-position sweep grid]]

**Produced by.** `app/services/turbulator_optimizer_service.py:559` — `run_turbulator_optimizer`

**Consumed by.**

- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorSectionResult.xtr_opt`

**Source.** 🟡 PARTIAL

> RC-Network Wiki, 'Turbulator (Aerodynamik)' (a turbulator is a physical strip whose position must match where transition would otherwise be delayed); Anderson, Fundamentals of Aerodynamics 6e, §4.12.3 (transition location depends on local pressure gradient, roughness and Re)
>
> — via `rc-aircraft-designer, aerodynamics-expert`

**⚠️ Divergence from the source.** A single spanwise trip line is a legitimate manufacturing simplification (tape is applied as a straight strip) and no source forbids it. Two unsourced choices remain: the representative airfoil is the MIDDLE SECTION BY LIST INDEX, not by area or MAC, so a multi-airfoil wing can be optimised on a profile that carries almost no area; and applying one (cl, Re) optimum to every section ignores that the cited transition physics is local.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The representative airfoil is the MIDDLE section by list index (line 554), not by area or MAC, so a multi-airfoil wing can be optimised on an unrepresentative profile.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:553-559`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
