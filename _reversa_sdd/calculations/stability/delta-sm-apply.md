---
name: delta-sm-apply
symbol: Δ(SM)
kind: quantity
unit: – (fraction of MAC)
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

# Predicted SM change per apply

**Definition.** Predicted static-margin change of the current apply iteration; fed to the convergence guard and stored as history.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_sm = predicted_sm - sm_at_aft
```

**Inputs.**

- [[predicted-sm-wing-shift|Predicted SM after wing shift]]
- [[sm-at-aft|Static margin at aft CG]]

**Produced by.** `app/services/sm_sizing_service.py:884` — `apply_wing_shift`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:895 (_check_convergence_guard)` · `app/services/sm_sizing_service.py:910 (_update_convergence_counter)` · `app/services/sm_sizing_service.py:964,975,994 (htail twin)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Loop bookkeeping, not a design quantity. Note the algebra: since predicted_sm = sm_at_aft + dsm_dx·delta, this reduces identically to dsm_dx·delta — sm_at_aft cancels — so the guard compares lever magnitudes rather than actual convergence of the static margin.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Because predicted_sm = sm_at_aft + dsm_dx * delta_m, this expression algebraically reduces to `dsm_dx * delta_m` — sm_at_aft cancels. The guard therefore compares raw lever magnitudes, not actual convergence of the static margin.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `delta_sm_new: predicted SM change this iteration = predicted_sm − sm_at_aft`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
