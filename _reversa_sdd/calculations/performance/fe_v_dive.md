---
name: fe_v_dive
symbol: V_D
kind: quantity
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Dive speed

**Definition.** Design dive speed bounding the right edge of the V-n envelope.

**Formula — as the code writes it.**

```
v_dive = 1.4 * v_max_mps
```

**Inputs.** [[fe_v_max|Maximum level speed]] · [[fe_dive_factor|Dive-speed factor]]

**Produced by.** `app/services/flight_envelope_service.py:315` — `compute_vn_curve`

**Consumed by.**

- in this graph: [[fe_u_gust_at_v|Gust velocity schedule]] · [[fe_v_c|Cruise speed (back-derived)]] · [[fe_v_sweep|Velocity sweep points]]
- outside it: `VnDiagram.tsx`

**Source.** 🔴 NO SOURCE FOUND

> Inherits fe_dive_factor — no source.
>
> — via `scholz`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Three user-visible producers: fe:315, fe:523 (derive_performance_kpis recomputes), assumption_compute_service:956 (ctx['v_dive_mps'] -> SpeedChipRow). ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Three producers of V_D: compute_vn_curve line 315, derive_performance_kpis line 523 (recomputes 1.4·v_max independently), and assumption_compute_service._compute_v_dive line 956 (ctx['v_dive_mps'], rendered in SpeedChipRow). All three are user-visible.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
