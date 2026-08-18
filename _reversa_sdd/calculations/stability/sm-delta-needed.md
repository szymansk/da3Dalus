---
name: sm-delta-needed
symbol: ΔSM
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: false
source_status: SOURCED
---

# SM shortfall to target

**Definition.** Static margin change required to reach the target from the current aft-CG value.

**Formula — as the code writes it.**

```
delta_needed = target_sm - sm_at_aft
```

**Inputs.** [[target-static-margin-input|Target static margin]] · [[sm-at-aft|Static margin at aft CG]]

**Produced by.** `app/services/sm_sizing_service.py:411` — `suggest_corrections`

**Consumed by.**

- in this graph: [[delta-sh-m2|Required horizontal tail area change]] · [[delta-x-wing-shift|Required wing longitudinal shift]]
- outside it: `app/services/sm_sizing_service.py:412,413` · `app/services/sm_sizing_service.py:374,378,379 (duplicate in the error branch)`

**Source.** 🟢 SOURCED

> Trivial inversion of the sourced static-margin definition (Sadraey §11.6.2 Eq. 11.18); the iterate-to-target structure is Sadraey §6.7.1 ("Because both wing geometry and CG position depend on tail geometry (and vice versa), Eq. 6.29 is solved repeatedly during the iterative aircraft-design loop").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΔSM = SM_target − SM_current
```

**Cited in the code itself.** `# Invert: ΔSM = target_sm - sm_at_aft → Δlevers`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
