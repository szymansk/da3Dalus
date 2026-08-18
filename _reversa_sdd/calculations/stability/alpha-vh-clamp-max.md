---
name: alpha-vh-clamp-max
symbol: —
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# alpha_VH upper clamp

**Definition.** Upper bound applied to the tail efficiency factor.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.20`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:124` — `_alpha_vh`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

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
