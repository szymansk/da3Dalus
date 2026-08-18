---
name: lfop-altitude
symbol: altitude
kind: constant
unit: m
cluster: aero-strips
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/aero-strips
  - class/numerical-tolerance
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# Fallback altitude

**Definition.** The fallback operating point is always at sea level.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `0.0`

**Formula — as the code writes it.**

```
atmosphere = asb.Atmosphere(altitude=0.0)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:506` — `_resolve_level_flight_op`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `OperatingPointSchema.altitude`

**Source.** 🟡 PARTIAL

> AeroSandbox docs (asb.Atmosphere, U.S. 1976 COESA standard; altitude in metres)
>
> — via `aerosandbox-expert`

**The source states it as.**

```
ISA sea level = 0 m
```

**⚠️ Divergence from the source.** Sea level is the standard reference datum, so 0.0 is a defensible DEFAULT. Pinning it means the fallback operating point can never represent a high-altitude UAV, and it is consistent with lfop-rho and saoa-nu also being sea-level-only.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/section_aoa_service.py:506,540`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
