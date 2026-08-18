---
name: stability--sm-heavy-nose-warn
symbol: —
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# SM heavy-nose warning threshold

**Definition.** Upper end of the acceptable SM band; above this the tool offers an overshoot (nose-heavy) correction.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.20`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:54` — `_SM_HEAVY_NOSE_WARN`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Static-margin classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:398,402`

**Source.** 🟡 PARTIAL

> No source names 0.20 as a nose-heavy threshold. Attributable neighbours: exam-tail-volume-coefficient / Sadraey §6.7.1 — "Typical design practice: SM = 0.05 to 0.10 … Too high (>0.12): excessive stability makes aircraft sluggish"; rcplanedesigner.com "Airplane Balance" mission table — Trainer maximum 15 % MAC.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
SM design band 0.05–0.10; sluggish above ~0.12 (Sadraey §6.7.1)
```

**⚠️ Divergence from the source.** The literature's 'too much stability' onset is ~0.12 (Sadraey) or 0.15 (RC trainer maximum). The code warns only above 0.20, so the whole 0.12–0.20 band — sluggish by both authorities — passes silently. Also disagrees with the same app's trim_enrichment_service margin_high_threshold = 0.30.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated verbatim in loading_scenario_service.py:52. No cited source.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# above → overshoot suggestion`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
