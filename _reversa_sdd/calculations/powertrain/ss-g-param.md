---
name: ss-g-param
symbol: g
kind: parameter
unit: m/s^2
cluster: powertrain
user_visible: true
source_status: PARTIAL
code_audit: NOT_VERIFIED
node_class: unclassified-parameter
tags:
  - cluster/powertrain
  - class/unclassified-parameter
  - source/partial
  - surface/user-visible
  - audit/not-verified
  - flag/anomaly
  - flag/divergence
---

# Gravitational acceleration (solution space input)

**Definition.** Standard gravity used in the lift-coefficient relation.

⚪ **Unclassified parameter.** Not yet decided whether this is a user input or an internal tuning value.

**Value.** `9.80665`

**Formula — as the code writes it.**

```
g = assumptions.g
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/schemas/powertrain_solution_space.py:98` — `SolutionSpaceAssumptions.g`

⚪ **Not verified.** This node was not covered by the audit pass; treat its line and formula as extracted-but-unchecked.

**Consumed by.**

- in this graph: `Level-flight lift coefficient` · `Aerodynamic power at cruise` · `Aerodynamic power at top speed`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/powertrain_solution_space_service.py:344` · `app/services/powertrain_solution_space_service.py:349` · `app/services/powertrain_solution_space_service.py:350`

**Source.** 🟡 PARTIAL

> No expert vault attributes the numeric value; 9.80665 m/s^2 is the standard acceleration of free fall fixed by the 3rd CGPM (1901). Its role in the code is cited: Sadraey (2013) §4.6 uses W = m g inside C_L = 2W/(rho V^2 S) in the Eq. 4.55 derivation.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
C_L = 2 m g / (rho V^2 S)  (Sadraey, Eq. 4.55 derivation)
```

**⚠️ Divergence from the source.** Sadraey treats g as a physical constant, never a design variable. The code exposes it as a user-tunable parameter bounded only by gt=0, which no source supports for a 0.5-15 kg aircraft design tool.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Exposed as a user-tunable query parameter with no lower bound beyond gt=0 — a design tool for 0.5-15 kg RC/UAV aircraft has no reason to let the user vary g, and the module's own G_DEFAULT for the same value is dead (line 64).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `field description: "Gravitational acceleration [m/s²]"`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
