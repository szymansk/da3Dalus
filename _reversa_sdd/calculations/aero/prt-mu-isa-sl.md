---
name: prt-mu-isa-sl
symbol: μ
kind: constant
unit: Pa·s
cluster: aero-polars
user_visible: false
source_status: PARTIAL
node_class: physical-constant
tags:
  - cluster/aero-polars
  - class/physical-constant
  - source/partial
  - flag/divergence
  - flag/physical
---

# ISA sea-level dynamic viscosity

**Definition.** Dynamic viscosity used for all aircraft-level Re labels.

**Physical constant.** A value of nature. It must be identical everywhere it appears — a second definition is a defect by construction, not a judgement call.
*Identified as: dynamic viscosity of air.*

**Value.** `1.81e-5`

**Formula — as the code writes it.**

```
_MU_ISA_SL: float = 1.81e-5
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:46` — `_MU_ISA_SL`

**Consumed by.**

- in this graph: `Aircraft-level Reynolds number (V-band label)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `_reynolds_number_from_v:71` · `lookup_cd0_at_v:97`

**Source.** 🟡 PARTIAL

> ICAO Standard Atmosphere / ISO 2533:1975, sea level (Sutherland's law at 288.15 K): μ = 1.7894e-5 Pa·s
>
> — via `aerodynamics-expert`

**The source states it as.**

```
μ_ISA,SL = 1.7894e-5 Pa·s
```

**⚠️ Divergence from the source.** Code uses 1.81e-5 but labels it 'ISA sea-level'. 1.81e-5 is air at ≈293–295 K, +1.2% high. Re labels come out 1.2% low. Label is wrong; magnitude is defensible.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# ISA sea-level dynamic viscosity [Pa·s]
_MU_ISA_SL: float = 1.81e-5`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
