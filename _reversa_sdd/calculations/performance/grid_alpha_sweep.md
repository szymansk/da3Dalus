---
name: grid_alpha_sweep
kind: constant
unit: deg
cluster: perf-oppoints
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Grid-search alpha sweep

**Definition.** Alpha candidates evaluated by the grid-search fallback.

**Value.** `-4.0 to 20.0 deg, 13 points (2 deg step)`

**Formula — as the code writes it.**

```
alpha_candidates = np.linspace(-4.0, 20.0, 13)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/operating_point_generator_service.py:819` — `_grid_search_trim`

**Consumed by.**

- in this graph: [[alpha_trimmed|Trimmed angle of attack]]
- outside it: `app/services/operating_point_generator_service.py:821-830`

**Source.** 🔴 NO SOURCE FOUND

> Bounding authority: Sadraey §5.4.3 / Scholz 08_HighLift §8.2 — stall angle α_s typically 12–16°; Anderson 6e §4.13 — massive separation above ≈15°
>
> — via `aircraft-design-scholz, aerodynamics-expert`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** −4° to +20° in 13 points has no source. The upper 4–8° of the sweep lie beyond stall for any conventional section, and no CL_max check is applied, so the grid can return a 'trimmed' point at a physically stalled alpha. The 2° step also caps achievable trim precision: with dCm/dα of order 0.01–0.03 per degree, a 2° grid cannot resolve the 0.35 trim-score threshold it feeds.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 2° resolution limits the achievable trim precision, and the sweep can return alphas above the physical stall since no CL_max check is applied.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-oppoints|perf-oppoints]] · generated from the 2026-08-18 extraction.*
