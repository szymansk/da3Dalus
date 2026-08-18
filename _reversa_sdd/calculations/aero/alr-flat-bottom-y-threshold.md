---
name: alr-flat-bottom-y-threshold
symbol: —
kind: parameter
unit: chord fraction
cluster: aero-polars
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/aero-polars
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Legacy flat-bottom mean-|y| gate

**Definition.** Mean absolute lower-surface y below which the airfoil is flat_bottom (strict legacy path).

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.002`

**Formula — as the code writes it.**

```
_FLAT_BOTTOM_Y_THRESHOLD = 0.002
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:45` — `_FLAT_BOTTOM_Y_THRESHOLD`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `classify_family:286`

**Source.** 🟡 PARTIAL

> rcplanedesigner.com, 'Wing — Airfoils: Airfoils Families' (flat-bottom family, trainer use); Lennon (1996), Ch. 2 (Clark Y as the popular flat-bottom section)
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** Family is sourced; the 0.002-chord mean-\|y\| gate is an in-repo numerical criterion with no external source.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `if mean_lower_abs_y < _FLAT_BOTTOM_Y_THRESHOLD:
    return "flat_bottom"`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
