---
name: section-modulus-rod
symbol: W
kind: quantity
unit: mm³
cluster: structure
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: derived
tags:
  - cluster/structure
  - class/derived
  - source/partial
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Section modulus, solid round rod

**Definition.** Elastic section modulus of a solid round rod of diameter d. This d³/10 form is the convention the whole spar cluster uses in place of the exact π·d³/32.

**Derived quantity.** Computed from the inputs below.

**Formula — as the code writes it.**

```
return d**3 / 10.0
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:62` — `section_modulus_rod`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- outside it: `app/tests/test_spar_sizing_service.py:48`

**Source.** 🟡 PARTIAL

> Kirch, "Hauptholm", Flugmodellbau Kirch, https://www.flugmodellbau-kirch.de/Hauptholm.htm — round-rod (Rundstahl) section-modulus LOOKUP TABLE
>
> — via `direct verification of the kirch source named in the code; rc-aircraft-designer vault searched and contains NO section-modulus/Widerstandsmoment formula anywhere`

**The source states it as.**

```
The source gives NO formula for a round rod. It gives a table of values: d=3.0 mm → W=2.7 mm³; d=4.0 → 6.7; d=5.0 → 12.5; d=6.0 → 21.6. Arithmetic check: d³/10 gives 2.70, 6.40, 12.50, 21.60 — three of the four tabulated values match d³/10 EXACTLY. The exact solid-circular π·d³/32 gives 2.65, 6.28, 12.27, 21.21 — none match. So the source's own tabulated rod values were computed as d³/10 (the d=4.0 entry, 6.7 vs 6.4, is the single outlier and reads as a transcription artefact).
```

**⚠️ Divergence from the source.** The code writes the closed form W = d³/10; the source states only tabulated values consistent with it. The convention is therefore traceable to the cited RC source, but the ~1.9% overstatement vs the exact π·d³/32 = 0.09817·d³ is NOT justified anywhere in the source — it is an unexplained rounding the source inherited and the code adopted. This matters directionally: as a REQUIREMENT (spar_solver.py:521, spar_plan_service.py:218) it is conservative; as a SUPPLY (spar_plan_service.py:74, the W a real rod PROVIDES) it credits stock with 1.9% more bending capacity than it physically has. The source uses it only in the supply direction (a table of what rods provide), so the code's requirement-side use is an extension beyond the source.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** No production consumer — only the unit test; yet the SAME formula is re-implemented twice more (spar_solver.py:521, spar_plan_service.py:218) and a third time inside spar_plan_service._w_stock:74. Also: d³/10 = 0.1·d³ vs exact π·d³/32 = 0.0982·d³ — a ~1.9 % deviation with no cited justification for the rounding.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `Reference: kirch Hauptholm (https://www.flugmodellbau-kirch.de/Hauptholm.htm) and the user's section-modulus scan.`

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
