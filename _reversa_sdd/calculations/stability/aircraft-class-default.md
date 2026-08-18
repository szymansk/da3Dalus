---
name: aircraft-class-default
symbol: —
kind: constant
unit: – (string)
cluster: stability
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Default aircraft class

**Definition.** Class used for tail-volume targets when the aeroplane has no default loading scenario or an unknown class.

**Value.** `rc_trainer`

**Formula — as the code writes it.**

```
aircraft_class: str = ctx.get("aircraft_class", "rc_trainer")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/tail_sizing_service.py:236` — `compute_tail_volumes`

**Consumed by.**

- outside it: `app/services/tail_sizing_service.py:85,237,238` · `app/services/tail_sizing_service.py:449,453 (build_tail_sizing_context_from_aeroplane)` · `app/api/v2/endpoints/aeroplane/tail_sizing.py:138`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** No source prescribes a default aircraft class. rcplanedesigner.com's mission tables show the trainer band is the most conservative (largest V_H, largest static margin), so defaulting there is at least the safe direction — but it silently sizes an acrobatic or pylon design against trainer targets, and the substitution is reported only through `aircraft_class_used`, never as a warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Silently classifies an aerobatic or pylon design against trainer targets and reports the substitution only through `aircraft_class_used` — no warning is appended (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
