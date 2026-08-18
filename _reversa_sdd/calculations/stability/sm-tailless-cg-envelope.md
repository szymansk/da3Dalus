---
name: sm-tailless-cg-envelope
symbol: —
kind: quantity
unit: m
cluster: stability
user_visible: false
source_status: SOURCED
node_class: derived
tags:
  - cluster/stability
  - class/derived
  - source/sourced
  - flag/anomaly
---

# Tailless absolute CG envelope width

**Definition.** Absolute travel available between the tailless forward and aft CG limits, used only to raise a narrow-envelope warning.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
envelope_m = (_SM_TAILLESS_FWD_CG - _SM_TAILLESS_AFT_CG) * mac_m
```

**Inputs.**

- [[sm-tailless-fwd-cg|Tailless forward CG limit (SM)]]  — *⊣ limit*
- [[sm-tailless-aft-cg|Tailless aft CG limit (SM)]]  — *⊣ limit*

**Produced by.** `app/services/sm_sizing_service.py:232` — `_tailless_recommendation`

**Consumed by.**

- outside it: `app/services/sm_sizing_service.py:233 (log-only comparison)`

**Source.** 🟢 SOURCED

> Lennon, "Basics of R/C Model Aircraft Design" (1996) Ch. 23 — the tailless CG envelope is bounded by SM 10 % (forward) and 5 % (aft); Lennon explicitly warns that "Conventional tailed aircraft can tolerate CG shifts of several percent MAC; tailless aircraft cannot," which is exactly why the absolute width matters.
>
> — via `rc-aircraft-designer`

**The source states it as.**

```
envelope = (SM_fwd − SM_aft) · MAC = (0.10 − 0.05)·MAC (Lennon Ch. 23)
```

**⚠️ Anomaly.** Result only reaches a logger.warning — the narrow-envelope condition is never returned to the API caller, so the user is never told (ADR 0020: an undeclared caveat).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `# Narrow-envelope guard (spec gh-579): warn when computed absolute CG envelope
# (0.10 − 0.05) × MAC < 5 mm — physically unusable on tiny RC planks.`

---
*Cluster [[_index-stability|stability]] · generated from the 2026-08-18 extraction.*
