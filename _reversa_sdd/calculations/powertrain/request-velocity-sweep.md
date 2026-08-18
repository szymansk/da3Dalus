---
name: request-velocity-sweep
symbol: v_min_ms / v_max_ms / n_points
kind: parameter
unit: m/s, count
cluster: powertrain
user_visible: true
source_status: NO_SOURCE_FOUND
---

# Velocity sweep range and resolution

**Definition.** Bounds and sample count of the airspeed sweep; np.linspace generates the sample points.

**Value.** `v_min_ms=0.0, v_max_ms=30.0, n_points=20 (le=500 in the service schema, le=200 in the endpoint schema)`

**Formula — as the code writes it.**

```
velocities = np.linspace(request.v_min_ms, request.v_max_ms, request.n_points)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/powertrain_performance.py:694` — `compute_performance_curve`

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:711`

**Source.** 🔴 NO SOURCE FOUND

>
> — via `rc-aircraft-designer`
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** Sweep bounds and resolution are presentation parameters. The le=500 / le=200 mismatch between the service and endpoint schemas is a defect, not a provenance question.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** n_points has two different upper bounds for the same parameter: le=500 at powertrain_performance.py:221 and le=200 at app/api/v2/endpoints/aeroplane/powertrain_performance.py:54.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
