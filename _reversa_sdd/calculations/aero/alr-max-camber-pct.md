---
name: alr-max-camber-pct
symbol: f/c
kind: quantity
unit: % chord
cluster: aero-polars
user_visible: false
source_status: SOURCED
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/aero-polars
  - class/derived
  - source/sourced
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Max camber (classifier-internal)

**Definition.** Peak signed camber-line value expressed as percent of chord.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
max_camber = float(np.max(camber))
max_camber_pct = max_camber * 100.0
```

**Inputs.**

- [[alr-camber-line|Mean camber line]]

**Produced by.** `app/services/airfoil_low_re_service.py:214` — `classify_family`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Aft camber ratio (reflex Signal A)` · `Airfoil family label`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `classify_family:226,261,265,274,292`

**Source.** 🟢 SOURCED

> Abbott & von Doenhoff (1959), Ch. 6 / Anderson 6e §4.2 — NACA 4-digit first digit is maximum camber in percent chord

**The source states it as.**

```
f/c = max(y_c)/c ×100 [%]
```

**⚠️ Divergence from the source.** Two producers disagree: classify_family uses np.max(camber) (signed) while scripts/backfill_airfoil_low_re.py:241 persists np.max(np.abs(camber)). For a negative-camber (reflex-dominant) section the classifier and the stored column give different numbers — ADR 0022.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Second producer: scripts/backfill_airfoil_low_re.py:241 stores max_camber_pct as `float(np.max(np.abs(camber))) * 100.0` — the persisted value uses abs(), the classifier does not, so the two disagree for negative-camber sections (ADR 0022).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `max_camber = float(np.max(camber))
max_camber_pct = max_camber * 100.0  # as % of chord (coords normalized 0..1)`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
