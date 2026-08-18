---
name: alr-symmetric-camber-threshold
symbol: —
kind: parameter
unit: % chord
cluster: aero-polars
user_visible: true
source_status: PARTIAL
---

# Symmetric-family camber threshold

**Definition.** Max camber below which an airfoil is labelled symmetric.

**Value.** `0.5`

**Formula — as the code writes it.**

```
_SYMMETRIC_MAX_CAMBER_PCT = 0.5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:43` — `_SYMMETRIC_MAX_CAMBER_PCT`

**Consumed by.**

- outside it: `classify_family:261 (reflex guard)` · `classify_family:274`

**Source.** 🟡 PARTIAL

> rcplanedesigner.com, 'Wing — Airfoils: Airfoils Families' (symmetrical family); Lennon, Basics of R/C Model Aircraft Design (1996), Ch. 2 (symmetrical, e.g. E168, no camber)
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** The family label is sourced; the 0.5 %-chord numeric cut-off is not. A symmetric section has zero camber by definition — 0.5% is an unsourced numerical tolerance.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `_SYMMETRIC_MAX_CAMBER_PCT = 0.5  # max_camber_pct below which → symmetric`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
