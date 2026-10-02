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

**Source.** 🟢 Definition of the load factor (`n = L/W`).
