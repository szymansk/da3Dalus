---
name: tos-cd-at-cl
symbol: cd
kind: quantity
unit: dimensionless
cluster: aero-strips
user_visible: false
source_status: PARTIAL
---

# Section cd at a target CL and trip position

**Definition.** 2D drag coefficient interpolated from the NeuralFoil polar at the requested CL.

**Formula — as the code writes it.**

```
return float(np.interp(cl_target, cl_sorted, cd_sorted))
```

**Inputs.** [[tos-alpha-grid|Alpha grid for cd lookup]] · [[tos-model-size|NeuralFoil model size (optimiser)]] · [[tos-xtr-lower|Lower-surface trip position]] · [[bwsd-re-local|Local section Reynolds number]] · [[saoa-cl|Section lift coefficient (Kutta-Joukowski)]]

**Produced by.** `app/services/turbulator_optimizer_service.py:175` — `_cd_at_cl_xtr`

**Consumed by.**

- in this graph: [[cdftp-cd-clean|Clean section drag (installed-turbulator path)]] · [[cdftp-cd-tripped|Tripped section drag (installed-turbulator path)]] · [[tos-cd-clean|Natural-transition section drag]] · [[tos-cd-nearest-fallback|Nearest-neighbour cd fallback]] · [[tos-cd-values|cd sweep over the trip grid]]

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
