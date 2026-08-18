---
name: resolved-ar
symbol: AR
kind: quantity
unit: dimensionless
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Resolved aspect ratio

**Definition.** Wing aspect ratio resolved by the same three-tier priority.

**Formula — as the code writes it.**

```
ar = _pick(request.aspect_ratio, "aspect_ratio", _DEFAULT_AR, "Wing aspect ratio (aspect_ratio)", "aspect_ratio")
```

**Inputs.** [[default-ar-sizing|Default aspect ratio (sizing)]]

**Produced by.** `app/services/powertrain_sizing_service.py:179` — `_resolve_aero_params`

**Consumed by.**

- in this graph: [[combo-cruise-power|Estimated cruise power]] · [[combo-required-power|Power required for a motor+battery combo]]
- outside it: `app/services/powertrain_sizing_service.py:247` · `app/services/powertrain_sizing_service.py:312`

**Source.** 🟢 SOURCED

> rcplanedesigner.com, 'Aspect Ratio - Practical limits and mission-consistent ranges': Trainer 5/7/9, Sport 4/5.5/7; gliders (AR 10-25) out of scope. Sadraey (2013) §4.6 uses AR ~ 12 for a turboprop transport.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
AR = b^2 / S; mission-consistent ranges Trainer 5-9, Sport 4-7
```

**⚠️ Divergence from the source.** The source insists AR 'is selected within mission-consistent ranges rather than optimized in isolation' and that it cannot be set independently of span and wing loading. A single mission-blind default contradicts that framing.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
