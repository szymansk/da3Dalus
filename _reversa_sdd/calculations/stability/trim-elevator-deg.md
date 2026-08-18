---
name: trim-elevator-deg
symbol: delta_e_trim
kind: quantity
unit: deg
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

# Trim elevator deflection (from result)

**Definition.** Elevator deflection at the analysed operating point; first control surface whose name contains 'elevator'.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
for name, defl in control_surfaces.deflections.items():
    if "elevator" in name.lower():
        return _scalar(defl)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/stability_service.py:55` — `_find_trim_elevator`

**Consumed by.**

- outside it: `app/services/stability_service.py:341` · `app/services/stability_service.py:174 (trim_elevator_deg column)`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §12.5.4, Eq. 12.90 — the elevator deflection required for longitudinal trim, δ_E = −[(T·z_T/(qSC̄) + C_mo)C_Lα + (C_L1 − C_Lo)C_mα] / [C_Lα·C_mδE − C_mα·C_LδE]; §12.5.4 also defines the trim curve δ_E vs speed.
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
δ_E = −[(T·z_T/(qSC̄) + C_mo)·C_Lα + (C_L1 − C_Lo)·C_mα] / [C_Lα·C_mδE − C_mα·C_LδE]  (Eq. 12.90)
```

**⚠️ Divergence from the source.** The literature quantity is the *solution* of a trim equation. The code performs no trim solve — it substring-matches 'elevator' in the solver's deflection dict (app/services/stability_service.py:57-61) and echoes back whatever deflection was requested. Sadraey's roles for pitch control also include the all-moving stabilator (§12.5.5 step 12), which the substring match misses.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Substring match on 'elevator' silently ignores the other pitch roles the codebase recognises (ruddervator, elevon, stabilator, flaperon) — a V-tail or flying wing always reports None.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
