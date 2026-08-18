---
name: spanwise-velocity-echo
kind: parameter
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-spanwise
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Spanwise-loads velocity echo

**Definition.** Freestream velocity injected into the integrator metadata.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
result_with_meta["velocity_mps"] = float(resolved_op.velocity)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2057` — `analyze_airplane_spanwise_loads`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SpanwiseLoadsResponse.velocity_mps`

**Source.** 🟡 PARTIAL

> Anderson 6e §1.5 (V_inf in q_inf); feeds q-dyn which is SOURCED.

**⚠️ Divergence from the source.** Echo only.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
