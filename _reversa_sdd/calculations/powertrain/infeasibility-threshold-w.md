---
name: infeasibility-threshold-w
symbol: 0.1
kind: constant
unit: W
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - flag/anomaly
  - flag/scale
---

# Infeasible-powertrain warning threshold

**Definition.** Shaft-power ceiling below which the response warns that the powertrain may be infeasible.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.1`

**Formula — as the code writes it.**

```
if p_shaft_max < 0.1:
```

**Inputs.**

- [[curve-p-shaft-max|Shaft power ceiling]]  — *⊣ limit*

**Produced by.** `app/services/powertrain_performance.py:687` — `compute_performance_curve`

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:688`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Scale (ADR 0023).** No source sets a feasibility floor. At RC/UAV scale even the smallest indoor models draw tens of watts, so a 0.1 W threshold cannot discriminate a feasible from an infeasible powertrain in the 0.5-15 kg range.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic number with no explanation. 0.1 W is far below any usable RC powertrain (smallest indoor models need tens of watts), so the check almost never fires — it is effectively a zero-check dressed as a feasibility check.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Check if power ceiling is very low (infeasibility check)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
