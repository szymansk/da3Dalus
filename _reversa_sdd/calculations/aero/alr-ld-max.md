---
name: alr-ld-max
symbol: (L/D)_max
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
---

# Section (L/D)_max

**Definition.** Maximum CL/CD over the trusted sweep at one Re.

**Formula — as the code writes it.**

```
ld = np.where(cd_f > 1e-12, cl_f / cd_f, np.nan)
result["ld_max"] = float(np.nanmax(ld))
```

**Inputs.** [[alr-alpha-sweep|Alpha sweep bounds and step]]

**Produced by.** `app/services/airfoil_low_re_service.py:635` — `_extract_metrics`

**Consumed by.**

- in this graph: [[alr-score-re-agnostic|re_agnostic suitability score]]
- outside it: `AirfoilLowRePolarModel.ld_max` · `score_re_agnostic:848`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 — (L/D)_max = max(C_L/C_D)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
(L/D)_max = max C_L/C_D
```

**⚠️ Divergence from the source.** Anderson's closed form ½√(πeAR/C_D0) is a *wing* result; here it is a 2D section maximum taken numerically over the sweep, which is the correct 2D analogue. Not exposed on SuitabilityItem despite being the highest-weighted (0.35) re_agnostic input.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Not exposed on SuitabilityItem — the highest-weighted input (0.35) to re_agnostic is never shown alongside the score.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `with np.errstate(divide="ignore", invalid="ignore"):
    ld = np.where(cd_f > 1e-12, cl_f / cd_f, np.nan)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
