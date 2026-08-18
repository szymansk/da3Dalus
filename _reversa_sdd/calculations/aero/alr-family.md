---
name: alr-family
symbol: —
kind: quantity
unit: enum
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - flag/divergence
  - flag/scale
---

# Airfoil family label

**Definition.** One of reflexed / symmetric / flat_bottom / semi_symmetric / cambered assigned by the geometry heuristic.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if reflex_signal_a or reflex_signal_b: return "reflexed" ... return "cambered"
```

**Inputs.**

- [[alr-aft-camber-ratio|Aft camber ratio (reflex Signal A)]]  — *⊣ limit*
- [[alr-aft-concavity|Aft camber concavity (reflex Signal B)]]
- [[alr-max-camber-pct|Max camber (classifier-internal)]]  — *⊣ limit*
- [[alr-mean-lower-abs-y|Mean |y| of lower surface]]
- [[alr-aft-quad-coeff|Aft lower-surface quadratic coefficient]]

**Produced by.** `app/services/airfoil_low_re_service.py:267` — `classify_family`

**Consumed by.**

- in this graph: `Mission family bonus`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/core/background_jobs.py:361` · `scripts/backfill_airfoil_low_re.py:128` · `suitability_service.py:476,559 (SuitabilityItem.family)` · `score_mission:918` · `frontend AirfoilSuitabilityCard.tsx / AirfoilSuitabilityFilterBar.tsx`

**Source.** 🟡 PARTIAL

> rcplanedesigner.com, 'Wing — Airfoils: Airfoils Families' (under-cambered / flat-bottom / semi-symmetrical / symmetrical); Lennon (1996), Ch. 1–2 (heavily cambered / moderately cambered / symmetrical, plus reflexed E184 for tailless)
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** The five-way taxonomy maps cleanly onto both sources — except that neither source has a 'cambered' bucket that merges under-cambered with moderately cambered, and neither offers numeric decision rules. The whole decision tree is in-repo.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Both sources are hobbyist RC material (lower authority), which is appropriate here: the taxonomy is an RC-modelling convention, not an academic classification.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `reflex_signal_a = (
    max_camber_pct >= _SYMMETRIC_MAX_CAMBER_PCT  # guard: not symmetric
    and aft_camber_ratio < _REFLEX_AFT_CAMBER_RATIO_MAX
)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
