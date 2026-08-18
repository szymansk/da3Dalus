---
name: spanwise-velocity-echo
kind: parameter
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Spanwise-loads velocity echo

**Definition.** Freestream velocity injected into the integrator metadata.

**Formula — as the code writes it.**

```
result_with_meta["velocity_mps"] = float(resolved_op.velocity)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2057` — `analyze_airplane_spanwise_loads`

**Consumed by.**

- outside it: `SpanwiseLoadsResponse.velocity_mps`

**Source.** 🟡 PARTIAL

> Anderson 6e §1.5 (V_inf in q_inf); feeds q-dyn which is SOURCED.

**⚠️ Divergence from the source.** Echo only.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
