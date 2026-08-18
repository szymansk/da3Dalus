---
name: fe_gravity
symbol: g
kind: constant
unit: m/s^2
cluster: perf-envelope
user_visible: false
source_status: PARTIAL
---

# Gravitational acceleration (flight envelope)

**Definition.** Gravity used for all weight and wing-loading terms in the flight-envelope service.

**Value.** `9.81`

**Formula — as the code writes it.**

```
GRAVITY = 9.81
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/flight_envelope_service.py:40` — `GRAVITY`

**Consumed by.**

- in this graph: [[fe_mu_g|Gust mass ratio]] · [[fe_weight|Aircraft weight]] · [[fe_wing_loading|Wing loading (gust path)]]

**Source.** 🟡 PARTIAL

> Rounded standard gravity g_n = 9.80665 m/s² (CGPM 3rd Conf. 1901; ISO 80000-3). 9.81 is a 2-decimal rounding, uncited in file.
>
> — via `scholz`

**⚠️ Divergence from the source.** Three g in one cluster: 9.81 (fe:40), 9.80665 (end:49), inline 9.81 (mkpi:273). Rounding error is 3.6e-4 relative — negligible physically, but it makes W/S from the two paths differ in the last displayed digit for no reason. Pick 9.80665 once (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Third value of g in this cluster: 9.81 here, 9.80665 in endurance_service (G, line 49), 9.81 inline in mission_kpi_service (line 273). W/S is therefore produced by three code paths with two different g.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
