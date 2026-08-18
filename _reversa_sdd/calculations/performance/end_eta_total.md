---
name: end_eta_total
symbol: eta_total
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: PARTIAL
---

# Total propulsion efficiency

**Definition.** Product of propeller, motor and ESC efficiencies, constant over speed.

**Formula — as the code writes it.**

```
eta_total: float = eta_prop * eta_motor * eta_esc
```

**Inputs.** [[end_eta_prop|Default propeller efficiency]] · [[end_eta_motor|Default motor efficiency]] · [[end_eta_esc|Default ESC efficiency]]

**Produced by.** `app/services/endurance_service.py:276` — `compute_endurance`

**Consumed by.**

- in this graph: [[end_p_req|Battery power required]]

**Source.** 🟡 PARTIAL

> Chain structure SOURCED (Sadraey §8.8.1 Eq. 8.15; Roxxy Ch. 2 pp. 21-22, which chains motor and propeller). The third ESC factor is a correct drivetrain element but appears in neither cited source.
>
> — via `rc`

**The source states it as.**

```
eta_total = eta_prop * eta_motor * eta_esc
```

**⚠️ Scale (ADR 0023).** Compounding effect: each factor sits at the optimistic end of its band (0.65 top of Deters' small-UAV range, 0.85 top of Roxxy's BLDC range, 0.94 unsourced). Product 0.519 vs a mid-band product of roughly 0.60*0.80*0.92 = 0.44 — an ~18% optimism in eta_total, which passes straight through to endurance and range as an ~18% overestimate before any other assumption is considered. Assumption 1 ('constant eta over speed range, no J-dependent eta_prop') is correctly declared as Class-I.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**Cited in the code itself.** `"1. Constant η over speed range (no J-dependent η_prop) — Class-I"`

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
