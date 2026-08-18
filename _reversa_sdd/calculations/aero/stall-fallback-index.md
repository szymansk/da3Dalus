---
name: stall-fallback-index
kind: constant
unit: index
cluster: aero-spanwise
user_visible: true
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/no-source-found
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
---

# Stall fallback index

**Definition.** When no CL-drop/CD-rise pair is found after CLmax, stall is declared at the very next alpha station.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `i_clmax + 1`

**Formula — as the code writes it.**

```
i_stall = min(i_clmax + 1, n - 1)
```

**Inputs.**

- [[max-cl-point|Maximum lift coefficient point]]  — *⊣ limit*

**Produced by.** `app/services/analysis_service.py:177` — `_find_stall_point`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🔴 NO SOURCE FOUND

> No source declares stall one grid step past CL_max. Anderson §4.x defines stall by separation, not by grid index. Fabricated value surfaced to the user as 'Stall-Indiz' with no warning (ADR 0020).
> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Anomaly.** Fabricates a stall point one grid step past CLmax with no warning — an undeclared substitution (ADR 0020) presented to the user as 'Stall-Indiz'.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
