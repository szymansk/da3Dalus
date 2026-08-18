---
name: tos-confidence-probe-xtr
symbol: —
kind: quantity
unit: x/c
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/neuralfoil
---

# Confidence-probe trip position

**Definition.** Mid-grid xtr at which NeuralFoil's analysis_confidence is sampled.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
xtr_upper=float(xtr_grid[len(xtr_grid) // 2]),
```

**Inputs.**

- [[tos-xtr-grid|Turbulator trip-position sweep grid]]

**Produced by.** `app/services/turbulator_optimizer_service.py:218` — `optimize_section_xtr`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Mean NeuralFoil analysis confidence`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> Sharpe, PhD thesis (MIT, 2024) §7.2.4 (confidence is a function of the FULL input latent vector, via a Mahalanobis-distance correction on the whole query point)
>
> — via `aerosandbox-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Because confidence depends on every input including the trip location, sampling it at one grid point does not characterise the sweep — a low-confidence region at, say, xtr = 0.25 is invisible when the probe sits at xtr = 0.55. The code comment also says 'at the first xtr' while the code takes the middle point.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The comment says confidence is sampled 'at the first xtr' but the code samples the middle grid point — comment contradicts code.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:218`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
