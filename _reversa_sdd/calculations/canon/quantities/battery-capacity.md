---
canon: battery-capacity
kind: quantity
symbol: E_bat
unit: Wh
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/powertrain-battery
  - role/derived
type: scalar
---

# Usable battery capacity · `E_bat`

Usable pack energy, derived: `E_bat = Q_bat / 1000 · U_bat` — the rated charge [[battery-charge-capacity]] (mAh, as the catalogue stores it) in Ah times the nominal pack voltage [[battery-voltage]] (cells × 3.7 V). Nothing is read in Wh (maintainer, 2026-10-25, #1235). 0 means 'not configured'.

**Unit.** `Wh`

**Produced by.** [[airplane-components]]

**Used by.** [[battery-mass-from-capacity]] · [[cruise-target-performance]] · [[endurance-and-range]] · [[endurance-and-range-optimum]]
