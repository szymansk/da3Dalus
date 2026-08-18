---
name: speed-polar-ld
kind: quantity
unit: -
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
---

# Glide ratio per point

**Definition.** Lift-to-drag ratio along the sorted polar; the code notes it equals V/w.

**Formula — as the code writes it.**

```
ld = cl_s / cd_s  # equals V / w
```

**Inputs.** [[cl-values|Lift coefficient array]] · [[cd-values|Drag coefficient array]]

**Produced by.** `app/services/analysis_service.py:522` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[i-best-glide|Best-glide index]] · [[ld-max|Maximum lift-to-drag ratio]]

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2; RC-Network Wiki 'Gleitzahl'
>
> — via `aerodynamics-expert, rc-aircraft-designer`

**The source states it as.**

```
L/D = C_L/C_D = horizontal distance / altitude lost (= V/w)
```

**⚠️ Divergence from the source.** The code comment '# equals V / w' is confirmed by the source. Being the third in-file producer of an L/D number (also lines 108 and 1154) is an ADR 0022 issue, not a physics one — all three are mathematically identical.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third producer of an L/D number inside this file (also lines 108 and 1154).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
