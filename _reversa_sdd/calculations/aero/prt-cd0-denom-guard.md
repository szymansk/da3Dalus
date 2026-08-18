---
name: prt-cd0-denom-guard
symbol: —
kind: constant
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
node_class: numerical-tolerance
tags:
  - cluster/aero-polars
  - class/numerical-tolerance
  - source/no-source-found
  - flag/divergence
---

# 1/√Re interpolation denominator guard

**Definition.** Below this \|denominator\| the interpolation degenerates to the lower endpoint.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-15`

**Formula — as the code writes it.**

```
if abs(denom) < 1e-15:
    return float(cd0_lo)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:172` — `lookup_cd0_at_v`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 1e-15 is a float-epsilon guard, not a physical constant.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `denom = inv_sqrt_hi - inv_sqrt_lo
if abs(denom) < 1e-15:
    return float(cd0_lo)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
