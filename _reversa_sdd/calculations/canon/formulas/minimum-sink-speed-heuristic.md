---
canon: minimum-sink-speed-heuristic
kind: formula
status: draft
output: minimum-sink-speed
source_status: NO_SOURCE_FOUND
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/no-source-found
  - dim/balances
  - flag/conflict
---

# Minimum-sink speed as a fixed multiple of the stall speed

**Canonical form**

```
V_mp = 1.2 * V_S
```

**Produces** [[minimum-sink-speed]]  ·  **from** [[stall-speed]]

**Dimensional check.** 🟢 balances

**Source.** 🔴 NO SOURCE FOUND

> No source for V_mp = 1.2*V_S in Scholz, Sadraey, Anderson, Lennon or the RC-Network Wiki. The sourced alternative is Sadraey Eq. 4.85 (closed form) or the ratio V_mp = V_md/1.316.

**The source writes it as**

```
n/a - no source form exists.
```

**Validity at 0.5–15 kg.** Unattributed. Additionally inconsistent with the companion heuristic (see minimum-drag-speed-heuristic): 1.4/1.2 = 1.167 where Sadraey requires V_md/V_mp = 1.316. Worse for RC than for transports because minimum-sink speed is a headline number for the glider/thermal end of the 0.5-15 kg range, where users will compare it against measured sink polars.

## ⚠️ Conflict

V_mp has two independent producers -- argmin of the computed sink rate, and this flat 1.2*V_S -- and the parabolic-polar result V_mp = V_md / 3^(1/4) (about 0.76 V_md) is used by neither, so the two speeds V_md and V_mp are not even constrained to the correct ratio to each other. A third, incompatible value for the same physical speed exists in operating_point_generator_service:434: for a propeller aircraft the best-rate-of-climb speed V_y IS the minimum-power speed, yet it is set there to max(1.50*V_S1, 0.95*V_cruise).

> Two or more implementations use **genuinely different laws** for this quantity.
> This is the entry that must be decided, not merely read.

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[kpi_min_sink_heuristic]] | EXACT | 🟢 |  |
| [[kpi_min_sink_speed]] | DEVIATES | 🟢 | Three-way selection across two different laws: an unreachable 'min_sink' marker branch, el |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

