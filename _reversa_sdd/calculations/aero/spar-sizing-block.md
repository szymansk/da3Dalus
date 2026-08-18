---
name: spar-sizing-block
kind: quantity
unit: mixed
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Per-surface spar sizing block

**Definition.** Optional list of SparSizingResult appended to the spanwise-loads response when spar_params are supplied.

**Formula — as the code writes it.**

```
spar_sizing: Optional[list[SparSizingResult]] = Field(None, ...)
```

**Inputs.** [[g-limit-effective|Effective manoeuvre load factor]] · [[sigma-allow|Allowable bending stress]] · [[tc-by-y|Local thickness-to-chord ratio]] · [[sizing-half-span-selection|Design half-span selection]]

**Produced by.** `app/schemas/spanwise_loads.py:100` — `SpanwiseLoadsWithSizingResponse.spar_sizing`

**Consumed by.**

- outside it: `API /spanwise_loads_with_sizing` · `frontend/hooks/useSparSizing.ts`

**Source.** 🟡 PARTIAL

> Container; members sourced separately — Sadraey §10.4.1 Eq. 10.4 / Table 10.9 (g_limit, j), Scholz 07_WingDesign §7.1/§7.4 (t/c, root BM), RC-Network Wiki 'Holm' (spar carries bending).

**⚠️ Divergence from the source.** No source defines this response envelope; the aggregate is a project construct.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
