---
canon: air-density-isa
entry: formula
kind: procedure
shape: law
status: draft
output: air-density
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
---

# ISA air density at altitude

**Canonical form**

```
rho = rho_ISA(h)   [U.S. 1976 COESA standard atmosphere]
```

**Produces** [[air-density]]  ·  **from** [[altitude]]

**Kind: a procedure.** There is no closed form, so an algorithm stands in its place. Source and scale are asked as of any entry — a procedure is not source-free: it either implements a published standard or solves a stated equation. **On top of that** it must say **under which assumptions it holds** and **when it converges**, including what it returns when it does not.

### The procedure

> A procedure is not invented here. It has **two origins**, and both are citable:
> the **relation** it solves, and the **method** it solves it with. Its assumptions and
> its convergence behaviour are then properties of that method — published, not chosen.

**Relation solved.** 🔴 not yet stated — which equation or standard does this implement?

**Method.** 🔴 not yet named — bisection, Brent, Newton, Picard, an interior-point solver, a tabulated standard?

**Assumptions.** 🔴 not yet stated — bracketing, continuity, monotonicity, validity range. These follow from the method; they are not a matter of taste.

**Convergence.** 🔴 not yet stated — tolerance, iteration cap, and the guarantee the method actually offers.

**On failure.** 🔴 not yet stated — what is returned when it does not converge, and is it declared? (ADR 0020)

**Dimensional check.** ⚪ procedural — not an algebraic law

**Source.** 🟢 SOURCED

> NOAA/NASA/USAF, "U.S. Standard Atmosphere, 1976", NOAA-S/T 76-1562 (the COESA model). Below 32 km identical to the ICAO ISA. Scholz, Flugzeugentwurf, 05_PreliminarySizing §5.6.2 states the troposphere layer used: T(h) = 288.15 - 0.0065*h[m] for 0<=h<=11 km, T = 216.65 K for 11-20 km, pressure from the hydrostatic equation.

**The source writes it as**

```
Scholz does not write rho(h) directly; he writes T(h) and derives p(h), then uses q/M^2 = (gamma/2)*p(h). Sea-level anchors: T0 = 288.15 K, p0 = 101325 Pa, rho0 = 1.225 kg/m^3.
```

**Validity at 0.5–15 kg.** Model is exact and the chain defaults to h=0, so it degenerates to the 1.225 literal. The real RC limitation is not altitude but that RC flies in the surface layer where the day's density deviates from ISA: 15 C vs 30 C at sea level is ~5% in rho, i.e. ~2.5% on every speed in the chain. ISA-at-0m is a nominal reference, not the field condition, and should be labelled as such (ADR 0020: substituting ISA for measured conditions is an undeclared substitution).

## Implementations (2)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[air_density_rho]] | EXACT | 🟢 |  |
| [[rho-speed-polar]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Relation and method** — which equation it solves, and by which named method
- [ ] **Assumptions** — the conditions the method requires (bracketing, continuity, range)
- [ ] **Convergence** — the criterion, and what is returned and declared on failure
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

