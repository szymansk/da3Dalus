---
name: end_t_endurance_max
symbol: t_endurance,max
kind: quantity
unit: s
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/perf-envelope
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Maximum endurance

**Definition.** Flight time on a full pack flown at minimum-power speed.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
t_endurance_max_s = (capacity_wh_val * 3600.0) / p_req_vmin
```

**Inputs.**

- [[end_capacity_wh|Battery capacity]]
- [[end_seconds_per_hour|Wh-to-Ws conversion]]  — *× unit*
- [[end_p_req_vmin|Power required at V_min_sink]]  — *⊣ limit*

**Produced by.** `app/services/endurance_service.py:403` — `compute_endurance`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `EnduranceCard.tsx` · `metricsAdapters.toPowertrainItems` · `GET /aeroplanes/{id}/endurance`

**Source.** 🟡 PARTIAL

> Traub, L.W., 'Range and Endurance Estimates for Battery-Powered Aircraft', Journal of Aircraft, Vol. 48, No. 2 (March-April 2011), pp. 703-707 — real, specific, correctly named in the module header (add volume/issue/pages in code). Flying at minimum power for maximum endurance: Sadraey §4.2.5.4.
>
> — via `scholz, rc`

**The source states it as.**

```
t = E_batt[Wh] * 3600 / P_req(V_min_power)
```

**⚠️ Divergence from the source.** The code DEPARTS from its own cited source in a way the citation conceals. Traub 2011 derives battery endurance with an explicit Peukert correction and a usable-capacity treatment; the code drops both and discharges 100% of nameplate Wh. Assumption 3 declares the Peukert omission ('valid for C-rates < 2C') but nothing declares the depth-of-discharge omission.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** No RC source for usable DoD was found in the vaults, so the correct derate is NOT established here — but discharging a LiPo to 100% nameplate is not RC practice under any convention, so the reported endurance is optimistic by construction and the response says nothing. Treat the derate as an open question for the maintainer, not as a known 80% figure.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** No usable-capacity or reserve derating: 100 % of nameplate Wh is discharged. For LiPo the practical floor is ~80 % DoD, so the reported endurance is optimistic by construction and nothing in the response says so.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"t_endurance(V) = E_battery [Wh] × 3600 [s/h] / P_req(V) [W]"; "2. Constant m_TO over discharge"; "3. Peukert effect neglected (valid for moderate C-rates < 2C)"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
