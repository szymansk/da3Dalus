---
canon: max-mass-structure
entry: formula
kind: law
tool: APP
shape: law
status: draft
output: max-mass-structure
source_status: SOURCED
dimensional_check: BALANCES
tags:
  - canon/formula
  - source/sourced
  - dim/balances
  - shape/law
  - kind/law
  - status/draft
tex: m_{max,struct} = n_{break,+}\,m
inputs: {n_break_pos: break-load-factor-positive, m: aircraft-mass}
outputs: {m_max_struct: max-mass-structure}
---

# Mass at which the spar no longer holds one g

**Canonical form**

```
m_max,struct = n_break,pos * m
```

**Produces** [[max-mass-structure]]  ·  **from** [[break-load-factor-positive]] · [[aircraft-mass]]

**Kind: a law.** The break load factor scales inversely with the mass, so the mass at which
the spar fails already at 1 g is `n_break,+ · m`. A physical limit, not a design load — anything
above 1 g (`n_lim`, class bands) is evaluation (A10).

**Source.** 🟢 Definition of the load factor (`n = L/W`); for models, Lennon, *Basics of R/C Model Aircraft Design*, Ch. 21 (load factor as the vector sum of weight and centripetal force).

**Validity in the RC/UAV regime (ADR 0028).** Regime-independent: `n = L/W` is a definition, and its inversion contains no flow physics; Lennon (Ch. 21) describes the load factor of models the same way, as the vector sum of weight and centripetal force in g. It inherits the linear-scaling approximation of [[spar-break-load-factor]]: at `n_break,+·m` the 1 g flight point lies at a different `C_L`, so on a twisted wing the spanload shape, and with it `n_break`, is not exactly mass-invariant [no source].

## Implementations (0)

None in aero_kernel yet; no register node is mapped to this entry.

## Approval

- [ ] **Source** — citation real, or absence stated and adopted on the maintainer's authority
- [ ] **Regime** — holds in the RC/UAV regime (Reynolds, Mach, equipment), or the limitation is written down (ADR 0028)
- [ ] **Dimensions** — the check balances
- [ ] **Implementations** — all agree, or each deviation is declared and justified
- [ ] **Preconditions** — every binding condition holds, or the violation is ticketed
- [ ] **Inputs approved** — no formula is approvable before its inputs are

> While `status: draft` this entry **cites nothing and decides nothing**.
