---
name: w-eq-tol
kind: constant
unit: mm³ (also reused as mm)
cluster: structure
user_visible: false
source_status: NO_SOURCE_FOUND
---

# Section-modulus float-equality tolerance

**Definition.** Tolerance used both for W_stock ≥ erf_W acceptance and for the containment-band OD comparison, so float rounding does not reject an exactly-adequate stock item.

**Value.** `1e-9`

**Formula — as the code writes it.**

```
_W_EQ_TOL = 1e-9
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_plan_service.py:56` — `_W_EQ_TOL`

**Consumed by.**

- outside it: `app/services/spar_plan_service.py:155` · `app/services/spar_plan_service.py:159` · `app/services/spar_plan_service.py:169`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `aircraft-design-scholz + rc-aircraft-designer (floating-point equality tolerance, not an engineering quantity)`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Name and docstring declare the unit as mm³, but the same constant is used as a millimetre tolerance in the containment-band comparison at lines 155 and 169 (da > max_od_mm + _W_EQ_TOL). One constant, two incompatible units.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `#: Float-equality tolerance (mm³) for W_stock ≥ erf_W comparisons. Avoids rejecting stock whose W equals erf_W up to floating-point rounding.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
