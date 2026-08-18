---
name: alr-flat-bottom-quad-threshold
symbol: —
kind: parameter
unit: 1/chord
cluster: aero-polars
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - flag/divergence
---

# Flat-bottom aft-linearity threshold

**Definition.** Max \|quadratic coefficient\| of the aft lower surface for a flat_bottom label.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.005`

**Formula — as the code writes it.**

```
_FLAT_BOTTOM_QUAD_THRESHOLD = (0.005)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:110` — `_FLAT_BOTTOM_QUAD_THRESHOLD`

**Consumed by.**

- outside it: `classify_family:288`

**Source.** 🟡 PARTIAL

> rcplanedesigner.com, 'Wing — Airfoils: Airfoils Families' (flat-bottom family)
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** 0.005 calibrated in-repo against Clark Y (0.00006), Clark X (0.0), Clark V (0.0013) vs NACA 4412 (0.030), 4418 (0.009), SG6040 (0.015). Empirical, no external source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `#   flat_bottom (quad_coeff < 0.005): Clark Y (0.00006), Clark X (0.0), Clark V (0.0013)
#   cambered    (quad_coeff > 0.008): NACA 4412 (0.030), NACA 4418 (0.009), SG6040 (0.015)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
