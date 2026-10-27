---
canon: turn-sideslip
kind: quantity
symbol: beta_turn
unit: deg
role: output
tags:
  - canon/quantity
  - discipline/lateral
  - point/minimum-sink
  - role/output
type: scalar
---

# Sideslip in the steady turn · `beta_turn`

The steady sideslip an aircraft without ailerons must fly in its tightest sustained turn so that the sideslip's rolling moment cancels the rolling moment of the curved flight path (Drela, Design Rules, "Steady Sideslip in Turns"). Worst case: bank angle 45 degrees at the minimum-sink lift coefficient. Positive: nose pointing outside the flight circle.

**Unit.** `deg`

**Produced by.** [[turn-sideslip]]

**Applies to.** Aircraft without ailerons (`has_no_aileron`); otherwise not applicable.

**Used by.** the evaluation rule `turn-sideslip` (`drela.yaml`; the band 5…15 deg is Drela's and belongs to the evaluation, A10).
