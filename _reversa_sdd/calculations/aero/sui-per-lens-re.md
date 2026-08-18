---
name: sui-per-lens-re
symbol: Re_lens
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: SOURCED
---

# Per-lens Reynolds number

**Definition.** Reynolds number for each target-CL lens, from that lens's design speed and the root chord.

**Formula — as the code writes it.**

```
raw = v_mps * chord_m / _NU
clamped, _ = _clamp_re_to_grid(raw, re_grid)
```

**Inputs.** [[sui-nu|Kinematic viscosity for per-lens Re]] · [[low-re-grid|Absolute low-Re grid]]

**Produced by.** `app/services/suitability_service.py:383` — `_per_lens_re`

**Consumed by.**

- outside it: `search_suitability:393-395,452-464,414-427`

**Source.** 🟢 SOURCED

> Anderson 6e §1.7 — Re = Vc/ν
>
> — via `aerodynamics-expert`

**The source states it as.**

```
Re = Vc/ν
```

**⚠️ Divergence from the source.** Correct form and, uniquely in this cluster, the correct ISA viscosity. Diverges from its sibling _compute_re by 1.2% (see sui-nu).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Uses _NU while the sibling _compute_re uses _RHO/_MU — see sui-nu.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `raw = v_mps * chord_m / _NU
clamped, _ = _clamp_re_to_grid(raw, re_grid)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
