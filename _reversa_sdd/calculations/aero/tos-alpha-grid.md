---
name: tos-alpha-grid
symbol: _ALPHA_GRID
kind: constant
unit: deg
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/divergence
  - solver-adjacent/neuralfoil
---

# Alpha grid for cd lookup

**Definition.** 37-point alpha grid from -4° to 14° on which NeuralFoil polars are evaluated.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `np.linspace(-4.0, 14.0, 37)`

**Formula — as the code writes it.**

```
_ALPHA_GRID = np.linspace(-4.0, 14.0, 37)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:60` — `_ALPHA_GRID`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Section cd at a target CL and trip position` · `Mean NeuralFoil analysis confidence`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/turbulator_optimizer_service.py:_cd_at_cl_xtr` · `app/services/turbulator_optimizer_service.py:optimize_section_xtr`

**Source.** 🔴 NO SOURCE FOUND

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (NeuralFoil training alpha distribution: 95% within [-17 deg, +18 deg])
>
> — via `aerosandbox-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** [-4, +14] lies wholly inside the trained band, so the grid is safe, but neither the bounds nor the 0.5 deg step are attributable. A 37-point sweep is used only to interpolate cd at one cl, so most of it is discarded work.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:60`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
