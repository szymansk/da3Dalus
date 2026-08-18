---
name: cg-classification-overall
symbol: classification
kind: quantity
unit: enum (dimensionless)
cluster: mass
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/mass
  - class/derived
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Overall CG-envelope classification

**Definition.** Worst of the forward and aft SM classifications, using an explicit severity rank.

**Derived quantity.** Computed from the inputs below.

**Value.** `{"error": 3, "warn": 2, "ok": 1, "unknown": 0}`

**Formula — as the code writes it.**

```
_rank = {"error": 3, "warn": 2, "ok": 1, "unknown": 0}; if _rank[classification_fwd] >= _rank[classification_aft]: overall = classification_fwd else: overall = classification_aft
```

**Inputs.**

- [[sm-classification|Static-margin classification]]

**Produced by.** `app/services/loading_scenario_service.py:604` — `get_cg_envelope`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/services/loading_scenario_service.py:629 (CgEnvelopeRead.classification)` · `frontend/components/workbench/LoadingScenariosCard.tsx:85-87`

**Source.** 🟡 PARTIAL

> Sadraey, M.H., Wiley 2013, §11.3.2 — envelope containment is all-or-nothing: "Any point outside the polygon is forbidden", and the pre-flight check requires that BOTH the weight limit and the cg position be verified. That supports 'worst case governs'; the specific rank map has no source.
>
> — via `aircraft-design-scholz`

**⚠️ Divergence from the source.** Sadraey's containment logic requires both limits to be VERIFIED before a loading is accepted; an unverifiable limit is not a pass. The code ranks "unknown" lowest (0), so an unknown forward classification is masked by any known aft classification and the aircraft is reported ok/warn on the strength of half an envelope. Under §11.3.2 the correct behaviour is the opposite — unknown should dominate, or at minimum not be silently outranked by 'ok'.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** "unknown" ranks LOWEST (0), so an unknown forward SM is masked by any known aft classification. Additionally the frontend type CgClassification = "error" \| "warn" \| "ok" (frontend/hooks/useLoadingScenarios.ts:83) omits "unknown", which the backend can return (app/schemas/loading_scenario.py:31).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `"# Hierarchy: error > warn > ok > unknown" — app/services/loading_scenario_service.py:603`

---
*Cluster [[_index-mass|mass]] · generated from the 2026-08-18 extraction.*
