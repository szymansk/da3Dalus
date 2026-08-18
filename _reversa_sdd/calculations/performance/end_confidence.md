---
name: end_confidence
symbol: confidence
kind: quantity
unit: -
cluster: perf-envelope
user_visible: true
source_status: SOURCED
---

# Endurance confidence

**Definition.** 'estimated' when the polar fit fell back or its quality is poor/unknown, else 'computed'.

**Formula — as the code writes it.**

```
is_estimated = e_oswald_fallback_used or e_oswald_quality in ("poor", "unknown"); confidence = "estimated" if is_estimated else "computed"
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/endurance_service.py:291` — `compute_endurance`

**Consumed by.**

- outside it: `EnduranceCard.tsx` · `metricsAdapters.toPowertrainItems`

**Source.** 🟢 SOURCED

> Internal confidence policy — no external source applies.
>
> — via `aero`

**The source states it as.**

```
estimated when fallback used or quality in (poor, unknown)
```

**⚠️ Divergence from the source.** Real defect: the warning text at end:296 hardcodes 'Endurance derived from fallback e=0.8' but also fires when e_oswald_raw is a genuine fitted value and only the quality string is 'poor'/'unknown'. The user is told a number was used that was not used — worse than a vague warning, because it is checkably false.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** The warning text at line 296 hardcodes 'Endurance derived from fallback e=0.8' but is also emitted when e_oswald_raw is a real fitted value and only the quality string is 'poor'/'unknown'. The user is told a number was used that was not used.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-perf-envelope|perf-envelope]] · generated from the 2026-08-18 extraction.*
