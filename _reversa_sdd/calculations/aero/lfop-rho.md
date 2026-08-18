---
name: lfop-rho
symbol: rho
kind: constant
unit: kg/m³
cluster: aero-strips
user_visible: false
source_status: SOURCED
---

# Air density (level-flight solve)

**Definition.** Sea-level air density used for the level-flight CL target.

**Value.** `1.225`

**Formula — as the code writes it.**

```
rho = 1.225
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:486` — `_resolve_level_flight_op`

**Consumed by.**

- in this graph: [[lfop-cl-target|Level-flight target lift coefficient]]

**Source.** 🟢 SOURCED

> ISO 2533:1975 / U.S. Standard Atmosphere 1976, sea-level standard density; used as the ISA reference throughout Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.6.2
>
> — via `aircraft-design-scholz, aerosandbox-expert`

**The source states it as.**

```
rho_0 = 1.225 kg/m^3 at 0 m ISA
```

**⚠️ Divergence from the source.** Value is exact. It is hardcoded rather than read from asb.Atmosphere, so the level-flight solve is sea-level-only even when the operating point specifies an altitude.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:486`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
