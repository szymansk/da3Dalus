---
name: tos-delta-l-d
symbol: delta_l_d
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# L/D improvement

**Definition.** Difference between tripped and clean L/D — the UI's accept/reject criterion.

**Formula — as the code writes it.**

```
delta_l_d = l_d_tripped - l_d_clean if math.isfinite(l_d_tripped) and math.isfinite(l_d_clean) else float("nan")
```

**Inputs.** [[tos-l-d-tripped|Tripped lift-to-drag ratio]] · [[tos-l-d-clean|Clean lift-to-drag ratio]]

**Produced by.** `app/services/turbulator_optimizer_service.py:346` — `compute_ld_summary`

**Consumed by.**

- outside it: `app/schemas/turbulator_optimizer.py:TurbulatorOptimizerSummarySchema.delta_l_d` · `frontend/components/workbench/TurbulatorEditDialog.tsx:195,328-336`

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §4.12 (profile drag as a function of transition location)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
delta(L/D) between two configurations differing only in transition state
```

**⚠️ Divergence from the source.** This is the ONE defensible number in the L/D summary, because the omitted terms (induced drag, non-wing parasite drag) are identical in both states and cancel to first order — but the cancellation is only first order: with a common numerator C_L and denominators differing by delta_cd0, the delta is still overstated by roughly (C_D_true / C_D_profile)^2 relative to the true aircraft delta L/D. Since the UI uses this as the accept/reject criterion, the sign is trustworthy and the magnitude is not.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:346`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
