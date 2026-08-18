---
name: zero-crossing-fallback-index
kind: quantity
unit: index
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Zero-lift nearest-point fallback

**Definition.** When CL never changes sign, the point of minimum \|CL\| is returned instead of an interpolation.

**Formula — as the code writes it.**

```
i = int(np.argmin(np.abs(cl)))
```

**Inputs.** [[cl-values|Lift coefficient array]]

**Produced by.** `app/services/analysis_service.py:157` — `_interpolate_zero_crossing`

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> Numerical substitution (argmin\|CL\|) with no literature counterpart; no source treats a nearest-point as equivalent to a zero-lift condition.
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Undeclared fallback (ADR 0020): the response cannot distinguish an interpolated CD0 from a nearest-point substitute except by index==None.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
