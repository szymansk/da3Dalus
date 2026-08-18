---
name: is-directionally-stable
symbol: —
kind: quantity
unit: – (bool)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
---

# Directional stability flag

**Definition.** True when Cn_beta is present and positive.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
is_directionally_stable=(cnb is not None and cnb > 0)
```

**Inputs.**

- [[cnb|Yawing moment derivative w.r.t. beta]]

**Produced by.** `app/services/stability_service.py:346` — `get_stability_summary`

**Consumed by.**

- outside it: `app/services/stability_service.py:176` · `app/services/copilot_tools.py:460`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §6.2.2 and §12.6.2: directional (weathercock) stability ⇔ C_nβ > 0.
>
> — via `aircraft-design-scholz`

**⚠️ Anomaly.** Same divergence as is-statically-stable vs trim_enrichment_service.py:141.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
