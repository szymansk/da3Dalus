---
name: delta-cm-flap
symbol: ΔCm_flap
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Flap-induced pitching moment

**Definition.** Change in pitching moment coefficient caused by deploying the flaps, evaluated at the flapped CL_max point.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_cm_flap = cm_at_cl_max - cm_baseline
```

**Inputs.**

- [[cm-baseline|Baseline pitching moment (zero deflection)]]
- [[cl-max-landing-flap|Swept flapped CL_max]]  — *⊣ limit*

**Produced by.** `app/services/elevator_authority_service.py:896` — `_run_flap_analysis`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Net nose-up moment coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/elevator_authority_service.py:646,236,310,753,767,788`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §5.12.2 — flap deflection changes the pitching moment, and the size of that change is a discriminator between flap types ("Pitching-moment change is less than a plain flap (so the tail trim load is smaller)"); §6.7.1 lists the flap/wing moment terms in the full balance. Scholz 08_HighLift §8.2 covers the associated lift increment.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
ΔC_m,flap = C_m(flaps deployed) − C_m(clean), evaluated at the same condition
```

**⚠️ Divergence from the source.** The source defines the increment at a common reference condition. The code takes C_m at the FLAPPED CL_max alpha minus a baseline at a different alpha (see cm-baseline). Separately, the AVL path hardcodes ΔC_m,flap = 0.0 (elevator_authority_service.py:1096, 1109, 1129) with the comment 'AVL path: no flap run' — so the same aircraft gets a materially different forward CG limit depending on the solver, with no warning to the user (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** AVL path hardcodes this to 0.0 (lines 1096, 1109, 1129) with the comment 'AVL path: no flap run', so the same aircraft yields a materially different forward CG limit depending on the solver — with no warning surfaced to the user.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# ΔCm_flap = Cm_deployed - Cm_clean (typically negative = nose-down)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
