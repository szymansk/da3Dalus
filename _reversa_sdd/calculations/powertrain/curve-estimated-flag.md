---
name: curve-estimated-flag
symbol: estimated
kind: quantity
unit: boolean
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Estimated-power flag

**Definition.** Per-sample marker: True when the numbers came from the current x voltage estimate (fixed-RPM model), False when they came from the QPROP physics solve.

**Formula — as the code writes it.**

```
estimated_flag = False   # QPROP branch
estimated_flag = True    # fixed-RPM branch
```

**Inputs.** [[motor-uses-qprop-model|QPROP model availability flag]]

**Produced by.** `app/services/powertrain_performance.py:730` — `compute_performance_curve`

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:770` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:255`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Not an engineering quantity. Worth recording that Drela's notes describe the QPROP branch as a physics model, not a measurement, so the field description ('rather than a directly measured datasheet value') mislabels what the False case actually is.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The field description says the flag distinguishes derived-from-current x voltage from "a directly measured datasheet value", but the False case is a QPROP physics solve, not a measurement. Name/description contradicts the definition.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `PerformanceSample field description: "True when power was derived from current×voltage rather than a directly measured datasheet value."`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
