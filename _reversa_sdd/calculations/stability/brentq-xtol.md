---
name: brentq-xtol
symbol: xtol
kind: constant
unit: deg
cluster: stability
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: numerical-tolerance
tags:
  - cluster/stability
  - class/numerical-tolerance
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - solver-adjacent/aerobuildup
---

# Brent root-finder tolerance

**Definition.** Absolute convergence tolerance on the deflection variable for the Brent root solve.

**Numerical tolerance.** A solver or comparison epsilon, not a domain value. ADR 0023 does not apply.

**Value.** `1e-6`

**Formula — as the code writes it.**

```
trimmed_deflection = brentq(residual, lower, upper, xtol=1e-6, maxiter=50)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/aerobuildup_trim_service.py:214` — `trim_with_aerobuildup`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Trimmed control deflection`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/aerobuildup_trim_service.py:214`

**Source.** 🟡 PARTIAL

> The algorithm is citable: R. P. Brent, "Algorithms for Minimization without Derivatives", Prentice-Hall 1973, Ch. 4 (the inverse-quadratic-interpolation/bisection hybrid); implemented as scipy.optimize.brentq (SciPy documentation). Neither source prescribes 1e-6 as a tolerance — SciPy's own defaults are xtol=2e-12, rtol≈8.9e-16.
>
> — via `aerosandbox-expert`

**The source states it as.**

```
Brent's method: guaranteed bracketing bisection with inverse quadratic interpolation acceleration (Brent 1973, Ch. 4)
```

**⚠️ Divergence from the source.** The tolerance is a code choice, not a sourced one, and it is mismatched in both directions: 1e-6 degrees is ~7 orders finer than any servo resolution, while the function being sampled is an AeroBuildup evaluation that AeroSandbox itself characterises as a semi-empirical component buildup (workbook-style, Hoerner/Raymer/Roskam/Drela-derived). Tightening beyond the model's own fidelity buys iterations, not accuracy — and each iteration is a full solver run.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** 1e-6 degrees is ~7 orders of magnitude finer than any servo resolution and far below the fidelity of the AeroBuildup model being sampled — it buys iterations, not accuracy.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
