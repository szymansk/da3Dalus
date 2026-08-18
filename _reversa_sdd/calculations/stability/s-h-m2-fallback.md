---
name: s-h-m2-fallback
symbol: S_H
kind: constant
unit: m²
cluster: stability
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Horizontal tail area fallback

**Definition.** Horizontal tail area used when the context does not carry one.

**Value.** `0.08`

**Formula — as the code writes it.**

```
s_h_m2: float = ctx.get("s_h_m2") or 0.08
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:377` — `suggest_corrections`

**Consumed by.**

- in this graph: [[alpha-vh|Tail efficiency factor]] · [[delta-pct-htail|Horizontal tail chord-scale fraction]] · [[predicted-sm-fwd-htail|Predicted forward SM after htail scale]] · [[predicted-sm-htail-scale|Predicted SM after htail chord-scale]]
- outside it: `app/services/sm_sizing_service.py:377,408,513,641,707,959`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.08 m² is unattributed and repeated at six sites. With the companion fallbacks (S_ref 0.60 m², MAC 0.30 m, l_H 0.60 m) it implies V_H = 0.08·0.60/(0.60·0.30) = 0.27 — below every RC mission band in rcplanedesigner.com (Acrobatic minimum 0.40) and below the app's own V_H_PHYSICAL_MIN of 0.20's neighbourhood. The fallback set is not self-consistent as an aircraft.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Same magic literal repeated at six sites with no named constant and no source. Silent substitution (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
