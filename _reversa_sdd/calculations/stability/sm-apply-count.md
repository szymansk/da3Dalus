---
name: sm-apply-count
symbol: —
kind: quantity
unit: – (count)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Apply-loop counter

**Definition.** Number of real (non-dry-run) apply operations performed since the last recompute.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
ctx["sm_apply_count"] = int(ctx.get("sm_apply_count") or 0) + 1
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:300` — `_update_convergence_counter`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:275,924,1006`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Loop counter, not a design quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The module docstring (line 35-36) claims 'A fresh recompute_assumptions call (or a change in target_static_margin) resets the counter' — no reset of sm_apply_count exists anywhere in the repo (grep finds only lines 275, 300, 924, 1006).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Each real apply increments sm_apply_count in assumption_computation_context.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
