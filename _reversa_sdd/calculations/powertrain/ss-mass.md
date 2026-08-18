---
name: ss-mass
symbol: m
kind: quantity
unit: kg
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: derived
tags:
  - cluster/powertrain
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# All-up mass (solution space)

**Definition.** Aircraft mass from the design assumptions, or the PARAMETER_DEFAULTS mass with a warning.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
mass_kg_raw = get_effective_assumption(db, plane_id, "mass") ; if mass_kg_raw is None or float(mass_kg_raw) <= 0: warnings.append("mass not set in design assumptions. Using fallback 1.5 kg.") ; mass_kg = float(PARAMETER_DEFAULTS.get("mass", 1.5)) ; else: mass_kg = float(mass_kg_raw)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_solution_space_service.py:307` — `compute_solution_space`

**Consumed by.**

- in this graph: `Level-flight lift coefficient` · `Aerodynamic power at cruise` · `Aerodynamic power at top speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source prescribes a default aircraft mass. Sadraey (2013) §8.7 bounds the class ('because of the limited energy density of batteries, this technology is best suited to aircraft of mass less than about 30 kg') but gives no typical value. 1.5 kg is unattributed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The literal 1.5 appears twice: as the PARAMETER_DEFAULTS entry and as the .get() fallback on the same line, plus a third time in the warning string.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/schemas/design_assumption.py:73 "mass": 1.5 — NO_SOURCE_FOUND for the value itself`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
