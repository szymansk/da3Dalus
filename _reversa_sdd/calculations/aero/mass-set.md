---
name: mass-set
kind: quantity
unit: kg
cluster: aero-spanwise
user_visible: true
source_status: SOURCED
---

# Speed-polar mass set

**Definition.** Ascending de-duplicated list of masses always containing the effective design mass.

**Formula — as the code writes it.**

```
masses: list[float] = [float(base_mass_kg)]; for m in masses_kg or []: mf = float(m); if mf > 0 and all(abs(mf - existing) > tol for existing in masses): masses.append(mf); masses.sort()
```

**Inputs.** [[base-mass-kg|Effective design mass]] · [[mass-dedup-tolerance|Mass de-duplication tolerance]]

**Produced by.** `app/services/analysis_service.py:471` — `_compute_speed_polar`

**Consumed by.**

- in this graph: [[weight-n|Weight]]
- outside it: `speed-polar-curves`

**Source.** 🟢 SOURCED

> RC-Network Wiki, 'Ballast (Fachbegriffe)', https://wiki.rc-network.de/wiki/Ballast
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
Aircraft weight does not change the SHAPE of the polar — it only shifts the airspeed at which each point is reached; the V/w ratio (and hence max glide ratio) is unaffected by weight.
```

**⚠️ Divergence from the source.** None. The source directly justifies plotting a family of mass curves off one CL/CD polar.

🟡 *Reported by the extraction pass, not independently verified.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
