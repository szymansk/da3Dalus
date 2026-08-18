---
name: t_static_mean_factor
symbol: k_T
kind: constant
unit: dimensionless
cluster: perf-matching
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/perf-matching
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Static-thrust de-rate factor

**Definition.** Multiplier applied to supplied static thrust before computing T/W in the ground roll.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.0`

**Formula — as the code writes it.**

```
_T_STATIC_MEAN_FACTOR: float = 1.0  # T as supplied (factor encoded in 1.21 constant)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/field_length_service.py:101` — `_T_STATIC_MEAN_FACTOR`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Effective mean thrust`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_compute_s_to_ground:201`

**Source.** 🔴 NO SOURCE FOUND

> No source. The de-rate it is meant to represent is real (a propeller's mean thrust over the ground roll is well below zero-airspeed static thrust) but neither Scholz nor Sadraey gives a T_mean/T_static factor; Sadraey instead integrates thrust explicitly (Eq. 4.66).
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The value 1.0 was chosen to make a Cessna 172N test reproduce, and justified by the claim that the factor is 'encoded in 1.21'. That justification is false - 1.21 is (1.1)^2, a kinematic factor. So the RC-propeller de-rate the comment documents (~0.75) is genuinely missing, not absorbed. Multiplying by 1.0 is also inert code (ADR 0021).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** A GA-airframe calibration is actively overriding RC-specific propeller physics that the code's own comment states. Direct ADR 0023 finding.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** The comment states RC props need ≈0.75, but the value was set to 1.0 to make a Cessna 172N test reproduce — a GA calibration overriding the RC-specific physics; the multiplication by 1.0 is also inert code (ADR 0021/0023).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"For RC propellers, T_mean ≈ 0.75 · T_static_zero_velocity. … To reproduce T/W = 0.178 in the test, we set _T_STATIC_MEAN_FACTOR = 1.0 (pass-through)."`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
