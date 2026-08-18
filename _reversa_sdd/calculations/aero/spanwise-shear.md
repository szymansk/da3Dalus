---
name: spanwise-shear
symbol: V(y)
kind: quantity
unit: N
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-spanwise
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Running shear force

**Definition.** Sum of the lift of all strips outboard of y.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
shear_N: float = Field(..., description="Running shear force V(y): sum of lift outboard of y (N)")
```

**Inputs.**

- [[q-dyn|Dynamic pressure]]

**Produced by.** `app/schemas/spanwise_loads.py:29` — `SpanwiseLoadEntry.shear_N`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Port root shear` · `Starboard root shear`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `frontend/hooks/useSpanwiseLoads.ts:15` · `frontend AnalysisViewerPanel.tsx:905`

**Source.** 🟡 PARTIAL

> Scholz 07_WingDesign §7.4 (spar webs 'resist shear loads'); Sadraey §5.8 (load distribution L' = c·C_L governs wing structural sizing). No source read states the discrete summation form.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Concept: V(y) = integral from y to b/2 of the running load l(eta) d(eta)
```

**⚠️ Divergence from the source.** The discrete sum over outboard strips is the correct numerical realisation of the integral, but its convergence depends entirely on the VLM strip count, which the response does not report.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
