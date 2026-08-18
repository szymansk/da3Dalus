---
name: sm-tailless-fwd-cg
symbol: SM_fwd,tailless
kind: constant
unit: – (fraction of MAC)
cluster: stability
user_visible: true
source_status: SOURCED
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/stability
  - class/unclassified-constant
  - source/sourced
  - surface/user-visible
  - audit/confirmed
---

# Tailless forward CG limit (SM)

**Definition.** Forward CG limit for tailless aircraft expressed as static margin — CG far ahead of NP.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.10`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/sm_sizing_service.py:59` — `_SM_TAILLESS_FWD_CG`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Tailless absolute CG envelope width`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/sm_sizing_service.py:232,246` · `app/api/v2/endpoints/aeroplane/sm_suggestions.py:96`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23: "set forward CG limit so SM ≈ 10% MAC and aft CG limit so SM ≈ 5% MAC."
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
forward CG limit at SM = 10 % MAC (Lennon Ch. 23)
```

**Cited in the code itself.** `# forward CG limit @ SM = 10% MAC (CG far ahead of NP)`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
