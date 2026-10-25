---
canon: battery-charge-capacity
kind: quantity
symbol: Q_bat
unit: mAh
role: derived
status: draft
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - point/none
  - group/powertrain-battery
  - role/derived
type: scalar
---

# Battery charge capacity · `Q_bat`

Rated charge of the pack, read as the catalogue stores it (field `capacity_mah`; maintainer, 2026-10-25, #1235). The pack energy [[battery-capacity]] is derived from it. 0 in the database means 'not configured'.

**Unit.** `mAh`

**Produced by.** [[airplane-components]]
