---
name: vlm-strip-cl
symbol: cl
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
  - solver-adjacent/vlm
---

# Local strip lift coefficient

**Definition.** Strip lift non-dimensionalised by dynamic pressure and strip area.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
denom = q * area; cl = lift / denom if denom > 0 else 0.0
```

**Inputs.**

- [[vlm-strip-lift|Strip lift force]]
- [[vlm-dynamic-pressure|Freestream dynamic pressure]]
- [[vlm-strip-area|Strip area]]

**Produced by.** `app/services/vlm_strip_forces.py:271` — `compute_vlm_strip_forces`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Chord × cl product` · `Normalised strip lift coefficient`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/schemas/strip_forces.py:StripForceEntry.cl` · `app/services/spanwise_loads.py:58` · `frontend/components/workbench/AnalysisViewerPanel.tsx:499`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §1.5 (coefficient definition); AVL 3.40 source, Avl/src/aero.f:348 ('forces normalized by strip area') and :870
>
> — via `aerodynamics-expert, avl-advisor`

**The source states it as.**

```
cl = L_strip / (q_inf * S_strip)
```

**⚠️ Divergence from the source.** Form matches AVL exactly. Differences are inherited from vlm-strip-area (panel vs planform area) and vlm-strip-lift (global vs local strip axes). The denom>0 -> 0.0 fallback has no source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** VLM is inviscid, so this cl carries no laminar-separation-bubble effect. At RC/UAV chord Reynolds numbers of 5e4-3e5 the real section cl(alpha) departs measurably from potential flow (Anderson §20.3.2 shows a Wortmann section at Re_c = 1e5 separating on both surfaces in the laminar solution). The strip cl is an inviscid upper bound at this scale.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Undeclared fallback: a zero denominator silently yields cl = 0.0 rather than NaN or a DesignWarning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/vlm_strip_forces.py:270-271`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
