---
name: alr-reflex-aft-concavity-min
symbol: —
kind: parameter
unit: 1/chord
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

# Reflex Signal B threshold

**Definition.** Minimum positive quadratic coefficient of the aft camber line marking upturned-TE reflex.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `0.015`

**Formula — as the code writes it.**

```
_REFLEX_AFT_CONCAVITY_MIN = (0.015)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:85` — `_REFLEX_AFT_CONCAVITY_MIN`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `classify_family:265`

**Source.** 🟡 PARTIAL

> Lennon (1996), Ch. 2 — upturned aft mean line defines reflex
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** 0.015 calibrated in-repo against Clark YH (+0.039) and NACA 4412 (−0.11). No external source for the threshold.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# For Clark YH this
#   coefficient ≈ +0.039; for NACA 4412 (not reflexed) it is −0.11.  Threshold 0.015`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
