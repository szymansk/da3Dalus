---
name: tc-fallback-ratio
symbol: t/c
kind: constant
unit: dimensionless
cluster: structure
user_visible: true
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/structure
  - class/unclassified-constant
  - source/partial
  - surface/user-visible
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
  - flag/scale
---

# Thickness-to-chord fallback ratio

**Definition.** Airfoil thickness-to-chord ratio substituted when no real airfoil/section thickness data is available for a station. Its use sets tc_fallback=True and emits a warning.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.12`

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/spar_sizing.py:32` — `_TC_FALLBACK`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `t/c fallback warning` · `Thickness-to-chord ratio at station`  
  *(these are backlinks — open the Backlinks pane to navigate them)*
- outside it: `app/services/spar_sizing.py:402` · `app/services/spar_sizing.py:403` · `app/services/spar_sizing.py:429`

**Source.** 🟡 PARTIAL

> Scholz, Flugzeugentwurf / Aircraft Design (HAW Hamburg lecture notes), 07_WingDesign §7.1 and §7.3 (relative thickness); Sadraey, Aircraft Design: A Systems Engineering Approach (Wiley 2013), §10.4.1 Example 10.1 (four-seat GA wing computed with (t/C)=0.12)
>
> — via `aircraft-design-scholz`

**The source states it as.**

```
Scholz §7.1/§7.3: t/c ranges from ~6% at the tip to 15% or more at the root; 12-15% at the root is the structurally motivated value. Sadraey Ex. 10.1 uses (t/C)=0.12 as the input for a GA wing.
```

**⚠️ Divergence from the source.** 0.12 sits inside the cited band and is used as a worked-example input by Sadraey, but NEITHER source states 0.12 as a fallback/default for an unknown airfoil. The value is defensible, the DEFAULTING is not attributable. Scholz's band is transport-category; Sadraey's 0.12 is a 1400 kg GA aircraft.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Scale (ADR 0023).** Both citations are transport/GA-category (Scholz is CS-25 Flugzeugentwurf; Sadraey Ex. 10.1 is a 1400 kg GA aircraft). No RC/UAV-scale (0.5-15 kg) validation of 0.12 as a fallback was found in the RC vault (rcplanedesigner wing__airfoils.md discusses t/c qualitatively and gives no default value). ADR 0023 finding.

> This application targets RC/UAV aircraft of **0.5–15 kg**. A constant is not
> justified by being standard in transport-category literature.

**⚠️ Anomaly.** Two producers of the same literal: app/services/spar_sizing.py:32 (used) and app/services/analysis_service.py:2101 (declared and never read — dead duplicate). Magic number: no source cited.

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

---
*Cluster [[_index-structure|structure]] · generated from the 2026-08-18 extraction.*
