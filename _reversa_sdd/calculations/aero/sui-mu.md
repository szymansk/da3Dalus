---
name: sui-mu
symbol: μ
kind: constant
unit: Pa·s
cluster: aero-polars
user_visible: false
source_status: PARTIAL
---

# Dynamic viscosity (suitability)

**Definition.** Dynamic viscosity used for the root/tip Reynolds computation.

**Value.** `1.81e-5`

**Formula — as the code writes it.**

```
_MU = 1.81e-5  # Pa·s  dynamic viscosity
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/suitability_service.py:75` — `_MU`

**Consumed by.**

- in this graph: [[sui-re-root|Root-chord Reynolds number]]
- outside it: `_compute_re:121`

**Source.** 🟡 PARTIAL

> ICAO Standard Atmosphere / ISO 2533:1975, sea level: μ = 1.7894e-5 Pa·s (Sutherland at 288.15 K)
>
> — via `aerodynamics-expert`

**The source states it as.**

```
μ_ISA,SL = 1.7894e-5 Pa·s
```

**⚠️ Divergence from the source.** The comment claims 'ISA sea-level' but 1.81e-5 is not the ISA value — it corresponds to ≈293–295 K. Worse, it is used alongside _NU = 1.46e-5 in the same file, which IS the ISA value; the two cannot both be ISA SL.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `# ISA sea-level for Re computation (ν = μ/ρ ≈ 1.81e-5/1.225 m²/s)
_MU = 1.81e-5  # Pa·s  dynamic viscosity`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
