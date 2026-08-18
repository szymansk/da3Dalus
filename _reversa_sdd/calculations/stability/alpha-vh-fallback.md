---
name: alpha-vh-fallback
symbol: —
kind: constant
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - flag/anomaly
  - flag/divergence
---

# alpha_VH fallback

**Definition.** Value returned for the tail efficiency factor when tail or reference area is missing or non-positive.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.10`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:120` — `_alpha_vh`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:120`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source gives 0.10 as a default for this composite. The nearest literature default for the quantity the code names ('tail efficiency') is η_h = 0.85–0.95 (Sadraey §6.7.1) or Lennon's HTE 40–90 % (Ch. 7) — an order of magnitude away, confirming that α_VH is not that quantity. Substitution is silent (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback — silently substitutes a typical value with no DesignWarning (ADR 0020). No source for 0.10.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `return 0.10  # fallback typical value`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
