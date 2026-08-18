---
name: sm-convergence-threshold
symbol: —
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Apply-loop convergence threshold

**Definition.** Change in predicted SM delta below which the apply loop is judged stalled.

**Value.** `0.005`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:94` — `_SM_CONVERGENCE_THRESHOLD`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:283`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Numerical tolerance, unattributed. For context, 0.005 (0.5 % MAC) is one tenth of the smallest RC design band width (rcplanedesigner Acrobatic 0–3 % MAC), so it is at least dimensionally sane — but no source states it.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `_SM_CONVERGENCE_THRESHOLD = 0.005  # \|Δ(delta_sm)\| < 0.5% → converged / stuck`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
