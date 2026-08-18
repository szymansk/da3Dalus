---
name: delta-x-clipped
symbol: Δx_clip
kind: quantity
unit: m
cluster: stability
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Clipped wing shift

**Definition.** Wing shift re-solved so the resulting forward-CG static margin exactly equals the clip limit.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
delta_x = (_SM_FORWARD_CLIP_LIMIT * mac_m + cg_fwd_m - x_np_m) / (1.0 - a_vh)
```

**Inputs.**

- [[sm-forward-clip-limit|Forward-CG SM clip limit]]  — *⊣ limit*
- [[mac-m-fallback|MAC fallback]]  — *⤵ fallback*
- [[alpha-vh|Tail efficiency factor]]

**Produced by.** `app/services/sm_sizing_service.py:431` — `suggest_corrections`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:446 (_wing_shift_option)`

**Source.** 🟡 PARTIAL

> The algebra is a correct inversion of the code's own x_np-after-shift model; it inherits whatever provenance that model has (see x-np-after-shift). The clip *target* value 0.30 has none (see sm-forward-clip-limit).
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
—
```

**⚠️ Divergence from the source.** The clip re-solves only the wing-shift lever. The horizontal-tail option returned in the same response (delta_sh_m2 / delta_pct) is not re-solved, so the two options presented side by side predict different resulting static margins. Sadraey §12.5.5 treats the equivalent situation as a convergence branch that returns upstream, not as an independent per-lever clip.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The clip fires but delta_sh_m2 / delta_pct (the htail option shown alongside) are NOT re-solved — the two options returned in the same response then predict different static margins.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Clip: solve for delta_x such that sm_at_fwd == _SM_FORWARD_CLIP_LIMIT
# (x_NP + Δx·(1-α_VH) - cg_fwd) / MAC = clip_limit
# Δx·(1-α_VH) = clip_limit·MAC + cg_fwd - x_NP`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
