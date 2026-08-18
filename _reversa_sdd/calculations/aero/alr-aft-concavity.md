---
name: alr-aft-concavity
symbol: —
kind: quantity
unit: 1/chord
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Aft camber concavity (reflex Signal B)

**Definition.** Leading coefficient of a 2nd-order fit to the camber line over x∈[0.5,1.0].

**Formula — as the code writes it.**

```
p_aft_c = np.polyfit(x_eval[aft_concavity_mask], camber[aft_concavity_mask], 2)
aft_concavity = float(p_aft_c[0])
```

**Inputs.** [[alr-camber-line|Mean camber line]]

**Produced by.** `app/services/airfoil_low_re_service.py:234` — `classify_family`

**Consumed by.**

- in this graph: [[alr-family|Airfoil family label]]
- outside it: `classify_family:265`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Bespoke: leading coefficient of a quadratic fit to the mean line over x∈[0.5,1.0]. No source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `aft_concavity_mask = (x_eval >= 0.50) & (x_eval <= 1.0)
aft_concavity = 0.0
if aft_concavity_mask.sum() >= 4:`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
