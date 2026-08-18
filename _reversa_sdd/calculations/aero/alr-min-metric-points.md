---
name: alr-min-metric-points
symbol: —
kind: constant
unit: count
cluster: aero-polars
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-polars
  - class/unclassified-constant
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Minimum trusted points for metric extraction

**Definition.** Fewer than 4 trusted CL/CD points aborts extraction; fewer than 5 skips the polar fit.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `4 / 5`

**Formula — as the code writes it.**

```
if len(cl) < 4 or len(cd) < 4: return result
...
if len(cl_f) >= 5:
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:602` — `_extract_metrics`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `_extract_metrics:610,656`

**Source.** 🟡 PARTIAL

> Elementary least-squares degrees of freedom: a 3-parameter quadratic needs ≥3 points to fit and ≥4 to leave any residual

**⚠️ Divergence from the source.** The 5-point floor for the parabolic fit is consistent with wanting ≥2 residual DOF, and the 4-point floor with a minimally-determined fit — but the code states no rationale and uses two different numbers for the same 'enough data' concept.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Two different minimums (4 and 5) for the same 'enough data' concept with no stated rationale.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `if len(cl) < 4 or len(cd) < 4:
    return result`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
