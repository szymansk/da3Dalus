---
name: alr-best-ld-cl
symbol: CL*
kind: quantity
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: SOURCED
---

# CL at maximum L/D (closed form)

**Definition.** CL that maximises L/D for the parabolic polar CD = cd0 + k(CL−cl0)².

**Formula — as the code writes it.**

```
return math.sqrt(cl0**2 + cd0 / k)
```

**Inputs.** [[alr-polar-cd0|Airfoil cd0 (parabolic fit vertex)]] · [[alr-polar-k|Airfoil polar curvature k]] · [[alr-polar-cl0|CL at minimum drag (cl0)]]

**Produced by.** `app/services/airfoil_low_re_service.py:760` — `best_ld_cl`

**Consumed by.**

- in this graph: [[alr-match|Match component of score_target_cl]]
- outside it: `score_target_cl:1038`

**Source.** 🟢 SOURCED

> Anderson 6e §6.7.2 — at (L/D)_max the zero-lift drag equals the induced drag, giving C_L* = √(C_D0/k) (stated there as √(πeAR·C_D0))
>
> — via `aerodynamics-expert`

**The source states it as.**

```
C_L* = √(C_D0/k)  [un-offset polar]
```

**⚠️ Divergence from the source.** For the offset polar C_D = cd0 + k(C_L−cl0)², maximising C_L/C_D gives k·u² + 2k·cl0·u − cd0 = 0 with u = C_L−cl0, hence C_L* = +√(cl0² + cd0/k). I verified this algebra: the IMPLEMENTED formula is correct and reduces to Anderson's at cl0 = 0. The docstring's first derivation block (lines 725-733, 'C_L* = cl0 + √(cd0/k)') is wrong and should be deleted — two contradictory formulas are documented for one quantity.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The docstring contains a first, wrong derivation block (lines 725-733, 'CL* = cl0 + sqrt(cd0/k)') immediately followed by the correct one — two contradictory formulas documented for the same quantity.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `CL* = u + cl0 = ±sqrt(cl0² + cd0/k); take positive root.
Special case cl0=0: CL* = sqrt(cd0/k). ✓`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
