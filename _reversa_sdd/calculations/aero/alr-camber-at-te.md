---
name: alr-camber-at-te
symbol: y_c(0.9)
kind: quantity
unit: chord fraction
cluster: aero-polars
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# camber_at_te (camber at x=0.9)

**Definition.** Mean-camber-line value at 90% chord, used as the primary reflex signal.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
camber_at_te = float(np.interp(0.9, x_eval, camber))  # camber at x = 0.9
```

**Inputs.**

- [[alr-camber-line|Mean camber line]]

**Produced by.** `app/services/airfoil_low_re_service.py:221` — `classify_family`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aft camber ratio (reflex Signal A)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `classify_family:226` · `AirfoilGeometryModel.camber_at_te (app/models/airfoil_low_re.py:55) via scripts/backfill_airfoil_low_re.py:247`

**Source.** 🟡 PARTIAL

> Lennon (1996), Ch. 2 — reflex is the upward turn of the mean line near the trailing edge
>
> — via `rc-aircraft-designer`

**⚠️ Divergence from the source.** The signal is sourced conceptually; the x = 0.9 evaluation station is arbitrary. Name and documentation contradict the value: the column is camber_at_te and app/models/airfoil_low_re.py:54 still says 'at the trailing edge (x≈1)'. Also computed twice (service and backfill script).

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Name contradicts definition: the column is `camber_at_te` and app/models/airfoil_low_re.py:54 still documents it as 'Camber-line value at the trailing edge (x≈1). Positive → reflexed TE' while the value is at x=0.9; also computed twice (here and in scripts/backfill_airfoil_low_re.py:247).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `camber_at_te = float(np.interp(0.9, x_eval, camber))  # camber at x = 0.9`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
