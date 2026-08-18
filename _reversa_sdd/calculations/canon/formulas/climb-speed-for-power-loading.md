---
canon: climb-speed-for-power-loading
entry: formula
kind: law
shape: approximation
status: draft
output: climb-speed
source_status: PARTIAL
dimensional_check: UNPARSEABLE
tags:
  - canon/formula
  - source/partial
  - dim/unparseable
  - shape/approximation
  - kind/law
  - status/draft
---

# Climb speed assumed by the power-loading constraint

**Canonical form**

```
V_climb = max(1.3 * V_S,target, 1 m/s)
```

**Produces** [[climb-speed]]  ·  **from** [[stall-speed-target]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

ℹ️ **Reclassified** from `procedure` by the trial of 2026-08-18. One line of scalar arithmetic with a clamp: `v_climb = max(1.3 * max(v_stall, 1.0), 1.0)` (app/services/matching_chart_service.py:563), consumed by the closed form `p_over_m * eta_prop / (g * v_climb)` (line 564). A coefficient times an input, clamped — a law, not a procedure.

> 🔴 **An assumption of this entry is broken in the code.**
>
> Two:
> (1) app/services/matching_chart_service.py:1133 and 1135 pass `v_stall=v_s`, and `v_s` is resolved at line 781 as `v_s_target if v_s_target is not None else defaults['v_s_target']` — the mission's maximum ACCEPTABLE stall speed (e.g. 7.0 m/s for trainer, 12.0 for sport, 27.7 for GA; lines 209-236), never the aircraft's computed stall speed. Consequence: the power-loading floor is drawn for the requirement, not for the design. Two aircraft on the same mission get the identical T/W floor however different their actual stall speeds are, and an aircraft that misses its stall target gets a floor corresponding to a speed it cannot fly. Because the floor is a constant T/W independent of W/S, the error displaces the whole design point vertically.
> (2) app/services/matching_chart_service.py:563 — the inner `max(v_stall, 1.0)` silently replaces any stall speed below 1 m/s with 1 m/s, raising T/W by the ratio 1.0/v_stall with no DesignWarning (ADR 0020). The outer `max(..., 1.0)` is unreachable: 1.3 * (something >= 1.0) is always >= 1.3 > 1.0 — inert code, ADR 0021.

**Evaluated by.** None — scalar evaluation. The result is emitted as a horizontal line, the same T/W repeated across the whole W/S sweep (`[pl_tw] * len(ws_range)`, matching_chart_service.py:1141).

**Accuracy.** Not applicable — no iteration, no tolerance. The lookup is exact on its four keys and undefined off them; there is no interpolation between mission profiles.

**On failure.** Returns None when profile_key is None or the key is absent from the table (matching_chart_service.py:558-562); the constraint is then simply omitted from the chart with no warning. For a custom mode the caller silently substitutes the 'sport' band: `_power_loading_constraint('sport', v_stall=v_s)` (matching_chart_service.py:1135) — an undeclared substitution, ADR 0020. The hover text (line 1152) declares 'V_climb=1.3*V_s, eta_prop=0.7' but not that V_s is the target, not the clamp, and not the 'sport' fallback.

⚠️ **Shape: an approximation.** A rule of thumb standing where a law belongs. It may be the right thing to show, but it is never approved *as* the law for this quantity.

> A fixed multiple of the target stall speed, not a climb-performance result.

**Dimensional check.** ⚪ not machine-checkable as written

**Source.** 🟡 PARTIAL

> Sadraey, Aircraft Design, §4.3.5 Eq. 4.80 and §4.3.5.2 Eq. 4.85 - the source specifies the climb speed for the power/thrust-loading constraint EXPLICITLY, and it is not a multiple of V_S: for jets it is the minimum-drag speed sqrt(2(W/S)/(rho*sqrt(C_Do/K))); for prop-driven aircraft it is the minimum-POWER speed sqrt(2(W/S)/(rho*sqrt(3*C_Do/K))), which introduces the 1.155 = sqrt(4/3) factor in Eq. 4.89.

**The source writes it as**

```
Sadraey's form is the min-power speed for props. V_climb = 1.3*V_S,target has no source; the 1 m/s floor is a numerical guard with no physical basis in any authority.
```

**Validity at 0.5–15 kg.** For an electric RC model - propeller-driven by definition in this mass class - Sadraey's PROP rule applies, and the app already computes the minimum-sink/minimum-power speed elsewhere. Using 1.3*V_S here creates a second producer of the climb speed (ADR 0022) and departs from the one place the source is unusually explicit. Sadraey also fixes the density: ROC sizing always uses SEA-LEVEL rho because that is where power is highest. Recommend replacing with V_mp and keeping 1.3*V_S only as a fallback that emits a DesignWarning.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[v_climb_power_loading]] | DEVIATES | 🟢 | 1.3*V_S is a sourced coefficient, but as an approach speed (V_REF >= 1.3 V_S0) and as the  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

