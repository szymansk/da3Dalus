---
name: cg-agg-m-ctx
symbol: x_cg,agg
kind: quantity
unit: m
cluster: mass
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/not-verified
---

# Published aggregate CG (computation context)

**Definition.** cg-agg cached on the aeroplane row for single-value clients and the stability chip row.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
"cg_agg_m": round(cg_agg, 4) if cg_agg is not None else None
```

**Inputs.**

- [[cg-agg|Aggregate CG (default scenario)]]  — *⤵ fallback*

**Produced by.** `app/services/assumption_compute_service.py:729` — `recompute_assumptions`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- outside it: `frontend/components/workbench/StabilityChipRow.tsx:27-35` · `frontend/lib/metricsAdapters.ts:200-234 (CG divergence vs. component CG)` · `frontend/lib/metricsAdapters.ts:343-344 (SM percent)` · `frontend/components/workbench/stability-overlay/buildStabilityTraces.ts:79` · `frontend/hooks/useComputationContext.ts:87`

**Source.** 🟢 SOURCED

> Sadraey, M.H., Wiley 2013, §11.2 Eq. (11.1), X_cg = ΣW_i·x_cg,i / ΣW_i, for one loading condition; Scholz, D. et al., PreSTo (EWADE 2011) §1 computes the same x_CG per configuration (empty, OEW, max payload).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
X_cg = ΣW_i·x_cg,i / ΣW_i   (Sadraey Eq. 11.1)
```

**Cited in the code itself.** `"cg_agg_m = CG of the is_default scenario (or plain weight-item CG). Kept for backward compat — single-value consumers still get a CG." — app/services/assumption_compute_service.py:727-728`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
