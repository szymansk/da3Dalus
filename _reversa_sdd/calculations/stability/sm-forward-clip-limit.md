---
name: sm-forward-clip-limit
symbol: —
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Forward-CG SM clip limit

**Definition.** Maximum static margin allowed at the forward CG before a wing shift is clipped.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.30`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:78` — `_SM_FORWARD_CLIP_LIMIT`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Clipped wing shift`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:427,431,434`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No consulted source names SM = 0.30 as any kind of limit. Sadraey §6.7.1 calls SM > 0.12 already sluggish; rcplanedesigner.com's largest RC mission maximum is 15 % MAC (Trainer). 30 % MAC is double the highest RC value found and beyond the transport CG-envelope width. The code's own module header (elevator_authority_service.py:39) calls this constant "the hardcoded 0.30 orphan" that gh-500 was meant to retire.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Fourth copy of the 0.30 constant (with elevator_authority_service._STUB_FORWARD_SM:93, loading_scenario_service._SM_ELEVATOR_LIMIT:53, trim_enrichment_service.margin_high_threshold:394). elevator_authority_service.py:39 explicitly calls this one 'the hardcoded 0.30 orphan' that gh-500 was supposed to retire — but gh-500's replacement never produces a value (see notes F1), so the orphan is still the operative number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Forward stability stub limit: SM = 0.30 (see loading_scenario_service.py)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
