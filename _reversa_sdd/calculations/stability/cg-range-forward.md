---
name: cg-range-forward
symbol: x_cg_fwd
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Forward CG limit from margin bounds

**Definition.** Most-forward (most stable) CG position, derived from the neutral point and the maximum allowed static margin.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
forward = np_x - (max_margin / 100) * mac
```

**Inputs.**

- [[neutral-point-x-solver|Neutral point (solver)]]
- [[mac-solver-cref|MAC (solver reference chord)]]
- [[max-static-margin-pct-default|Maximum static margin (CG-range default)]]  — *⤵ fallback*

**Produced by.** `app/services/stability_service.py:97` — `compute_cg_range`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/stability_service.py:334,351` · `app/services/copilot_tools.py:463` · `frontend/components/workbench/MarkerDetailBox.tsx:88 (component never mounted)`

**Source.** 🟡 PARTIAL

> Algebraic inversion of Sadraey §11.6.2 Eq. 11.18 (SM = (x_np − x_cg)/C̄ ⇒ x_cg = x_np − SM·C̄). The *concept* of a forward CG limit: Sadraey §11.6.3.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
x_cg = x_np − SM · C̄  (rearranged Eq. 11.18)
```

**⚠️ Divergence from the source.** The algebra is Sadraey's; the physics is not. Sadraey §11.6.3 sets the FORWARD CG limit from elevator effectiveness during take-off rotation, not from a maximum permitted static margin. No consulted source derives a forward limit from an SM ceiling, and no source names 25 % as that ceiling.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Competes with elevator_authority_service's physics forward limit and loading_scenario_service's 0.30·MAC stub — three different definitions of 'forward CG limit' (see notes F1, F3).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Forward limit = NP_x − (max_margin / 100) × MAC  (most stable)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
