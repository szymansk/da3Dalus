---
name: prt-re-aircraft
symbol: Re
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Aircraft-level Reynolds number (V-band label)

**Definition.** Reynolds label used to index the V-band polar table, at main-wing MAC and ISA SL.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return rho * v_mps * mac_m / mu
```

**Inputs.**

- [[prt-rho-default|Default air density (ISA SL)]]  — *⤵ fallback*
- [[prt-mu-isa-sl|ISA sea-level dynamic viscosity]]

**Produced by.** `app/services/polar_re_table_service.py:89` — `_reynolds_number_from_v`

**Consumed by.**

- in this graph: `cd0 at query velocity` · `polar_re_table_degenerate`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `polar_re_table_service.lookup_cd0_at_v:129` · `polar_re_table_service._fit_band_with_ar:273` · `polar_re_table_service._fallback_row:308` · `polar_re_table_service.build_re_table:451` · `app/schemas/polar_re_table.py PolarReTableRow.re`

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e (2016), §1.7 — Re = ρ∞V∞c/μ∞
>
> — via `aerodynamics-expert`

**The source states it as.**

```
Re = ρ V L / μ
```

**⚠️ Divergence from the source.** Identical form. Reference length is main-wing MAC at ISA SL; that is a labelling convention, not a physical per-component Re — the docstring already says so.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Docstring states it is 'a label for V-based lookup, NOT the per-component Re_local used by AeroBuildup' — a name that reads as a physical Re but is not the one the solver uses.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `return rho * v_mps * mac_m / mu`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
