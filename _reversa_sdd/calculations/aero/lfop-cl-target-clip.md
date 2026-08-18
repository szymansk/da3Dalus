---
name: lfop-cl-target-clip
symbol: —
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Target CL clamp

**Definition.** Target CL is clamped into [0.1, 2.0].

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.1 … 2.0`

**Formula — as the code writes it.**

```
cl_target = float(np.clip(cl_target, 0.1, 2.0))
```

**Inputs.**

- [[lfop-cl-target|Level-flight target lift coefficient]]

**Produced by.** `app/services/section_aoa_service.py:504` — `_resolve_level_flight_op`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Trimmed alpha from CL-target solve` · `CL residual for the root search`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> Scholz, Flugzeugentwurf, 08_HighLift §8.2 (c_L,max,clean is an airfoil property taken from measured catalogue data, e.g. Abbott 1959, or estimated by the DATCOM 1978 method — not a universal constant)
>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source supports either bound. The lower clamp at 0.1 masks an over-speed design; the upper clamp at 2.0 masks an over-loaded one. Both then feed brentq as if they were the real requirement.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** C_L = 2.0 is unreachable for a clean unflapped wing at this scale. Clean 2D c_l,max for typical RC sections at Re 5e4-3e5 is roughly 1.2-1.6, and the 3-D wing value is lower still; the 3-D CL,max of a 0.5-15 kg model is realistically well under 1.5. Clamping to 2.0 therefore converts a genuinely infeasible design into a silently trimmed one instead of raising an infeasibility warning.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Undeclared clamp: an overloaded design silently gets CL=2.0 instead of an infeasibility warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:504`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
