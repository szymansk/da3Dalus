---
name: sm-tailless-aft-cg
symbol: SM_aft,tailless
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
---

# Tailless aft CG limit (SM)

**Definition.** Aft CG limit for tailless aircraft expressed as static margin — CG approaching NP.

**Value.** `0.05`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:60` — `_SM_TAILLESS_AFT_CG`

**Consumed by.**

- in this graph: [[sm-tailless-cg-envelope|Tailless absolute CG envelope width]]
- outside it: `app/services/sm_sizing_service.py:232,247` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:97`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23: "aft CG limit so SM ≈ 5% MAC."
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
aft CG limit at SM = 5 % MAC (Lennon Ch. 23)
```

**Cited in the code itself.** `# aft CG limit @ SM = 5% MAC (CG approaching NP)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
