---
name: alr-score-cl-max-ref
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

# CL_max reference for re_agnostic

**Definition.** Section CL_max that maps to a full 1.0 on the CL_max component.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.5`

**Formula — as the code writes it.**

```
CL_MAX_REF = 1.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:856` — `score_re_agnostic`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `re_agnostic suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `score_re_agnostic:866`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source for 1.5. Also re-hardcoded at score_mission:935 as cl_max/1.5 — two producers of one reference (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Lennon (1996) Ch. 2 states symmetrical sections have lower C_l,max than cambered ones by construction. A single family-independent 1.5 therefore penalises the symmetric sections that the aerobatic mission deliberately prefers.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Same 1.5 is re-hardcoded in score_mission:935 (`cl_norm = min(cl_max / 1.5, 1.0)`) — two producers of the same reference.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `CL_MAX_REF = 1.5`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
