---
name: mix-gain-secondary
symbol: g_s
kind: parameter
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: PARTIAL
node_class: unclassified-parameter
tags:
  - cluster/stability
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Secondary mix gain

**Definition.** Gain applied to the antisymmetric (roll/yaw) control component of a mixed surface.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.0`

**Formula — as the code writes it.**

```
gs = float(getattr(ted, "mix_gain_secondary", 1.0) or 1.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:251` — `build_mix_params_from_schema`

**Consumed by.**

- in this graph: `Mixer antisymmetric component`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/trim_enrichment_service.py:255,303,305`

**Source.** 🟡 PARTIAL

> As mix-gain-primary: the antisymmetric (roll/yaw) channel of a mixed surface is described in Lennon Ch. 23 and Sadraey §12.8, without a numerical default.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** Same `or 1.0` falsy-zero override as mix_gain_primary. Note aileron entries are forced to (1.0, 1.0, diff) at trim_enrichment_service.py:260, discarding any stored gains.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same `or 1.0` falsy-zero override as mix_gain_primary. Note aileron entries are forced to (1.0, 1.0, diff) at line 260, discarding any stored gains.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
