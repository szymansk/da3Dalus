---
name: rear-spar-x-c-clamped
symbol: x/c_rear
kind: quantity
unit: dimensionless (x/c)
cluster: structure
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Clamped rear-spar chord location

**Definition.** The chordwise location actually used for the rear spar: the requested x/c pulled forward to hinge − clearance when it would sit at or behind the hinge. Raises RearSparClearanceInfeasible rather than clamping when that would breach the LE floor.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
limit = control_surface_hinge_x_c - clearance
if limit < _MIN_REAR_X_C:
    raise RearSparClearanceInfeasible(...)
return min(requested_x_c, limit)
```

**Inputs.**

- [[rear-x-over-chord|Rear-spar chord fraction (requested)]]
- [[wing-hinge-x-c|Most-forward control-surface hinge]]
- [[rear-clearance-fraction|Rear-spar control-surface clearance]]
- [[min-rear-x-c|Minimum rear-spar chord location]]  — *⊣ limit*

**Produced by.** `cad_designer/airplane/geometry/spar_solver.py:255` — `rear_spar_x_c_with_clearance`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `cad_designer/airplane/geometry/spar_solver.py:743` · `app/services/spar_plan_service.py:591` · `app/schemas/spar_plan.py:198`

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §12.4.3 "Aileron Design Constraints", constraint 4; Scholz, Flugzeugentwurf, 07_WingDesign §7.4, p. 7-42
>
> — via `aircraft-design-scholz (lead)`

**The source states it as.**

```
Sadraey §12.4.3(4): the wing rear spar is the most forward limit for the aileron hinge line — equivalently the rear spar must lie forward of the hinge. Scholz §7.4: space must be left between the rear spar and the hinge line.
```

**⚠️ Divergence from the source.** The direction of the constraint (rear spar forward of hinge) matches both sources, and reporting infeasibility rather than clamping past the LE floor is consistent with them. Two things are not sourced: the numeric clearance (0.03c) and the LE floor (0.05). Also, the clamp min(requested_x_c, limit) itself is applied with no DesignWarning — a rear spar silently moved forward of the requested x/c is surfaced only implicitly via each piece's x_over_chord field, which ADR 0020 would flag as an undeclared substitution (the file already handles the infeasible branch correctly).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Both citations are transport/GA-category; the required margin at RC/UAV scale is a different physical quantity (no drive mechanism). ADR 0023.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The clamp itself (min(requested, limit)) is applied with no warning: a rear spar silently moved forward from the requested x/c is reported only implicitly, via the x_over_chord field on each piece. ADR 0020 would call for an explicit DesignWarning on the substitution, as the file already does for the infeasible branch.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Until gh-1096 the floor was applied *after* the clamp (``max(safe, _MIN_REAR_X_C)``), so a hinge near the LE silently produced a spar **behind** the hinge, inside the movable surface. ``Q-WD-8`` ② records that order as a confirmed defect.

Per RF-SP-20 an infeasible layout is reported with its governing numbers, never quietly turned into something that merely looks buildable (ADR 0012, ADR 0020).`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
