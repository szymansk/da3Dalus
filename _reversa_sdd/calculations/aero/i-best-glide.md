---
name: i-best-glide
kind: quantity
unit: index
cluster: aero-spanwise
user_visible: false
source_status: SOURCED
---

# Best-glide index

**Definition.** Index of maximum L/D on the sorted curve.

**Formula — as the code writes it.**

```
i_best = int(np.argmax(ld))
```

**Inputs.** [[speed-polar-ld|Glide ratio per point]]

**Produced by.** `app/services/analysis_service.py:523` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[alpha-best-glide-deg|Alpha at best glide]] · [[ld-max|Maximum lift-to-drag ratio]] · [[v-best-glide|Best-glide speed]]

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2; RC-Network Wiki 'Gleitzahl' ('best glide ratio … occurs at a specific airspeed called the best glide speed')
>
> — via `aerodynamics-expert, rc-aircraft-designer`

**The source states it as.**

```
max(C_L/C_D) over the polar
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
