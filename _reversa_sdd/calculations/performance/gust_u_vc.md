---
name: gust_u_vc
symbol: U_de(V_C)
kind: constant
unit: m/s
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Design gust velocity at cruise speed

**Definition.** Sharp-edged vertical gust velocity (EAS) applied at and below cruise speed.

**Value.** `15.24`

**Formula — as the code writes it.**

```
GUST_U_VC_MPS: float = 15.24
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:43` — `GUST_U_VC_MPS`

**Consumed by.**

- in this graph: [[fe_u_gust_at_v|Gust velocity schedule]]

**Source.** 🟢 SOURCED

> CS-VLA 333(c)(1) and FAR 23.333(c)(1) — positive/negative sharp-edged gusts of 50 ft/s (15.24 m/s) EAS at V_C. Citation in code is accurate.
>
> — via `scholz, rc`

**The source states it as.**

```
U_de = 50 ft/s EAS at V_C
```

**⚠️ Scale (ADR 0023).** ADR 0023 — but not for the usual reason. A 15.24 m/s discrete gust is a property of the ATMOSPHERE, so it does not shrink with the aircraft. The failure is kinematic: at an RC cruise of 20 m/s the gust-induced incidence is atan(15.24/20) = 37 deg, roughly 4x stall alpha. The linear CL_alpha in delta_n is then physically void — the wing stalls long before the computed load factor is reached, so the gust line overstates n by a large and unbounded margin. CS-VLA applicability is MTOW <= 750 kg at manned cruise speeds (~50-70 m/s), where U/V ~ 0.25 keeps the linearisation honest. No RC-scale validation cited or possible without a stall-limited gust model.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** CS-VLA/FAR-23 gust values are certified for manned light aircraft (MTOW up to 750 kg / 1320 lb). Applied unscaled to a 0.5–15 kg RC/UAV target class — ADR 0023 concern; no RC-scale validation cited.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `CS-VLA.333(c)(1) / FAR-23.333(c) — sharp-edged EAS; "V_C: 15.24 m/s (50 ft/s EAS)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
