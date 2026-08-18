---
name: alr-re-interp-fraction
symbol: t
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: SOURCED
---

# ln(Re) interpolation fraction

**Definition.** Blend weight between two Re grid rows, linear in natural log of Re.

**Formula — as the code writes it.**

```
t = (math.log(re_query) - math.log(lo)) / (math.log(hi) - math.log(lo))
```

**Inputs.** [[low-re-grid|Absolute low-Re grid]]

**Produced by.** `app/services/airfoil_low_re_service.py:351` — `interpolate_polar_at_re`

**Consumed by.**

- outside it: `_interpolate_rows:381`

**Source.** 🟢 SOURCED

> Sharpe, PhD thesis (MIT 2024), §7.2 (NeuralFoil encoding): 'Reynolds number → ln(Re), because C_D ~ Re^-p — power-law in user space = affine in latent space'
>
> — via `aerosandbox-expert`

**The source states it as.**

```
z_Re = ln(Re)
```

**⚠️ Divergence from the source.** None. The docstring's claim at line 311 ('matching NeuralFoil's training encoding') is correct and is now citable — it simply carried no reference.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Docstring justifies it as 'matching NeuralFoil's training encoding' (line 311) — a claim about the surrogate's internals with no citation.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Linear in ln(Re)
t = (math.log(re_query) - math.log(lo)) / (math.log(hi) - math.log(lo))`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
