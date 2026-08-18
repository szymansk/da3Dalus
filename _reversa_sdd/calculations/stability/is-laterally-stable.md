---
name: is-laterally-stable
symbol: —
kind: quantity
unit: – (bool)
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Lateral stability flag

**Definition.** True when Cl_beta is present and negative.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
is_laterally_stable=(clb is not None and clb < 0)
```

**Inputs.**

- [[clb|Rolling moment derivative w.r.t. beta]]

**Produced by.** `app/services/stability_service.py:347` — `get_stability_summary`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/stability_service.py:177` · `app/services/copilot_tools.py:461`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.2.2 and §12.6.2: lateral stability (dihedral effect) ⇔ C_lβ < 0.
>
> — via `aircraft-design-scholz`

**⚠️ Anomaly.** Same divergence vs trim_enrichment_service.py:142.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
