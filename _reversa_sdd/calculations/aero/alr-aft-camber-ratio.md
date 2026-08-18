---
name: alr-aft-camber-ratio
symbol: —
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Aft camber ratio (reflex Signal A)

**Definition.** Ratio of camber at 90% chord to max camber; near zero indicates reflex.

**Formula — as the code writes it.**

```
aft_camber_ratio = camber_at_te / max(max_camber, 1e-9)
```

**Inputs.** [[alr-camber-at-te|camber_at_te (camber at x=0.9)]] · [[alr-max-camber-pct|Max camber (classifier-internal)]]

**Produced by.** `app/services/airfoil_low_re_service.py:226` — `classify_family`

**Consumed by.**

- in this graph: [[alr-family|Airfoil family label]]
- outside it: `classify_family:262`

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Bespoke shape descriptor; the ratio y_c(0.9)/max(y_c) appears in no source consulted.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `aft_camber_ratio = camber_at_te / max(max_camber, 1e-9)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
