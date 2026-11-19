---
canon: crow-mix
kind: quantity
symbol: s
unit: 1
role: input
tags:
  - canon/quantity
  - module/control-deflections
  - role/input
type: scalar
---

# Crow mix · `s`

The swept variable of the butterfly curves: `s = 0` is the landing configuration, `s = 1` full crow (the angles [[crow-flap-deflection]] and [[crow-aileron-deflection]]). It is the abscissa of [[butterfly-stall-speed-curve]], [[butterfly-approach-speed-curve]] and [[butterfly-glide-angle-curve]] and nothing else: the caller supplies no value, the formula runs the grid itself (`butterfly_mix_steps`, `config.yaml`). Listed so that a curve says what its `x` is.

**Unit.** `1`

