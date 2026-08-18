---
name: rho-speed-polar
symbol: ρ
kind: quantity
unit: kg/m³
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Air density (speed polar)

**Definition.** Density from the AeroSandbox standard atmosphere at the sweep altitude.

**Formula — as the code writes it.**

```
rho = float(asb.Atmosphere(altitude=altitude).density())
```

**Inputs.** [[altitude-speed-polar|Speed-polar altitude]]

**Produced by.** `app/services/analysis_service.py:626` — `_build_speed_polar`

**Consumed by.**

- in this graph: [[speed-polar-v|Glide forward speed]] · [[v-stall|Stall speed]]
- outside it: `SpeedPolar.rho`

**Source.** 🟢 SOURCED

> AeroSandbox asb.Atmosphere — U.S. 1976 COESA / ISA standard atmosphere; Scholz 05_PreliminarySizing §5.6.2 (troposphere T(h) = 288.15 − 0.0065·h[m])
>
> — via `aerosandbox-expert, aircraft-design-scholz`

**The source states it as.**

```
ISA: T(h) = 288.15 − 0.0065·h (0 ≤ h ≤ 11 km); rho from p/(R·T); asb.Atmosphere(altitude).density() [kg/m³]
```

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
