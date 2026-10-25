---
canon: spanwise-lift-distribution
kind: quantity
symbol: l(y)
unit: N/m
role: output
tags:
  - canon/quantity
  - discipline/structure
  - point/free
  - role/output
type: curve
---

# Spanwise lift distribution of the main wing · `l(y)`

Aerodynamic normal force per unit span along the main wing, `l(y) = q·c·c_n`, at the operating
point the caller supplies (speed, load factor). From AVL strip forces; replaces the elliptic
assumption. Normal to the strip, so it tilts with dihedral; equal to the lift per unit span on a flat
wing. Attached flow, no stall detection (see [[spanwise-loads]]).

**Unit.** `N/m`

**Produced by.** [[spanwise-loads]]
