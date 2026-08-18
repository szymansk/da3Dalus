---
name: ss-rho-param
symbol: rho
kind: parameter
unit: kg/m^3
cluster: powertrain
user_visible: true
source_status: SOURCED
code_audit: NOT_VERIFIED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/sourced
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Air density (solution space input)

**Definition.** Air density used for every solution-space computation. Fixed at ISA sea level unless the caller overrides it; there is no altitude input.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `1.225`

**Formula — as the code writes it.**

```
rho = assumptions.rho
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:93` — `SolutionSpaceAssumptions.rho`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Dynamic pressure` · `Aerodynamic power at cruise` · `Aerodynamic power at top speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:343` · `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🟢 SOURCED

> Sadraey (2013), §4.6, Eq. 4.51 (sigma = rho/rho_o) and §8.8.1 Example 8.3 ((0.653/1.225)^1.2): rho_o = 1.225 kg/m^3 is the ISA sea-level density.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
rho_o = 1.225 kg/m^3 (ISA sea level); sigma = rho/rho_o, with sigma = (1 - 6.873e-6 h)^4.26 in the troposphere (Eq. 4.94a)
```

**⚠️ Divergence from the source.** The sea-level VALUE is correct and cited. What has no source is the absence of any altitude correction: Sadraey Eq. 4.51 and Eq. 4.94a make sigma a required input to every power-loading calculation, and Sadraey also lapses engine power with altitude (Eq. 8.16). The solution space has no altitude input at all, so every number it returns is a sea-level number, and nothing in the response says so.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The solution space has no altitude parameter at all, unlike the other two services which both apply an exponential density correction — three services, two altitude models, one of them absent (notes F4). The module also declares an unused RHO_DEFAULT for the same value (line 65).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Air density [kg/m³] (ISA sea-level default)"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
