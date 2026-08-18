---
name: alr-semi-symmetric-threshold
symbol: —
kind: parameter
unit: % chord
cluster: aero-polars
user_visible: true
source_status: PARTIAL
---

# Semi-symmetric camber threshold

**Definition.** Max camber below which an airfoil is labelled semi_symmetric.

**Value.** `2.0`

**Formula — as the code writes it.**

```
_SEMI_SYMMETRIC_MAX_CAMBER_PCT = 2.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:44` — `_SEMI_SYMMETRIC_MAX_CAMBER_PCT`

**Consumed by.**

- outside it: `classify_family:292`

**Source.** 🟡 PARTIAL

> rcplanedesigner.com, 'Wing — Airfoils: Airfoils Families' — semi-symmetrical as the sport-model compromise between flat-bottom and symmetrical
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** Neither rcplanedesigner nor Lennon quantifies the camber boundary between semi-symmetrical and cambered. The 2.0 %-chord cut-off is unattributable.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `if max_camber_pct < _SEMI_SYMMETRIC_MAX_CAMBER_PCT:
    return "semi_symmetric"`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
