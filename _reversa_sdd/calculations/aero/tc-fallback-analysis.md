---
name: tc-fallback-analysis
symbol: t/c
kind: constant
unit: -
cluster: aero-spanwise
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-spanwise
  - class/unclassified-constant
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# t/c fallback constant (analysis_service copy)

**Definition.** Thickness-to-chord ratio nominally used when section airfoil data is unavailable.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.12`

**Formula — as the code writes it.**

```
_TC_FALLBACK = 0.12
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/analysis_service.py:2101` — `_TC_FALLBACK`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> Anderson 6e §4.x Airfoil Stall (leading-edge stall 'characteristic of relatively thin airfoils, thickness 10–16% of chord'); Scholz 07_WingDesign §7.1 ((t/c)_section = (t/c)_airfoil is scale-invariant)
>
> — via `aerodynamics-expert, aircraft-design-scholz`

**The source states it as.**

```
t/c is the thickness-to-chord ratio; 10–16% is the conventional band for thin/medium sections
```

**⚠️ Divergence from the source.** 12% sits inside the conventional band but no source prescribes 0.12 as a DEFAULT. Additionally this constant is dead code — no reader inside analysis_service.py (ADR 0021); the live copy is app/services/spar_sizing.py:32.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Dead constant — grep finds no reader inside analysis_service.py; the live one is app/services/spar_sizing.py:32 (ADR 0021: complete but unreachable code must be deleted).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-aero-spanwise|aero-spanwise]] · generated from the 2026-08-18 extraction.*
