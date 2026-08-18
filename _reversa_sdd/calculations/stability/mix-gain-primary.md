---
name: mix-gain-primary
symbol: g_p
kind: parameter
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-parameter
tags:
  - cluster/stability
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Primary mix gain

**Definition.** Gain applied to the symmetric (pitch/lift) control component of a mixed surface.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.0`

**Formula — as the code writes it.**

```
gp = float(getattr(ted, "mix_gain_primary", 1.0) or 1.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/trim_enrichment_service.py:250` — `build_mix_params_from_schema`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Mixer symmetric offset`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/trim_enrichment_service.py:255,303,304`

**Source.** 🟡 PARTIAL

> The concept of a mixing gain on the symmetric (pitch/lift) channel of a combined surface is described qualitatively in Lennon Ch. 23 (elevon mixing) and Sadraey §12.8 (unconventional control surfaces), but neither source gives a default gain value or a formal gain parameter.
>
> — via `rc-aircraft-designer + aircraft-design-scholz`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** Unity default is a code convention, not a sourced value. `or 1.0` overrides a legitimately stored 0.0 gain (falsy), so a surface deliberately decoupled from pitch is silently re-coupled at full gain — the opposite of the designer's intent. Same pattern for mix_gain_secondary and differential_ratio.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** `or 1.0` overrides a legitimately stored 0.0 gain (falsy) — a surface deliberately decoupled from pitch is silently re-coupled at full gain. Same pattern for mix_gain_secondary and differential_ratio.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
