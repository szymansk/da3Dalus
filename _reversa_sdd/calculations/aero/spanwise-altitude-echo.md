---
name: spanwise-altitude-echo
kind: parameter
unit: m
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

# Spanwise-loads altitude echo

**Definition.** Altitude injected into the integrator metadata.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Formula — as the code writes it.**

```
result_with_meta["altitude_m"] = float(resolved_op.altitude)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2058` — `analyze_airplane_spanwise_loads`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `SpanwiseLoadsResponse.altitude_m`

**Source.** 🟡 PARTIAL

> AeroSandbox asb.Atmosphere (altitude in metres, ISA); Scholz §5.6.2.
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Echo only.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
