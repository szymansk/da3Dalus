---
name: low-re-grid
symbol: —
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: PARTIAL
---

# Absolute low-Re grid

**Definition.** 13 log-spaced Reynolds numbers at which every airfoil's polar is precomputed.

**Value.** `[40000, 50000, 60000, 75000, 90000, 110000, 130000, 160000, 200000, 250000, 350000, 500000, 750000]`

**Formula — as the code writes it.**

```
_DEFAULT_LOW_RE_GRID: list[int] = [40_000, ... 750_000]
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/settings.py:60` — `_DEFAULT_LOW_RE_GRID`

**Consumed by.**

- in this graph: [[alr-re-interp-fraction|ln(Re) interpolation fraction]] · [[sui-per-lens-re|Per-lens Reynolds number]] · [[sui-re-clamped|Grid-clamped Reynolds + clamp flag]]
- outside it: `compute_airfoil_low_re:468` · `interpolate_polar_at_re (arg, unused)` · `suitability_service:254` · `_clamp_re_to_grid:124` · `compute_re_cd0_reference:808`

**Source.** 🟡 PARTIAL

> Anderson 6e §20.3.2 (Re_c = 100k as the representative low-Re airfoil case; laminar separation on both surfaces); Sharpe (2024) §7.2.4 (NeuralFoil confidence collapses near C_L ≈ 1.0 at Re_c ≈ 80×10³ where the LSB precariously forms); RC-Network Wiki 'Re-Zahl' (model aircraft operate near Re_crit; coefficients change strongly with Re there)
>
> — via `aerodynamics-expert, aerosandbox-expert, rc-aircraft-designer`

**⚠️ Divergence from the source.** The range and the 'dense below 250k because the LSB governs' rationale are both supportable from these sources, and the span is genuinely well matched to 0.5–15 kg RC/UAV. The 13 specific grid points are an unattributable discretisation choice.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Range is well matched to RC/UAV scale; no source cited for the bubble-governed claim.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Absolute Re grid for the low-Re backfill (13 log-spaced points).
# Dense below 250k where the laminar-separation bubble governs; coarser above.`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
