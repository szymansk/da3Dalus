---
name: cl-a-guard-epsilon
symbol: —
kind: constant
unit: 1/rad
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/stability
  - class/numerical-tolerance
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# CL_alpha division guard

**Definition.** Minimum \|CL_alpha\| below which the derivative-based static margin is not computed.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-6`

**Formula — as the code writes it.**

```
if has_cm_a and abs(cl_a) > 1e-6:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:145` — `classify_stability`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Static margin from derivatives`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/trim_enrichment_service.py:145`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Numerical division guard, unattributed. For context, Sadraey §6.7.4 Eq. 6.57 gives C_Lα of order 4–6 1/rad for real surfaces, so 1e-6 is ~7 orders of magnitude below any physical value — it guards only against exactly-zero/absent data. The real defect is that `stability_derivatives.get("CL_a", 0.0)` defaults to 0.0, so absent and genuinely-zero are indistinguishable and both silently suppress the static margin.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** `cl_a = stability_derivatives.get("CL_a", 0.0)` (line 138) defaults to 0.0, so an absent CL_a is indistinguishable from a genuinely zero one — both silently suppress the static margin with no warning.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
