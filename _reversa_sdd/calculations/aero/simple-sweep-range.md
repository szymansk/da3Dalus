---
name: simple-sweep-range
kind: quantity
unit: depends on sweep_var
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
  - flag/divergence
---

# Simple-sweep variable range

**Definition.** Linear sweep of one operating-point variable from its current value.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
np.linspace(start=current_val, stop=current_val + sweep_request.step_size * sweep_request.num, num=sweep_request.num)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:1571` — `analyze_simple_sweep`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `analyse_aerodynamics` · `API /simple_sweep response`

**Source.** 🔴 NO SOURCE FOUND

> Sweep discretisation; no domain source.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Off-by-one independent of any source: the range spans step_size·num across num points, so the realised step is step_size·num/(num−1), not step_size.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The sweep spans step_size·num over num points, so the actual step is step_size·num/(num−1), not step_size; no frontend consumer was found for /simple_sweep.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
