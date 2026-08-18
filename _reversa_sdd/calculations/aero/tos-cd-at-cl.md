---
name: tos-cd-at-cl
symbol: cd
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
node_class: derived
tags:
  - cluster/aero-strips
  - class/derived
  - source/partial
  - flag/divergence
---

# Section cd at a target CL and trip position

**Definition.** 2D drag coefficient interpolated from the NeuralFoil polar at the requested CL.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return float(np.interp(cl_target, cl_sorted, cd_sorted))
```

**Inputs.**

- [[tos-alpha-grid|Alpha grid for cd lookup]]
- [[tos-model-size|NeuralFoil model size (optimiser)]]
- [[tos-xtr-lower|Lower-surface trip position]]
- [[bwsd-re-local|Local section Reynolds number]]  — *⊣ limit*
- [[saoa-cl|Section lift coefficient (Kutta-Joukowski)]]

**Produced by.** `app/services/turbulator_optimizer_service.py:175` — `_cd_at_cl_xtr`

**Consumed by.**

- in this graph: `Clean section drag (installed-turbulator path)` · `Tripped section drag (installed-turbulator path)` · `Natural-transition section drag` · `Nearest-neighbour cd fallback` · `cd sweep over the trip grid`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🟡 PARTIAL

> Anderson, Fundamentals of Aerodynamics 6e, §4.11 (the drag polar: cd as a function of cl for a section at given Re)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
cd = cd(cl; Re, transition state)
```

**⚠️ Divergence from the source.** Building a polar by alpha-sweep and interpolating at a target cl is standard. Unattributable detail: sorting by cl then np.interp assumes single-valued cd(cl), which fails once the sweep passes stall (cl folds back) — at +14 deg with a low-Re section this is reachable.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:175`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
