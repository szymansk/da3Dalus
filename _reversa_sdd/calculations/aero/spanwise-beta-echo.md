---
name: spanwise-beta-echo
kind: parameter
unit: deg
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Spanwise-loads sideslip echo

**Definition.** Sideslip angle of the run, echoed because it changes the spanwise lift distribution.

**Formula — as the code writes it.**

```
result_with_meta["beta"] = float(resolved_op.beta)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2060` — `analyze_airplane_spanwise_loads`

**Consumed by.**

- outside it: `SpanwiseLoadsResponse.beta`

**Source.** 🟡 PARTIAL

> AeroSandbox OperatingPoint (alpha, beta as the flight-condition angles); no closed-form source needed.
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Echo only.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
