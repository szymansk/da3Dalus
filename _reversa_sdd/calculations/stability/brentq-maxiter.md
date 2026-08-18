---
name: brentq-maxiter
symbol: maxiter
kind: constant
unit: – (count)
cluster: stability
user_visible: false
source_status: PARTIAL
---

# Brent root-finder iteration cap

**Definition.** Maximum Brent iterations before the solve is abandoned.

**Value.** `50`

**Formula — as the code writes it.**

```
trimmed_deflection = brentq(residual, lower, upper, xtol=1e-6, maxiter=50)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/aerobuildup_trim_service.py:214` — `trim_with_aerobuildup`

**Consumed by.**

- in this graph: [[trimmed-deflection|Trimmed control deflection]]
- outside it: `app/services/aerobuildup_trim_service.py:214`

**Source.** 🟡 PARTIAL

> R. P. Brent, "Algorithms for Minimization without Derivatives", Prentice-Hall 1973, Ch. 4; scipy.optimize.brentq (SciPy documentation, default maxiter=100). No source prescribes 50.
>
> — via `aerosandbox-expert`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** Half the SciPy default, unattributed. Because each iteration is a full AeroBuildup run (which AeroSandbox documents as vectorisable across operating points in a single .run() — an option not used here), the cap bounds iterations but not wall-clock time, and no timeout exists.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Each iteration is a full AeroBuildup run; the cap is unbounded in wall-clock terms and no timeout exists.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
