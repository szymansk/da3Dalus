---
name: sm-classify-neutral-threshold-pct
symbol: —
kind: constant
unit: % MAC
cluster: stability
user_visible: true
source_status: SOURCED
---

# Neutral/unstable boundary

**Definition.** Static margin percent above which the aircraft is labelled 'neutral' rather than 'unstable'.

**Value.** `0`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:79` — `classify_stability`

**Consumed by.**

- in this graph: [[stability-class|Stability classification (static margin band)]]
- outside it: `app/services/stability_service.py:79`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2, Eq. 11.22: x_np − x_cg > 0; equivalently Eq. 11.17 C_mα = C_Lα(X_cg − X_np) < 0. Corroborated: Lennon Ch. 6 ("neutral stability is reached when CG and NP coincide").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_mα < 0  ⇔  X_cg < X_np  ⇔  SM > 0
```

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
