---
name: max-x-wing-shift-mac
symbol: —
kind: constant
unit: – (multiples of MAC)
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

# Maximum wing shift clip

**Definition.** Intended safety clip on the per-iteration wing shift, expressed in multiples of MAC.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `5.0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:81` — `_MAX_X_WING_SHIFT_MAC`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `NONE — grep over app/, cad_designer/, scripts/ and frontend/ finds no reference other than the definition itself`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source gives a per-iteration wing-shift limit of 5 × MAC. The constant is dead — declared at sm_sizing_service.py:81 with an explicit safety purpose and never referenced (ADR 0021), so the clip it names does not exist.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** DEAD CONSTANT: declared with an explicit safety purpose and never used. The clip it names does not exist in the code (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Maximum reasonable wing shift (5× MAC per iteration, safety clip)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
