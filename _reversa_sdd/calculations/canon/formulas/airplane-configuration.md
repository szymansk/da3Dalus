---
canon: airplane-configuration
entry: formula
kind: procedure
tool: GEO
shape: law
status: draft
output: airplane-takeoff, airplane-landing
source_status: NO_SOURCE_FOUND
dimensional_check: PROCEDURAL
tags:
  - canon/formula
  - source/no-source-found
  - dim/procedural
  - shape/law
  - kind/procedure
  - status/draft
inputs: {airplane: airplane, flap_deflection: null}
outputs: {airplane_cfg: null}
optional: [flap_deflection]
# ESCALATED: which devices count as flaps — the canon says "if the geometry has flaps" but states no
# rule for which devices count (e.g. trailing-edge devices on the main wing acting as flaps).
applications:
  - id: takeoff
    bind: {flap_deflection: flap-deflection-takeoff}
    produce: {airplane_cfg: airplane-takeoff}
  - id: landing
    bind: {flap_deflection: flap-deflection-landing}
    produce: {airplane_cfg: airplane-landing}
---

# The airplane in its take-off or landing configuration

**Canonical form**

```
airplane_cfg := airplane with its flaps at delta_f,cfg      (cfg = take-off | landing)
```

**Produces** [[airplane-takeoff]] · [[airplane-landing]]  ·  **from** [[airplane]] · [[flap-deflection-takeoff]] · [[flap-deflection-landing]]

**Kind: a procedure — an evaluation of the model.** The same airplane with its flaps set for the
configuration: the flap is in the geometry, not a factor on `C_L,max` ([[stall-speed]], 2026-10-02).
The configured airplane is what the take-off and landing applications of [[stall-speed]] bind
(A2: a named condition is a quantity, produced by its own application — #1181, architect
2026-10-14).

**Without flaps there is no configuration — the same aircraft, not a fallback** ([[stall-speed]],
maintainer 2026-10-02): if the geometry has flaps, they are used as constructed for that
configuration; if it has none, the configured airplane is the airplane itself.

**The deflection is a design input** ([[flap-deflection-takeoff]], [[flap-deflection-landing]];
maintainer, 2026-10-14), not bounded by the geometry's stop `positive_deflection_deg`: the canon is
used to find out which stop the wanted speed needs.

**Four cases** (architect, 2026-10-14; `flap_deflection` is optional):

| aircraft | deflection | result |
|---|---|---|
| no flaps | absent | the unchanged aircraft, no warning — the canon's own definition ([[stall-speed]], maintainer 2026-10-02) |
| no flaps | given | the unchanged aircraft and a `practice` warning `deflection_without_flap`: the supplied value is not used |
| flaps | absent | no value: `missing_input` for the configured airplane; its dependents fail; the clean stall speed still computes |
| flaps | given | the deflection applied exactly, also beyond the stop |

Which devices count as flaps is not yet stated in the canon (escalated in the front matter).

**Validity, declared (no threshold, A10).** The configured airplane is evaluated with NeuralFoil's flap
model, which is unverified at large deflections and low Reynolds number: ANFORDERUNGEN.md, §
"Rollwirkung gegen die gebauten Ruderausschläge" (lines 544–546: beyond about 25° the result is only as
good as that model), and § "Nicht im MVP: die Querruderdifferenzierung" (lines 1007–1008: 15–25° at
Re ≈ 60 000, unverified). Landing settings typically lie above that range.

**Source.** 🔴 NO SOURCE FOUND — a construction step, adopted on the maintainer's statement in
[[stall-speed]] (2026-10-02).
