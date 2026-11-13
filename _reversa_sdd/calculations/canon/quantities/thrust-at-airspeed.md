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

The **full-throttle** thrust the fitted motor and propeller deliver at the speed currently
flown — not the bench number. It falls with airspeed because the advance ratio rises and the
thrust coefficient `C_T(J)` falls with it, at the rpm of the torque balance
([[motor-propeller-equilibrium]], which does not assume constant power). Evaluated at the given flight-speed; the
optimisers embed the same relation over their own V (`embeds:`).

**Unit.** `N`

**Produced by.** [[thrust-at-airspeed-from-coefficient]]
