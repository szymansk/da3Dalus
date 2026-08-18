---
name: trim-bracket-test
symbol: —
kind: quantity
unit: – (dimensionless)
cluster: stability
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Root bracketing test

**Definition.** Sign test on the residual at both deflection bounds; a positive product means the target is unreachable inside the bounds.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
if f_lower * f_upper > 0:
```

**Inputs.**

- [[aerobuildup-trim-residual|AeroBuildup trim residual]]
- [[deflection-bounds|Trim search bounds]]  — *⊣ limit*

**Produced by.** `app/services/aerobuildup_trim_service.py:186` — `trim_with_aerobuildup`

**Consumed by.**

- outside it: `app/services/aerobuildup_trim_service.py:187-211 (non-converged early return)`

**Source.** 🟢 SOURCED

> R. P. Brent, "Algorithms for Minimization without Derivatives", Prentice-Hall 1973, Ch. 4 — the method requires a sign-changing bracket [a,b] with f(a)·f(b) < 0; scipy.optimize.brentq raises ValueError otherwise. Engineering meaning of the failure: Sadraey §12.5.5 step 19 — if the required deflection cannot be achieved within the limit, "no elevator can satisfy trim; redesign tail/landing gear."
>
> — via `aircraft-design-scholz + aerosandbox-expert`

**The source states it as.**

```
f(a)·f(b) < 0 required for a guaranteed bracketed root (Brent 1973, Ch. 4)
```

**⚠️ Divergence from the source.** The test is correct. The response is not: Sadraey treats an unachievable trim as a design failure requiring upstream redesign, whereas the code returns trimmed_deflection = 0.0 (aerobuildup_trim_service.py:207) — a fabricated value indistinguishable from a genuine zero-deflection trim to any consumer that ignores `converged`.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** On failure the result is returned with `trimmed_deflection=0.0` (line 207) rather than None — a fabricated value that is indistinguishable from a genuine zero-deflection trim to any consumer that ignores `converged`.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"AeroBuildup trim root not bracketed for aeroplane %s: ... target %s=%g not achievable within [%g, %g]"`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
