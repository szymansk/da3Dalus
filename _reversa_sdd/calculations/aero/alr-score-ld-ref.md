---
name: alr-score-ld-ref
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-polars
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# L/D reference for re_agnostic

**Definition.** L/D that maps to a full 1.0 on the L/D component.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `60.0`

**Formula — as the code writes it.**

```
LD_REF = 60.0  # excellent L/D at low Re
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:855` — `score_re_agnostic`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `re_agnostic suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_re_agnostic:863`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 'Excellent L/D at low Re' is a description, not a citation. Anderson's (L/D)_max relation is a wing formula and cannot supply a section reference; neither RC source quotes a section L/D target.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** A single Re-independent L/D reference across a 40k–750k grid is untenable — section L/D at Re 40k is far below the same section's value at Re 750k, so low-Re-optimised sections are systematically under-scored (ADR 0023).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic reference described only as 'excellent L/D at low Re', no source and no RC/UAV-scale validation (ADR 0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `LD_REF = 60.0  # excellent L/D at low Re`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
