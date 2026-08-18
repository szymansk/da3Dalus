---
name: strip-forces-wing-name
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Strip-forces wing name

**Definition.** Label identifying which wing the strip forces belong to.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
wing_name=aircraft.name   (airplane path)   /   wing_name=wing_name   (single-wing path)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1895` — `analyze_airplane_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `StripForcesResponse.wing_name` · `frontend useStripForces`

**Source.** 🔴 NO SOURCE FOUND

> Label field, not a calculation. The naming defect (aircraft.name on the airplane path at 1895 vs the real wing name at 1979) is a code issue with no source dimension.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Name contradicts its definition on the airplane path: the field called wing_name is filled with the AIRCRAFT name (line 1895) while analyze_wing_strip_forces fills it with the real wing name (line 1979).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
