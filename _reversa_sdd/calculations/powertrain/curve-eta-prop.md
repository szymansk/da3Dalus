---
name: curve-eta-prop
symbol: eta_prop(J)
kind: quantity
unit: dimensionless (0..1)
cluster: powertrain
user_visible: true
source_status: SOURCED
---

# Propeller efficiency per velocity sample

**Definition.** Propulsive efficiency at each swept airspeed, clipped to [0,1], explicitly J-dependent rather than a flat scalar.

**Formula — as the code writes it.**

```
eta_prop = float(np.clip(Pe, 0.0, 1.0))
```

**Inputs.** [[polar-pe|Propeller efficiency from polar]]

**Produced by.** `app/services/powertrain_performance.py:760` — `compute_performance_curve`

**Consumed by.**

- outside it: `app/services/powertrain_performance.py:768` · `app/api/v2/endpoints/aeroplane/powertrain_performance.py:255`

**Source.** 🟢 SOURCED

> Deters, Ananda & Selig (2014), §II.D, Eq. 7: eta = J C_T / C_P — explicitly J-dependent, which is what the code implements per velocity sample.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
eta = J C_T / C_P
```

**⚠️ Anomaly.** The comment explicitly contrasts this with "the flat 0.65 scalar" — that flat scalar is still the operative value in both other powertrain services (endurance_service.py:53 DEFAULT_ETA_PROP used by sizing, and SolutionSpaceAssumptions.eta_prop_lo). Two competing authorities for propeller efficiency in the same cluster (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# η_prop from Pe (J-dependent — NOT the flat 0.65 scalar)`

---
*Cluster [[_index-powertrain|powertrain]] · generated from the 2026-08-18 extraction.*
