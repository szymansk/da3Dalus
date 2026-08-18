---
name: stability--sm-unstable-limit
symbol: —
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: PARTIAL
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# SM instability threshold

**Definition.** Static margin below which the design is declared unstable and saving is blocked.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.02`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:53` — `_SM_UNSTABLE_LIMIT`

**Consumed by.**

- in this graph: `Static-margin classification`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:373,387,516,522,527,539`

**Source.** 🟡 PARTIAL

> The zero-SM instability boundary itself is Sadraey §11.6.2 Eq. 11.22. The specific value SM = 0.02 is not attributable. Nearest attributable statement: Sadraey §11.4 — "A conventional aircraft becomes dynamically longitudinally unstable when the cg lies within roughly 2–3 % MAC of the neutral point." That sentence supports a 2–3 % *dynamic* caution band, not a 2 % hard block-save threshold.
>
> — via `aircraft-design-scholz + rc-aircraft-designer`

**The source states it as.**

```
Static instability at SM ≤ 0 (Eq. 11.22); dynamic instability within ~2–3 % MAC of the NP (§11.4)
```

**⚠️ Divergence from the source.** The code treats 0.02 as a hard error that blocks saving. Sadraey treats 2–3 % MAC as the onset of *dynamic* instability, and rcplanedesigner.com explicitly allows Acrobatic RC models down to 0 % MAC (neutral stability) — so at RC scale a 2 % block is stricter than the hobbyist source and looser than "statically unstable". The code's own comment in the duplicate (loading_scenario_service.py:51, "Phugoid divergent") attributes it to the phugoid mode; no consulted source ties phugoid divergence to SM = 0.02.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Duplicated verbatim in loading_scenario_service.py:51 (`_SM_UNSTABLE_LIMIT = 0.02  # below → ERROR (Phugoid divergent)`) — two independent producers of the same threshold. No cited source in either place.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# below → ERROR, block_save`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
