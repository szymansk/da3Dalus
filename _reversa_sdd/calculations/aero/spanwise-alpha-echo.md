---
name: spanwise-alpha-echo
kind: parameter
unit: deg
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

# Spanwise-loads alpha echo

**Definition.** Angle of attack of the run, echoed so a follow-up sizing request reuses the same operating point.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
result_with_meta["alpha"] = float(resolved_op.alpha)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2059` — `analyze_airplane_spanwise_loads`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SpanwiseLoadsResponse.alpha` · `frontend useSpanwiseLoads`

**Source.** 🟡 PARTIAL

> Anderson 6e §4.3 (α as the independent aerodynamic variable)

**⚠️ Divergence from the source.** Echo of a request parameter; no formula to source.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
