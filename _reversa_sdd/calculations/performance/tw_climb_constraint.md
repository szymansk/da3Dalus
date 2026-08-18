---
name: tw_climb_constraint
symbol: (T/W)_climb
kind: quantity
unit: dimensionless
cluster: perf-matching
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-matching
  - class/derived
  - source/sourced
  - surface/user-visible
  - audit/confirmed
  - flag/divergence
---

# Climb constraint T/W

**Definition.** T/W required to sustain the target climb gradient at the clean polar.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
gamma_rad = math.radians(gamma_deg); q = 0.5 * rho * v_climb * v_climb; k = 1.0 / (math.pi * e * ar); drag_over_weight = q * cd0 / ws + ws * k / q; return math.sin(gamma_rad) + drag_over_weight
```

**Inputs.**

- [[ws_range_mc|W/S sweep vector]]
- [[mode_default_gamma_climb|Mode default climb gradient]]  — *⤵ fallback*
- [[v_md|Minimum-drag speed]]
- [[ar_resolved|Resolved aspect ratio]]  — *⤵ fallback*
- [[rho_sl|Sea-level ISA density]]  — *⤵ fallback*

**Produced by.** `app/services/matching_chart_service.py:413` — `_climb_constraint`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Re-refined climb T/W per W/S`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `climb_tw:865` · `constraints_raw 'Climb':929` · `MatchingChartResponse.constraints`

**Source.** 🟢 SOURCED

> Scholz, Flugzeugentwurf 05_PreliminarySizing §5.3 Eq. (5.13) (second-segment-climb-gradient): from T = D + m*g*sin(gamma) and L = m*g*cos(gamma) ~ m*g, dividing by m*g gives T/(m*g) = 1/E + sin(gamma) = D/W + sin(gamma). Exactly the code's implementation.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
T/(m*g) = D/W + sin(gamma)
```

**⚠️ Divergence from the source.** Citation error: the docstring credits 'Anderson 6e §6.3'. The correct attribution is Scholz §5.3 Eq. 5.13. Also, Scholz applies this with the engine-out scaling n_E/(n_E-1) and at the CS-25 second-segment gradients (2.4/2.7/3.0%); the code applies it all-engines at an arbitrary gamma, which is the right simplification for a single-motor model but is not the source's use.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `"T/W required to sustain a climb gradient γ — Anderson 6e §6.3. T/W = sin(γ) + D/W (clean polar)"`

---
*Cluster [[_index-perf-matching|perf-matching]] · generated from the 2026-08-18 extraction.*
