---
name: alr-alpha-attached-window
symbol: [α_lo, α_hi]
kind: quantity
unit: deg
cluster: aero-polars
user_visible: false
source_status: PARTIAL
---

# Attached-flow alpha window

**Definition.** Alpha range from the first trusted point up to the CL_max peak.

**Formula — as the code writes it.**

```
attached_alpha = alpha_f[: idx_max + 1]
result["alpha_attached_lo"] = float(attached_alpha[0])
result["alpha_attached_hi"] = float(attached_alpha[-1])
```

**Inputs.** [[alr-cl-max|Section CL_max]] · [[alr-alpha-sweep|Alpha sweep bounds and step]]

**Produced by.** `app/services/airfoil_low_re_service.py:649` — `_extract_metrics`

**Consumed by.**

- in this graph: [[alr-min-analysis-confidence|Windowed min analysis confidence]]
- outside it: `AirfoilLowRePolarModel.alpha_attached_lo/hi` · `_windowed_min_confidence:559`

**Source.** 🟡 PARTIAL

> Anderson 6e §4.12.4 — attached flow persists up to the stalling angle
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** Taking [first trusted α, α at CL_max] as 'attached' is consistent with the source, but the lower bound is set by the confidence gate rather than by any flow criterion, so the window is a data-availability artefact as much as a physical one. Persisted with no downstream reader except _windowed_min_confidence.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Not exposed on SuitabilityItem and only read back by _windowed_min_confidence — persisted with no downstream reader in app/ or frontend/.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `attached = cl_f[: idx_max + 1]
attached_alpha = alpha_f[: idx_max + 1]`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
