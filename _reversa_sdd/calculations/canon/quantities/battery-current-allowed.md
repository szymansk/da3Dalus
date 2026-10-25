---
canon: battery-current-allowed
kind: quantity
symbol: I_bat,max
unit: A
role: derived
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - point/none
  - group/powertrain-battery
  - role/derived
type: scalar
---

# Allowed continuous battery current · `I_bat,max`

`I_bat,max = C_rate · Q_bat / 1000` (`Q_bat` in mAh, `C_rate` in 1/h). A value for the evaluation to compare with [[battery-current]]; the canon draws no verdict from the two (A10).

**Unit.** `A`

**Produced by.** [[airplane-components]]
