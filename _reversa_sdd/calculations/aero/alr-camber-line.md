---
name: alr-camber-line
symbol: y_c(x)
kind: quantity
unit: chord fraction
cluster: aero-polars
user_visible: false
source_status: SOURCED
---

# Mean camber line

**Definition.** Mean of the interpolated upper and lower surfaces over 200 chordwise stations.

**Formula — as the code writes it.**

```
camber = (y_upper + y_lower) / 2.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:211` — `classify_family`

**Consumed by.**

- in this graph: [[alr-aft-concavity|Aft camber concavity (reflex Signal B)]] · [[alr-camber-at-te|camber_at_te (camber at x=0.9)]] · [[alr-max-camber-pct|Max camber (classifier-internal)]]
- outside it: `classify_family:213,221,234`

**Source.** 🟢 SOURCED

> Abbott & von Doenhoff, Theory of Wing Sections (Dover 1959), Ch. 1 — mean line defined as the locus midway between upper and lower surfaces; Anderson 6e §4.2 (airfoil nomenclature)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
y_c(x) = (y_upper(x) + y_lower(x))/2
```

**⚠️ Divergence from the source.** Identical form. 200-station resampling is an implementation detail.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `x_eval = np.linspace(x_min, x_max, 200)
y_upper = np.interp(x_eval, upper_s[:, 0], upper_s[:, 1])
y_lower = np.interp(x_eval, lower_s[:, 0], lower_s[:, 1])
camber = (y_upper + y_lower) / 2.0`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
