---
name: aero-model-label
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
  - solver-adjacent/avl
---

# Aerodynamic model label

**Definition.** String identifying which solver produced the strip forces.

**Derived quantity.** Computed from the inputs below.

**Value.** `"AVL" / "ASB"`

**Formula — as the code writes it.**

```
aero_model = "AVL"   /   aero_model = "ASB"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1883` — `analyze_airplane_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `StripForcesResponse.aero_model` · `frontend useStripForces`

**Source.** 🔴 NO SOURCE FOUND

> Provenance string; no domain source. Correctly identifies the producing solver, which is the ADR-0019-relevant part.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
