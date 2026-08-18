---
name: tos-cd-nan
symbol: —
kind: constant
unit: dimensionless
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# NaN cd on NeuralFoil failure

**Definition.** cd is NaN when NeuralFoil raises or returns all-NaN outputs.

**Value.** `float("nan")`

**Formula — as the code writes it.**

```
return float("nan")
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:179` — `_cd_at_cl_xtr`

**Consumed by.**

- outside it: `tos-argmin-finite`

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.1 (NeuralFoil 'always returns an answer' — static computational graph, no iterative solver, unlike XFoil)
>
> — via `aerosandbox-expert`

**⚠️ Divergence from the source.** Because the cited design guarantees an answer, a NaN here indicates a wrapper/exception path or an all-NaN guard trip, not a model non-convergence. NaN is a defensible sentinel; propagating it to a user-visible field without an accompanying warning is not.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:153,179`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
