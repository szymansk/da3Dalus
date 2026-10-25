---
canon: thrust-at-airspeed
kind: quantity
symbol: T
unit: "N"
role: output
tags:
  - canon/quantity
  - discipline/powered
  - point/free
  - role/output
type: scalar
---

# Thrust at airspeed · `T(V)`

The thrust a chosen propeller actually delivers at the speed currently flown — not the
bench number. Propeller thrust falls with airspeed, because motor and propeller are
roughly constant-power devices at high throttle. Evaluated at the given flight-speed; the
optimisers embed the same relation over their own V (`embeds:`).

**Unit.** `N`

**Produced by.** [[thrust-at-airspeed-from-coefficient]]
