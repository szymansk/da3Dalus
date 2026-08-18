---
name: trim-alpha-deg
symbol: alpha_trim
kind: quantity
unit: deg
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Trim angle of attack

**Definition.** Angle of attack of the analysed flight condition, echoed into the stability summary.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
trim_alpha_deg=_scalar(result.flight_condition.alpha)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:340` — `get_stability_summary`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/stability_service.py:173 (trim_alpha_deg column)`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Nothing to source: the field is the requested operating-point alpha echoed back (app/services/stability_service.py:340), not a trimmed angle of attack. Sadraey §12.5.4 Eq. 12.86 solves α and δ_E simultaneously; that solve does not exist here.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Named 'trim' but no trim solve happens here — it is simply the requested alpha of the operating point echoed back.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
