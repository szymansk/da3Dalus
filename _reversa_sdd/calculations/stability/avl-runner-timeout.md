---
name: avl-runner-timeout
symbol: —
kind: constant
unit: s
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
  - solver-adjacent/avl
---

# AVL run timeout

**Definition.** Wall-clock limit for each AVL invocation in the elevator-authority path.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `60`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/elevator_authority_service.py:1042` — `_compute_forward_cg_limit_avl`

**Consumed by.**

- outside it: `app/services/elevator_authority_service.py:1046,1053`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `none — not a design quantity`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Process wall-clock limit; not an engineering quantity and not covered by any aerodynamic source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Magic value, no source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
