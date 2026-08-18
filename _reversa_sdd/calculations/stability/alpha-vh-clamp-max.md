---
name: alpha-vh-clamp-max
symbol: —
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# alpha_VH upper clamp

**Definition.** Upper bound applied to the tail efficiency factor.

**Value.** `0.20`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:124` — `_alpha_vh`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:124`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Same mismatch as the lower clamp: comment says 0.05–0.15 typical, code clamps at 0.20. Unattributed.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same mismatch as the lower clamp.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Clamp to physically meaningful range (spec §A1: 0.05–0.15 typical)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
