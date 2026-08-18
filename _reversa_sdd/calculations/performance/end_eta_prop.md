---
name: end_eta_prop
symbol: eta_prop
kind: constant
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-envelope
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Default propeller efficiency

**Definition.** Assumed propeller efficiency when no design assumption is set.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.65`

**Formula — as the code writes it.**

```
DEFAULT_ETA_PROP = 0.65  # APC/Folding RC-Scale, Drela/Hepperle
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:53` — `DEFAULT_ETA_PROP`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Total propulsion efficiency`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `powertrain_sizing_service.py`

**Source.** 🟡 PARTIAL

> Deters, Ananda & Selig, 'Reynolds Number Effects on the Performance of Small-Scale Propellers', AIAA 2014-2151, §V.B: small-UAV propellers rarely exceed 55-65% efficiency even at the highest tested Reynolds numbers.
>
> — via `rc, scholz`

**The source states it as.**

```
eta_prop = 0.65
```

**⚠️ Divergence from the source.** Rare good outcome: the VALUE is well-supported at RC/UAV scale (top of the measured 55-65% band) — but by a source the code does not name. The in-code attribution 'APC/Folding RC-Scale, Drela/Hepperle' is two surnames, not a citation. Note the full-scale sources disagree and must not be used here: Sadraey §8.8.1 gives 0.75-0.85 at cruise and Roxxy Motoren-Fibel Ch. 2 pp. 21-22 gives 0.75-0.80 — both would be wrong for this class. Replace the surnames with Deters et al. 2014 and the constant becomes properly RC-validated. Also duplicated as PARAMETER_DEFAULTS['prop_efficiency'] in app/schemas/design_assumption.py:88 with a different rationale.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated as PARAMETER_DEFAULTS['prop_efficiency'] = 0.65 (app/schemas/design_assumption.py:88) with a different comment ('Typical 0.55-0.75 for RC propellers at cruise'). Two constants, two rationales, one number.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"APC/Folding RC-Scale, Drela/Hepperle" — author names only, no work, chapter or equation. Not a specific citation.`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
