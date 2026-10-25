---
canon: battery-c-rate
kind: quantity
symbol: C_rate
unit: 1/h
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

# Continuous discharge rate · `C_rate`

Continuous C-rate of the pack as the manufacturer publishes it (field `c_rate`; maintainer, 2026-10-25, #1235). A burst rating is not modelled. With it [[airplane-components]] derives the allowed continuous current [[battery-current-allowed]] = `C_rate · Q_bat`.

**Unit.** `1/h`

**Produced by.** [[airplane-components]]
