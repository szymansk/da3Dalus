---
name: alr-aft-quad-coeff
symbol: —
kind: quantity
unit: 1/chord
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Aft lower-surface quadratic coefficient

**Definition.** \|Leading coefficient\| of a 2nd-order fit to the lower surface over the aft chord.

**Formula — as the code writes it.**

```
p_aft = np.polyfit(x_eval[aft_mask], y_lower[aft_mask], 2)
aft_quad_coeff = float(abs(p_aft[0]))
```

**Inputs.** [[alr-flat-bottom-aft-x-lo|Flat-bottom aft window start]]

**Produced by.** `app/services/airfoil_low_re_service.py:246` — `classify_family`

**Consumed by.**

- in this graph: [[alr-family|Airfoil family label]]
- outside it: `classify_family:288`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Bespoke lower-surface linearity measure; no source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `p_aft = np.polyfit(x_eval[aft_mask], y_lower[aft_mask], 2)
aft_quad_coeff = float(abs(p_aft[0]))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
