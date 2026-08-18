---
name: alr-stall-gentleness
symbol: dCL/dα
kind: quantity
unit: 1/deg
cluster: aero-polars
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Stall gentleness

**Definition.** dCL/dα fitted over the 4 points starting at the CL_max peak; ≈0 gentle, negative abrupt.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
post_cl = cl_f[idx_max : idx_max + 4]
post_alpha = alpha_f[idx_max : idx_max + 4]
coeffs = np.polyfit(post_alpha, post_cl, 1)
result["stall_gentleness"] = float(coeffs[0])
```

**Inputs.**

- [[alr-cl-max|Section CL_max]]  — *⊣ limit*
- [[alr-alpha-sweep|Alpha sweep bounds and step]]  — *⊣ limit*

**Produced by.** `app/services/airfoil_low_re_service.py:624` — `_extract_metrics`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Stall gentleness normalisation scale` · `re_agnostic suitability score`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `AirfoilLowRePolarModel.stall_gentleness` · `score_re_agnostic:851` · `suitability_service:513 → SuitabilityItem.stall_gentleness` · `frontend AirfoilSuitabilityCard.tsx:397`

**Source.** 🟡 PARTIAL

> Anderson 6e §4.12.4 (separation point migrates forward; lift falls abruptly past stall); Lennon (1996), Ch. 2 — 'gentle stall' as a named airfoil property of moderately cambered sections
>
> — via `aerodynamics-expert, rc-aircraft-designer`

**⚠️ Divergence from the source.** Gentle vs abrupt stall is a sourced qualitative property, but quantifying it as a linear dCL/dα over a fixed 4-point post-peak window is unattributable, and the window length is unsourced. Comment says '3 points after peak' while the slice takes the peak plus 3.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Comment says '3 points after peak' but the slice `cl_f[idx_max : idx_max+4]` takes the peak plus 3 — comment contradicts code.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Use linear fit over the 3 points after peak
if idx_max + 3 < len(cl_f):
    post_cl = cl_f[idx_max : idx_max + 4]`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
