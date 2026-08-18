---
name: altitude-speed-polar
kind: parameter
unit: m
cluster: aero-spanwise
user_visible: true
source_status: PARTIAL
---

# Speed-polar altitude

**Definition.** Altitude echoed from the sweep request, defaulting to 0 m.

**Value.** `0.0`

**Formula — as the code writes it.**

```
altitude = float(getattr(sweep_request, "altitude", 0.0) or 0.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:625` — `_build_speed_polar`

**Consumed by.**

- in this graph: [[rho-speed-polar|Air density (speed polar)]]
- outside it: `SpeedPolar.altitude`

**Source.** 🟡 PARTIAL

> Scholz 05_PreliminarySizing §5.6.2 (standard-atmosphere altitude as the independent variable); ASB Atmosphere takes altitude in METRES

**The source states it as.**

```
h [m], ISA
```

**⚠️ Divergence from the source.** The default 0.0 m (sea level) is the conservative/worst-case choice per Scholz's guidance on picking sea-level density for the stall-speed constraint, but the code does not state this as intent.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
