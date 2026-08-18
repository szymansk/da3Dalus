---
name: alpha-vh-clamp-min
symbol: —
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# alpha_VH lower clamp

**Definition.** Lower bound applied to the tail efficiency factor.

**Value.** `0.01`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:124` — `_alpha_vh`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:124`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The code's own comment cites a typical range 0.05–0.15 but clamps at 0.01. No consulted source supplies either bound for this composite.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The comment says the typical range is 0.05–0.15 but the clamp is 0.01–0.20 — the stated justification does not match the number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Clamp to physically meaningful range (spec §A1: 0.05–0.15 typical)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
