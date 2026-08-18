---
canon: endurance-from-battery
entry: formula
kind: law
shape: law
status: draft
output: endurance-time
source_status: PARTIAL
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/partial
  - dim/balances
  - shape/law
  - kind/law
---

# Flight time from pack energy and power draw

**Canonical form**

```
t = 3600 * E_bat / P_req
```

**Produces** [[endurance-time]]  ·  **from** [[battery-capacity]] · [[power-required]]

**Kind: a law.** A closed-form relation. Approval asks for its **source** and its **validity at 0.5–15 kg**.

**Dimensional check.** 🟢 balances

**Source.** 🟡 PARTIAL

> Dimensional identity (energy divided by power), with the 3600 converting Wh to J. No textbook derivation is needed or exists. The nearest domain source for the energy side is RC-Network Wiki, "Energiedichte" (Antriebstechnik), which tabulates LiPo at 0.55 MJ/kg against Li-Ion 0.36, NiMH 0.22, lead-acid 0.11 (and kerosene 40 for scale).

**The source writes it as**

```
No source writes this as a design equation; Scholz/Sadraey handle endurance through fuel fractions and the Breguet loiter equations, which do not transfer to a battery (mass does not decrease as energy is consumed - a genuine structural difference between the electric and fuel cases, and the reason Breguet is the wrong tool here).
```

**Validity at 0.5–15 kg.** Valid as an UPPER BOUND only, and the gap is large enough to matter at RC scale. Three effects all push the same way: (1) RC practice never discharges a LiPo to 100% - usable capacity is conventionally ~80%; (2) P_req is not constant over a real flight (climb, manoeuvre, headwind); (3) voltage sag and Peukert-type losses at the high C-rates typical of RC reduce delivered energy below nameplate. If E_bat is genuinely the USABLE pack energy as the skeleton's definition states, effect (1) is already handled and the remaining overstatement is perhaps 10-15%; if it is nameplate capacity, the overstatement is 25-35%. The distinction must be enforced at the input, not assumed.

## Implementations (1)

| node | claimed | verified | deviation |
|---|---|---|---|
| [[end_t_at_vmd]] | SPECIALISED | 🟢 | Evaluated at V_md (the range point) rather than at V_min_sink (the endurance point); the r |

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Scale** — holds at 0.5–15 kg, or the limitation is written down (ADR 0023)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.

