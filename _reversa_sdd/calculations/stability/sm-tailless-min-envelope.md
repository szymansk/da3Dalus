---
name: sm-tailless-min-envelope
symbol: —
kind: constant
unit: m
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - flag/divergence
---

# Minimum usable CG envelope

**Definition.** Absolute CG travel below which a tailless configuration is considered unusable in practice.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.005`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:64` — `_SM_TAILLESS_MIN_ENVELOPE_M`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:233,238`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source specifies a minimum absolute CG travel in millimetres. Lennon Ch. 23 makes the qualitative point (mass-fixed items on the CG, fuel tank on the CG, battery positioned mid-envelope) but gives no numeric floor. 5 mm is a plausible workshop-tolerance figure and is at least RC-scale, but it is unattributed.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# Below this absolute CG envelope width the configuration is unusable in practice
# (e.g. a micro RC plank with MAC ≈ 80 mm has only 4 mm of CG travel).`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
