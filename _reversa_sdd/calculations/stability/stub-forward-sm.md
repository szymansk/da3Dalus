---
name: stub-forward-sm
symbol: —
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Stub forward static margin

**Definition.** Conservative forward static-margin used when no physics-based limit can be computed.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.30`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:93` — `_STUB_FORWARD_SM`

**Consumed by.**

- outside it: `app/services/elevator_authority_service.py:362`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Same as sm-forward-clip-limit: no source names SM = 0.30 as a conservative forward limit. Sadraey §6.7.1 calls SM > 0.12 sluggish; the largest RC mission maximum found is 0.15 (rcplanedesigner Trainer). Third of four independent copies of this constant in the cluster.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third copy of 0.30 (notes F3), and its only consumer (_build_stub_result) is unreachable (notes F1).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Conservative stub forward SM = 0.30 (same as old loading_scenario stub)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
