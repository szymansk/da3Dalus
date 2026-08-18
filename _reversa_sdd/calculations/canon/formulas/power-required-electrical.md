---
canon: power-required-electrical
entry: formula
kind: law
shape: law
status: draft
output: power-required
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
---

# Electrical power required for level flight

**Canonical form**

```
P_req(V) = 0.5 * rho * V^3 * S_ref * (C_D0 + k * C_L^2) / eta_total,  with C_L = 2 m g / (rho V^2 S_ref)
```

**Produces** [[power-required]]  ·  **from** [[air-density]] · [[flight-speed]] · [[wing-reference-area]] · [[zero-lift-drag-coefficient]] · [[induced-drag-factor]] · [[aircraft-mass]] · [[gravity]] · [[propulsive-efficiency]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟢 SOURCED

> Sadraey, Aircraft Design, §4.3.3.2, Eq. 4.50 and 4.55: eta_P*P_max = T*V_max with T = D, then substituting D = 0.5*rho*V^2*S*(C_Do + K*C_L^2) and C_L = 2W/(rho*V^2*S) - which is precisely the proposal's expression. Propeller efficiency values: Sadraey §4.3.3.2 gives eta_P = 0.7-0.85 at cruise; §4.3.5.2 gives 0.5-0.6 for fixed-pitch and ~0.7 for variable-pitch/constant-speed in climb.

**The source writes it as**

```
Sadraey's eta is eta_P, the PROPELLER efficiency alone, converting shaft power to thrust power. The proposal's eta_total is a battery-to-thrust chain efficiency, which is a different and larger composition.
```

**Validity at 0.5–15 kg.** The aerodynamics are exact; the weak link is eta_total, and it is weak specifically at RC scale. Sadraey's eta_P covers only the propeller. A battery-to-thrust chain must also fold in ESC losses, motor efficiency and pack internal resistance - and motor efficiency is strongly current-dependent, not constant: Drela's 3-parameter motor model (motor theory §1.2) gives eta_m = P_shaft/(V*I) = [1/(1 + i*R*K_V/Omega)]*(K_V/K_Q), which falls at both low current (no-load losses dominate) and high current (i^2*R dominates). Since this formula is evaluated across a speed sweep, eta_total varies along the very axis being swept. Treating it as a scalar is the dominant error source in P_req at 0.5-15 kg, larger than any aerodynamic term here.

## Implementations (3)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[end_p_req]] | EXACT | 🟢 |  |
| [[end_p_req_vmd]] | SPECIALISED | 🟢 | Evaluated at V = V_md with the Reynolds-interpolated C_D0 and e at that speed. |
| [[end_p_req_vmin]] | SPECIALISED | 🟢 | Evaluated at V = V_min_sink with the Reynolds-interpolated C_D0 and e at that speed. |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

