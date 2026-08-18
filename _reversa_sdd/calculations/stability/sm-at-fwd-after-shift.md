---
name: sm-at-fwd-after-shift
symbol: SM_fwd,after
kind: quantity
unit: – (fraction of MAC)
cluster: stability
user_visible: false
source_status: SOURCED
---

# Forward-CG SM after wing shift

**Definition.** Static margin at the forward stability CG that would result from the proposed wing shift; used to trigger the forward clip.

**Formula — as the code writes it.**

```
sm_at_fwd_after_shift = (x_np_new - cg_fwd_m) / mac_m
```

**Inputs.** [[x-np-after-shift|Neutral point after wing shift]] · [[mac-m-fallback|MAC fallback]]

**Produced by.** `app/services/sm_sizing_service.py:426` — `suggest_corrections`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:427`

**Source.** 🟢 SOURCED

> Sadraey (Wiley 2013) §11.6.2 Eq. 11.18 evaluated at the forward cg; the requirement that both cg extremes be checked is Sadraey §11.6.3 and §12.5.5 step 16 ("Calculate the effectiveness derivatives … for both most aft and most forward cg").
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
SM = (x_np − x_cg)/C̄, evaluated at x_cg,fwd
```

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
