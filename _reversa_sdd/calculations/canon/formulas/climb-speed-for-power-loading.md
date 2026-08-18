---
canon: climb-speed-for-power-loading
entry: formula
kind: procedure
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
  - kind/procedure
---

# Climb speed assumed by the power-loading constraint

**Canonical form**

```
V_climb = max(1.3 * V_S,target, 1 m/s)
```

**Produces** [[climb-speed]]  ·  **from** [[stall-speed-target]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Approval asks two different questions: **under which assumptions does it hold**, and **when does it converge** — including what it returns when it does not.

### Assumptions and convergence

> A procedure exists because no closed solution does. What replaces the source is the
> statement of **what must hold for it to be valid** and **when it terminates**. Both
> are required before approval.

**Assumptions.** 🔴 not yet stated — required for approval.

**Convergence.** 🔴 not yet stated — required for approval.

**On failure.** 🔴 not yet stated — what is returned when it does not converge, and is it declared? (ADR 0020)

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

- [ ] **Assumptions** — the conditions under which the procedure is valid are stated
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

