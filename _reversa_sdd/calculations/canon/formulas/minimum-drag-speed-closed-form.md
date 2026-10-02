---
canon: minimum-drag-speed-closed-form
entry: formula
kind: law
shape: approximation
status: draft
output: minimum-drag-speed-probe
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/route
  - kind/law
  - status/draft
---

# Minimum-drag speed from the parabolic polar

**Canonical form**

```
V_md,probe = sqrt( 2*(W/S) / (rho * sqrt(C_D0 / k)) )
```

**Produces** [[minimum-drag-speed-probe]]  ·  **from** [[wing-loading]] · [[air-density]] · [[zero-lift-drag-coefficient]] · [[induced-drag-factor]]

**Probe, nicht Erzeuger.** Die Autorität ist [[minimum-drag-speed-from-polar]]. Diese Form setzt konstanten Nullauftriebswiderstand und konstanten Streckungsfaktor voraus — bei unseren Reynoldszahlen hängen beide von der Geschwindigkeit ab. Der Vergleich beider Wege ist ein Test (ADR 0022), keine zweite Wahrheit.

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Shape: a route.** This is one of several ways to the same quantity. The canon has chosen: the authority is [[minimum-drag-speed-from-polar]]; this closed form is its Probe — it requires that they **agree**.

**Test that follows.** Both routes claim the same quantity by different means; they must agree. Where they do not, the polar is not parabolic — which is a statement about the aircraft, not a defect.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design: A Systems Engineering Approach, §4.3.5, Eq. 4.80: V_ROCmax = V_Dmin = sqrt( (2*W/(rho*S)) / sqrt(C_Do/K) ). Cited by Sadraey to his own Aircraft Performance reference [5].

**The source writes it as**

```
Identical to the proposal once W/S is factored (Sadraey writes 2W/(rho*S) grouped, the proposal writes 2*(W/S)/rho). Sadraey introduces it as the speed for maximum rate of climb of a JET; the same quantity is the minimum-drag speed for any aircraft.
```

**Validity at 0.5–15 kg.** Valid at RC scale as an algebraic consequence of the parabolic polar, with the same caveat as max-lift-to-drag-parabolic: at Re 5e4-3e5 the polar is offset-parabolic, so C_D0 and k must be fitted over the C_L range of interest, not anchored at C_L = 0 (see zero-lift-drag-from-sweep). Do not let this closed form and the argmax-of-polar route both be authoritative - ADR 0022.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[v_md]] | EXACT | 🟢 |  |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

**Own output since 2026-10-02.** As the Probe it must not produce `V_md` itself: it did, and
with `C_D0` and `e` now bound to the cruise point (ADR 0004) that closed a loop
`V_md → V_cruise → e → k → V_md`. Its value is `V_md,probe`, compared with the
optimisation's `V_md`; a mismatch beyond the parabola's known error at low Reynolds number
is reported, not substituted.
