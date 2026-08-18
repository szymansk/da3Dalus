---
name: alr-cd0-reference-percentile
symbol: —
kind: parameter
unit: percent
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/no-source-found
  - flag/divergence
---

# Fleet cd0 reference percentile

**Definition.** Percentile of the fleet cd0 distribution at a given Re used as the efficiency reference.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `20.0`

**Formula — as the code writes it.**

```
percentile: float = 20.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:774` — `compute_re_cd0_reference`

**Consumed by.**

- in this graph: `Per-Re fleet cd0 reference`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `compute_re_cd0_reference:823`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** The 20th percentile as an 'efficiency reference' is a population-relative normalisation choice; no source in any consulted vault.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `return float(np.percentile(cd0_arr, percentile))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
