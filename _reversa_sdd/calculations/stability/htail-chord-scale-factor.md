---
name: htail-chord-scale-factor
symbol: scale
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: false
source_status: SOURCED
---

# Horizontal tail chord scale factor

**Definition.** Multiplier applied to every horizontal-tail cross-section chord on a real apply.

**Formula — as the code writes it.**

```
scale = 1.0 + delta_pct
```

**Inputs.** [[delta-pct-htail|Horizontal tail chord-scale fraction]]

**Produced by.** `app/services/sm_sizing_service.py:982` — `apply_htail_scale`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:983 (guard), 989 (xsec.chord write)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.7 — tail planform area S_h is realised through AR_h, taper, span and chord; scaling chord at fixed span is one admissible realisation of a target S_h obtained from §6.7.1.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
S_h = V_H·C̄·S/l, then distributed over b_h and C_h (Sadraey §6.7)
```

**⚠️ Divergence from the source.** Constant-span chord scaling changes AR_h, which Sadraey §6.7 constrains to roughly 4–6 (PreSTo: 4.5–5.5) and which feeds back into C_Lα_h via Eq. 6.57. The code applies the scale with no AR check.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
