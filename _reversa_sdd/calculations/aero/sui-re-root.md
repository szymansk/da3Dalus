---
name: sui-re-root
symbol: Re_root
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: true
source_status: SOURCED
---

# Root-chord Reynolds number

**Definition.** Query Reynolds number at the root chord and slider speed.

**Formula — as the code writes it.**

```
return _RHO * speed_ms * chord_m / _MU
```

**Inputs.** [[sui-rho|ISA sea-level density (suitability)]] · [[sui-mu|Dynamic viscosity (suitability)]]

**Produced by.** `app/services/suitability_service.py:121` — `_compute_re`

**Consumed by.**

- in this graph: [[sui-re-clamped|Grid-clamped Reynolds + clamp flag]] · [[sui-tip-re-flag|tip_re_flag]]
- outside it: `search_suitability:259,272,275` · `SuitabilityQuery.reynolds:688`

**Source.** 🟢 SOURCED

> Anderson 6e §1.7 — Re = ρ∞V∞c/μ∞ with chord as reference length
>
> — via `aerodynamics-expert, rc-aircraft-designer`

**The source states it as.**

```
Re_c = ρVc/μ
```

**⚠️ Divergence from the source.** Identical form. Cross-check: RC-Network Wiki 'Re-Zahl' gives the model-flight shortcut Re ≈ v[m/s]·t[mm]·70, i.e. an implied ν = 1.43e-5 — same regime, confirming the magnitude.

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `return _RHO * speed_ms * chord_m / _MU`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
