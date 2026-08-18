---
name: op_xyz_ref
kind: quantity
unit: m
cluster: perf-oppoints
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-oppoints
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Operating-point moment reference

**Definition.** Moment reference point persisted with each operating point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
xyz_ref=[design_cg_x, 0.0, 0.0]
```

**Inputs.**

- [[design_cg_x|Design CG x-position]]

**Produced by.** `app/services/operating_point_generator_service.py:1027` — `_op_model_from_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/models/analysismodels.py (xyz_ref)` · `app/services/retrim_service.py` · `app/services/flight_envelope_service.py`

**Source.** 🟡 PARTIAL

> AeroSandbox 4.2 Airplane: xyz_ref is the moment reference point. Sadraey §11/§12.5: aircraft moments for trim are taken about the centre of gravity.
>
> — via `aerosandbox-expert, aircraft-design-scholz`

**The source states it as.**

```
xyz_ref = CG position (x, y, z)
```

**⚠️ Divergence from the source.** Using the CG as moment reference is sourced and correct. Hard-zeroing y and z is not: a vertically offset CG changes the thrust/drag moment arm and hence the pitch trim, and a laterally offset CG produces a rolling moment the solve then attributes to the controls. Both are discarded even when the design assumptions supply them.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** y and z of the CG are hard-zeroed, so a vertically offset CG is silently discarded even if the design assumptions provide one.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
