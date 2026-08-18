---
name: alr-n-crit
symbol: N_crit
kind: parameter
unit: dimensionless
cluster: aero-polars
user_visible: false
source_status: SOURCED
---

# Transition criterion n_crit

**Definition.** e^N transition amplification factor passed to NeuralFoil.

**Value.** `9.0`

**Formula — as the code writes it.**

```
n_crit: float = 9.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/airfoil_low_re_service.py:414` — `compute_airfoil_low_re`

**Consumed by.**

- outside it: `get_aero_from_neuralfoil:473` · `AirfoilLowRePolarModel.n_crit` · `settings.low_re_n_crit (app/settings.py:96)`

**Source.** 🟢 SOURCED

> Drela, XFOIL 6.99 User Primer, transition-criterion (Ncrit) table: dirty tunnel 4–8, average wind tunnel 9 (XFOIL default), clean tunnel 10–12, motorglider 11–13, sailplane 12–14. In range for the surrogate: Sharpe (2024) §7.2.5 trained N_crit ~ U[0,18]
>
> — via `aerosandbox-expert, aerodynamics-expert`

**The source states it as.**

```
N_crit = 9 ('average wind tunnel', XFOIL default)
```

**⚠️ Divergence from the source.** Value matches the source's default exactly. But the same table puts free-flight sailplanes/motorgliders at 11–14, i.e. the app models every RC/UAV airfoil in dirtier air than a slope soarer actually flies in — earlier transition, less laminar run, pessimistic cd and CL_max. The code cites nothing and exposes no way to change it per mission.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** N_crit = 9 is a wind-tunnel turbulence calibration, never validated at 0.5–15 kg RC/UAV scale (ADR 0023). The anomaly note in the inventory has the direction backwards: 9 already assumes *more* turbulence than clean-air model flight, not less.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** n_crit=9 is the standard wind-tunnel/free-air value; no RC/UAV-scale validation is cited (ADR 0023) — RC models often fly in higher-turbulence air.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `n_crit : float
    Transition criterion (e^N method).`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
