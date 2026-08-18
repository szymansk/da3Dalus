---
name: prt-blasius-source
symbol: —
kind: constant
unit: n/a
cluster: aero-polars
user_visible: false
source_status: PARTIAL
code_audit: CONFIRMED
node_class: unclassified-constant
tags:
  - cluster/aero-polars
  - class/unclassified-constant
  - source/partial
  - audit/confirmed
  - flag/divergence
---

# Blasius / Schlichting cd0∝Re^(-1/2) scaling rationale

**Definition.** Cited justification for interpolating cd0 linearly in 1/√Re.

⚪ **Unclassified constant.** Not yet decided whether this is a rule of thumb, a calibration or a physical value. Classifying it is open work — it is deliberately not guessed.

**Value.** `Blasius (1908): cf = 0.664/√Re for laminar flat plate → cd0 ∝ 1/√Re; Schlichting (1979): turbulent cf ∝ Re^{-0.2} (Prandtl); Hepperle (2012): electric endurance; e insensitive to Re at sub-stall; Drela (XFOIL framework): span-efficiency dominated by planform, not Re; Anderson (2016): §6.1.2 drag polar, §6.7.2 (L/D)_max`

**Formula — as the code writes it.**

```
(docstring Sources block, lines 22-30)
```

**Inputs.** — *(leaf: a constant or an external input)*

**Produced by.** `app/services/polar_re_table_service.py:24` — `module docstring`

🟢 **Verified against the code** — an independent reviewer read this line and confirmed the formula, unit and value (2026-08-18 audit).

**Consumed by.**

- 🔴 **nothing found.** A computed value nothing reads is a finding (ADR 0021).

**Source.** 🟡 PARTIAL

> Verified: Blasius, Z. Math. Phys. 56 (1908) 1–37 (local c_f = 0.664/√Re_x); Schlichting, Boundary-Layer Theory 7e (1979), Ch. XXI (turbulent flat plate ∝ Re^-1/5); Anderson 6e §4.12.1–4.12.2
>
> — via `aerodynamics-expert`

**⚠️ Divergence from the source.** Three problems in the docstring's Sources block. (1) The Anderson section number is wrong: the drag polar is §6.7.2, not §6.1.2 — §6.7.2 covers BOTH the polar and (L/D)_max. (2) 'Hepperle (2012): electric endurance' and 'Drela (XFOIL framework)' carry no title, page or equation and are not citations. (3) Blasius 0.664/√Re is the LOCAL c_f; the chord-integrated value is 1.328/√Re_c — the docstring conflates them (harmless for the ∝ Re^-1/2 argument).

🟡 *Reported by the extraction pass, not independently verified.*

**Cited in the code itself.** `- Blasius (1908): cf = 0.664/√Re for laminar flat plate → cd0 ∝ 1/√Re
- Schlichting (1979): turbulent cf ∝ Re^{-0.2} (Prandtl); overall Re scaling
  dominated by laminar/transition terms at RC scale → 1/√Re is pragmatic
- Hepperle (2012): electric endurance; e insensitive to Re at sub-stall
- Drela (XFOIL framework): span-efficiency dominated by planform, not Re
- Anderson (2016): §6.1.2 drag polar, §6.7.2 (L/D)_max`

---
*Cluster [[_index-aero-polars|aero-polars]] · generated from the 2026-08-18 extraction.*
