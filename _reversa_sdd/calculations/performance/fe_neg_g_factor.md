---
name: fe_neg_g_factor
symbol: -0.4
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
  - flag/scale
---

# Negative g-limit ratio

**Definition.** Ratio of negative to positive structural limit load factor.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `-0.4`

**Formula — as the code writes it.**

```
max(..., -0.4 * g_limit)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:328` — `compute_vn_curve`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Negative gust-critical trigger` · `Negative maneuver load factor`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013) §10.4.1, 'Negative Load Factors': negative limit is 'typically about 0.4x the positive maximum for transports'. Matching regulatory rule FAR/CS 23.337(b)(1) for normal/utility category.
>
> — via `scholz, rc`

**The source states it as.**

```
n_neg = -0.4 * n_pos
```

**⚠️ Scale (ADR 0023).** ADR 0023: Sadraey states the 0.4 for TRANSPORTS, and 23.337(b) for certified normal/utility GA. Same section notes acrobatic GA reaches -3 g, i.e. a ratio near -0.5 to -0.75. For RC the relevant case is again the symmetrical-airfoil aerobatic model, which is structurally and aerodynamically closer to the acrobatic category than to transports. -0.4 is defensible for a trainer, optimistic for an aerobat. Also appears three times uncited (fe:328, 260, 266).

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number appearing three times (lines 328, 260, 266) with no citation, although the identical -0.4·n rule exists in FAR/CS-23.337(b) for the normal category. Uncited and unvalidated at RC scale.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
