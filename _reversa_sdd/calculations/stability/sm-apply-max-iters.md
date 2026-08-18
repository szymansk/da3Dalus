---
name: sm-apply-max-iters
symbol: —
kind: constant
unit: – (count)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Apply-loop iteration cap

**Definition.** Number of apply operations after which the convergence guard becomes active.

**Value.** `3`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:93` — `_SM_APPLY_MAX_ITERS`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:276`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Numerical loop guard, not a design quantity. Sadraey §6.7.1/§12.5.5 describe the design loop as iterating to convergence with no fixed iteration count. 3 is unattributed.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# Convergence guard (spec-gate A6, gh-509)
_SM_APPLY_MAX_ITERS = 3  # maximum apply calls before convergence check fires`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
