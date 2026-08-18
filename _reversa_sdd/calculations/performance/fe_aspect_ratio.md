---
name: fe_aspect_ratio
symbol: AR
kind: quantity
unit: -
cluster: perf-envelope
user_visible: false
source_status: SOURCED
---

# Aspect ratio (gust path)

**Definition.** Wing aspect ratio derived from reference span and area for the Helmbold fallback.

**Formula — as the code writes it.**

```
ar = (b_ref_m**2) / wing_area_m2
```

**Inputs.** [[fe_b_ref|Reference span]] · [[fe_wing_area|Reference wing area]]

**Produced by.** `app/services/flight_envelope_service.py:343` — `compute_vn_curve`

**Consumed by.**

- in this graph: [[fe_cl_alpha_helmbold|Finite-span lift-curve slope (Helmbold fallback)]]

**Source.** 🟢 SOURCED

> Anderson, Fundamentals of Aerodynamics 6e, §5.3 (standard definition).
>
> — via `aero`

**The source states it as.**

```
AR = b^2 / S
```

**⚠️ Divergence from the source.** Definition is not in question; the second-producer problem is (ADR 0022). ctx['aspect_ratio'] already exists and is what mission_kpi_service reads.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer of AR: assumption_compute_service caches ctx['aspect_ratio'], which endurance_service and mission_kpi_service read. The gust path recomputes it locally instead.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
