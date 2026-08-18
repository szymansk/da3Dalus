---
name: air-density-sea-level-alias
symbol: AIR_DENSITY_SEA_LEVEL
kind: constant
unit: kg/m^3
cluster: powertrain
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/powertrain
  - class/unclassified-constant
  - source/sourced
  - audit/confirmed
  - flag/anomaly
---

# Sea-level density alias (sizing)

**Definition.** Backward-compatibility alias for endurance_service.RHO_SEA_LEVEL, kept for existing tests.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `1.225 (via RHO_SEA_LEVEL import)`

**Formula — as the code writes it.**

```
AIR_DENSITY_SEA_LEVEL = RHO_SEA_LEVEL  # kept for backward compat with existing tests
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_sizing_service.py:41` — `AIR_DENSITY_SEA_LEVEL`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Air density at altitude (sizing)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/tests/test_powertrain_sizing_service.py:19`

**Source.** 🟢 SOURCED

> Sadraey (2013), §8.8.1 Example 8.3 evaluates (0.653/1.225)^1.2, and §4.6 Eq. 4.51 defines sigma = rho/rho_o; rho_o = 1.225 kg/m^3 is the ISA sea-level reference.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
rho_o = 1.225 kg/m^3
```

**⚠️ Anomaly.** NO PRODUCTION CONSUMER — the alias exists only so tests can import it; the service body uses RHO_SEA_LEVEL directly (line 52).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# kept for backward compat with existing tests`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
