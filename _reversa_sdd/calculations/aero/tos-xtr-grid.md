---
name: tos-xtr-grid
symbol: XTR_GRID
kind: constant
unit: x/c
cluster: aero-strips
user_visible: true
source_status: PARTIAL
---

# Turbulator trip-position sweep grid

**Definition.** 15-point x/c grid from 0.2 to 0.9 over which the trip position is optimised.

**Value.** `np.linspace(0.2, 0.9, 15)`

**Formula — as the code writes it.**

```
XTR_GRID: np.ndarray = np.linspace(0.2, 0.9, 15)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/turbulator_optimizer_service.py:53` — `XTR_GRID`

**Consumed by.**

- in this graph: [[tos-cd-values|cd sweep over the trip grid]] · [[tos-confidence-probe-xtr|Confidence-probe trip position]] · [[tos-global-xtr-opt|Whole-wing optimal trip position]] · [[tos-xtr-opt|Optimal trip position]]
- outside it: `app/services/turbulator_optimizer_service.py:optimize_section_xtr` · `app/services/turbulator_optimizer_service.py:run_turbulator_optimizer`

**Source.** 🟡 PARTIAL

> Sharpe, PhD thesis (MIT, 2024) §7.2.5 (forced trip location x_tr,forced/c is a trained NeuralFoil input: 80% of training cases natural, 20% uniform on [0, 1]); RC-Network Wiki, 'Turbulator (Aerodynamik)', wiki.rc-network.de/wiki/Turbulator
>
> — via `aerosandbox-expert, rc-aircraft-designer, aerodynamics-expert`

**The source states it as.**

```
NeuralFoil accepts forced trip positions across the full [0, 1] chord; RC practice: zig-zag/crinkle tape 'applied near the leading edge', positioned 'at the location where natural transition would otherwise be delayed'
```

**⚠️ Divergence from the source.** The INPUT is sourced; the grid bounds are not. Two concerns. (1) The grid starts at 0.2 c, but the cited RC practice puts tape near the leading edge — the region actual modellers use is partly outside the search space. (2) The grid ends at 0.9 c, well aft of natural transition for most low-Re sections, so those points are near-duplicates of the clean case and the 15-point budget is spent unevenly. The warning text also hardcodes the string '[0.2, 0.9]', so an overridden xtr_grid yields a false message.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Turbulators are an RC/low-Re practice with no transport-category counterpart, so no transport constant leaked in here — but equally, no academic source in the consulted set fixes the practical placement window at this scale. Treat 0.2-0.9 as an unvalidated design choice.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Magic bounds: 0.2/0.9/15 carry no cited source, and the boundary-minimum warning text hardcodes '[0.2, 0.9]' so an overridden xtr_grid produces a wrong message.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/turbulator_optimizer_service.py:53`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
