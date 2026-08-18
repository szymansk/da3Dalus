---
name: cg-change-epsilon
symbol: ε_cg
kind: constant
unit: m
cluster: mass
user_visible: false
source_status: NO_SOURCE_FOUND
---

# CG-change detection epsilon

**Definition.** Minimum change in the computed design CG that triggers marking operating points DIRTY and publishing AssumptionChanged(cg_x).

**Value.** `1e-6`

**Formula — as the code writes it.**

```
if old_cg is None or abs(cg_x - old_cg) > 1e-6:
```

**Inputs.** [[cg-x-design|Design CG_x (aerodynamic CG target)]]

**Produced by.** `app/services/assumption_compute_service.py:802` — `recompute_assumptions`

**Consumed by.**

- outside it: `app/services/assumption_compute_service.py:808 (mark_ops_dirty)` · `app/services/assumption_compute_service.py:809 (event_bus.publish AssumptionChanged)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Magic number with no comment. The stored value is rounded to 4 decimals (line 204), so any change smaller than 5e-5 m cannot actually be observed on the next pass — the 1e-6 threshold is finer than the persisted resolution.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
