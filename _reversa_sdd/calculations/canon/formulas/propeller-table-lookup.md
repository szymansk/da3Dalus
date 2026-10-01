---
canon: propeller-table-lookup
entry: formula
kind: procedure
shape: law
status: draft
output: thrust-coefficient
source_status: SOURCED
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/sourced
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
---

# Thrust coefficient from the measured propeller table

**Canonical form**

```
C_T := interp( table of the chosen propeller, J )
```

**Produces** [[thrust-coefficient]]  ·  **from** [[airplane]] · [[advance-ratio]]

**Kind: a procedure — a table lookup.** The thrust coefficient of the propeller fitted to the
airplane, interpolated at the advance ratio. 454 APC propellers with 300 187 measured
points are in the database; extrapolation outside the measured `J` range is flagged.
