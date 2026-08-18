---
name: flap_deflection_clipped_value
kind: quantity
unit: deg
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
  - flag/divergence
---

# Clipped flap deflection

**Definition.** Target flap deflection clamped into the governing TED mechanical limits.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
clipped_value = max(-max_neg, min(requested, max_pos))
```

**Inputs.**

- [[flap_limit_most_restrictive|Governing flap deflection limit]]  — *⊣ limit*
- [[target_flap_takeoff_deg|Takeoff flap deflection target]]
- [[target_flap_landing_deg|Landing flap deflection target]]

**Produced by.** `app/services/operating_point_generator_service.py:98` — `_clip_flap_to_ted_limit`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `FLAP_DEFLECTION_CLIPPED warning`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/operating_point_generator_service.py:639, 647 (with_control_deflections)` · `app/services/operating_point_generator_service.py:972 (controls dict)`

**Source.** 🟡 PARTIAL

> Sadraey §12.6.3: 'The unifying constraint is δ ≤ δ_max. Exceeding it requires upstream redesign' (stated for the rudder, applied generally in §12)
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Clamping to the mechanical limit is the source's own rule. Note the source says exceeding the limit should force redesign, not a silent clamp — supports emitting the warning, which the code does for flaps only.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `Epic gh-525 finding C2: the OPG historically hard-coded 15° (takeoff) and 30° (landing) flap deflections without checking the aircraft's ``TrailingEdgeDevice.positive_deflection_deg``. AVL has no internal hinge clamp and NeuralFoil silently extrapolates τ(x_h/c) past the training range`

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
