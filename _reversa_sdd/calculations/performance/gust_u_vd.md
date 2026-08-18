---
name: gust_u_vd
symbol: U_de(V_D)
kind: constant
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: regulatory-constant
tags:
  - cluster/perf-envelope
  - class/regulatory-constant
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/scale
---

# Design gust velocity at dive speed

**Definition.** Sharp-edged vertical gust velocity (EAS) applied at dive speed.

**Regulatory constant.** Taken from a standard. It carries the clause *and* the class of aircraft that clause applies to.

**Value.** `7.62`

**Formula — as the code writes it.**

```
GUST_U_VD_MPS: float = 7.62
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:44` — `GUST_U_VD_MPS`

**Consumed by.**

- in this graph: `Gust velocity schedule`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟢 SOURCED

> CS-VLA 333(c)(1) / FAR 23.333(c)(1) — 25 ft/s (7.62 m/s) EAS at V_D. Accurate.
>
> — via `scholz`

**The source states it as.**

```
U_de = 25 ft/s EAS at V_D
```

**⚠️ Scale (ADR 0023).** Same kinematic breakdown as gust_u_vc, milder: at V_D ~ 39 m/s, atan(7.62/39) = 11 deg — still at or past stall alpha for most RC sections.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Same RC-scale concern as gust_u_vc.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `CS-VLA.333(c)(1) / FAR-23.333(c); "V_D: 7.62 m/s (25 ft/s EAS)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
