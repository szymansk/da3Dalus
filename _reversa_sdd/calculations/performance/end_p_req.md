---
name: end_p_req
symbol: P_req(V)
kind: quantity
unit: W
cluster: perf-envelope
user_visible: true
source_status: SOURCED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/sourced
  - surface/user-visible
  - flag/anomaly
  - flag/divergence
---

# Battery power required

**Definition.** Electrical power drawn from the pack for level flight at speed V.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return p_aero / eta_total
```

**Inputs.**

- [[end_p_aero|Aerodynamic power]]
- [[end_eta_total|Total propulsion efficiency]]

**Produced by.** `app/services/endurance_service.py:127` — `_power_required`

**Consumed by.**

- in this graph: `Power required at V_md` · `Power required at V_min_sink`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `powertrain_sizing_service.py`

**Source.** 🟢 SOURCED

> Energy chain P_elec = P_prop/(eta_mot*eta_prop), Roxxy Motoren-Fibel Ch. 2 pp. 21-22; propulsive-efficiency definition Sadraey §8.8.1 Eq. 8.15.
>
> — via `rc, scholz`

**The source states it as.**

```
P_batt = D*V/eta_total
```

**⚠️ Divergence from the source.** Physics correct. Structural note: a private helper is imported across a module boundary by powertrain_sizing_service.py:37. The reuse is deliberate and correct (one authority for power-required physics, ADR 0022) — the underscore is what should change, not the call site.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** A private helper (`_power_required`) is imported across module boundaries by powertrain_sizing_service.py:37 — the underscore contract is broken but the reuse is deliberate ('power-required physics are now delegated to endurance_service._power_required').

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
