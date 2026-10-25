---
canon: battery-energy-required
kind: quantity
symbol: E_req
unit: Wh
role: input
tags:
  - canon/quantity
  - stage/references
  - module/construction
  - group/powertrain-battery
  - role/input
type: scalar
---

# Battery energy the mission requires · `E_req`

Energy the pack must deliver to fly the mission target: the endurance target times the battery power at the cruise speed, `E_req = t_target · P_bat` (the part-load chain, #1235/#1238). Not the energy of a chosen battery ([[battery-capacity]]): it is what the designer needs in order to size a placeholder battery in the design direction (design layer, post-MVP; #1285).

No formula produces it yet; its producer comes with #1238 (part-load endurance in the kernel), and until then it is the one input of [[battery-mass-from-capacity]] without a source.

**Unit.** `Wh`

**Used by.** [[battery-mass-from-capacity]]
