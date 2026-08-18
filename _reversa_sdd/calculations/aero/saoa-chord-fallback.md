---
name: saoa-chord-fallback
symbol: chord
kind: constant
unit: m
cluster: aero-strips
user_visible: false
source_status: NO_SOURCE_FOUND
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-strips
  - class/unclassified-constant
  - source/no-source-found
  - audit/confirmed
  - flag/anomaly
  - flag/divergence
---

# Chord fallback for Reynolds

**Definition.** Chord used when a cross-section's chord cannot be read.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `0.20`

**Formula — as the code writes it.**

```
chord = 0.20
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/section_aoa_service.py:160` — `_compute_alpha_l0_per_section`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- in this graph: `Local chord Reynolds number (alpha_L0 lookup)`  
  *(these are backlinks — open the Backlinks pane to navigate them)*

**Source.** 🔴 NO SOURCE FOUND

> No citable source was found. **This is recorded, not filled in.** The value is
> in the code without an attributable origin.

**⚠️ Divergence from the source.** 0.20 m is a plausible RC chord but unattributable. Combined with the 15 m/s fallback it silently fixes Re = 2e5, a value that then looks like a real measurement.

🟡 *Reported by the extraction pass, not independently verified.*

**⚠️ Anomaly.** Undeclared fallback with a magic RC-ish 0.20 m chord and no warning (ADR 0020).

🟡 *Reported by the extraction pass, not independently verified. Do not cite as a
defect until confirmed against the code.*

**Cited in the code itself.** `app/services/section_aoa_service.py:157-160`

---
*Cluster [[_index-aero-strips|aero-strips]] · generated from the 2026-08-18 extraction.*
