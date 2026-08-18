---
name: tc-fallback-warning
kind: quantity
unit: -
cluster: structure
user_visible: true
source_status: NO_SOURCE_FOUND
---

# t/c fallback warning

**Definition.** Human-readable warning listing every station where the 0.12 t/c fallback was applied, or None.

**Formula — as the code writes it.**

```
tc_warn = (
    f"t/c=0.12 fallback applied at y={ys_str} m — no airfoil thickness data available."
)
```

**Inputs.** [[tc-fallback-ratio|Thickness-to-chord fallback ratio]]

**Produced by.** `app/services/spar_sizing.py:366` — `compute_spar_sizing`

**Consumed by.**

- outside it: `app/schemas/spar_sizing.py:144` · `frontend/hooks/useSparSizing.ts:45` · `frontend/components/workbench/SparSizingPanel.tsx:148` · `frontend/components/workbench/SparSizingPanel.tsx:154`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (warning text, not a calculation)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
