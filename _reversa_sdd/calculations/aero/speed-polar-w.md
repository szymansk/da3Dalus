---
name: speed-polar-w
symbol: w
kind: quantity
unit: m/s
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Sink rate

**Definition.** Steady-glide sink rate at each speed.

**Formula — as the code writes it.**

```
w = v * (cd_pos / cl_pos)
```

**Inputs.** [[speed-polar-v|Glide forward speed]] · [[cl-values|Lift coefficient array]] · [[cd-values|Drag coefficient array]]

**Produced by.** `app/services/analysis_service.py:515` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[i-min-sink|Minimum-sink index]] · [[w-min|Minimum sink rate]]
- outside it: `SpeedPolarCurve.w` · `frontend speed-polar chart`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Gleitzahl (Aerodynamik)', https://wiki.rc-network.de/wiki/Gleitzahl
>
> — via `rc-aircraft-designer, aerodynamics-expert`

**The source states it as.**

```
E = L/D = C_L/C_D = horizontal distance / altitude lost  ⇒  sink/forward speed = 1/E = C_D/C_L
```

**⚠️ Divergence from the source.** The exact relation is w = V·sin(γ) with tan γ = C_D/C_L; the code uses w = V·(C_D/C_L), i.e. the small-glide-angle approximation sin γ ≈ tan γ. Error < 1.5% for E > 5, ~5% at E = 3. Acceptable for RC gliders, not flagged in the code.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
