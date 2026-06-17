# Spar Vector Solver → CAD Spare insertion — design spec

**Date:** 2026-06-17
**Status:** Draft for review
**Builds on:** #1019 (SectionGeometry: rotation-aware thickness/top_z/bottom_z/center_z),
#1008 (spar sizing: required section modulus, material, shape), #1002 (spanwise V/M).
**Related:** #1011 (buckling — feeds the strength check), #1027 (test hygiene).

## Problem / goal

We can now compute loads (#1002), spar cross-section sizing (#1008), and the real
section envelope (#1019). The missing step is turning that into a **buildable spar
layout**: where each spar sits, which direction it runs, what diameter/wall it has,
and how the pieces and the two wing halves join — emitted as `cad_designer`
`Spare` objects that drop straight into the construction.

## Structural model — two collinear spar systems

Classic two-spar wing: **front spar = bending**, **rear spar = torsion +
positioning**. We solve both.

### Front (main) spar — carries bending
Priority hierarchy (highest first):

1. **Continuous + root-collinear carry-through.** One straight tube root→tip on
   each half, and the two halves collinear through `y=0` (one beam across the
   centreline). Loads pass wing-to-wing directly.
2. **Continuous per half, root collinear via reinforcement.** If a single straight
   tube can't be collinear across the root (geometry), keep the per-half spar but
   add a **dedicated reinforcement spar**: short, *truly collinear in the surface*,
   sized to the root moment, placed as close as possible to the **max-moment**
   (root) station. Wing-to-wing moment transfer is handled there by a constructive
   joiner (telescoping sleeve / pin), not by a continuous main spar.
3. **Segmented + telescoping.** Where a straight piece can't stay inside the
   envelope *and* meet the #1008 strength diameter, break at the segment boundary
   and join telescoping: **OD of the outer (tip-side) piece = ID of the inner
   (root-side) piece**, with a load-transfer overlap.

**Confirmed priority rule:** keep a piece continuous only while its
strength-required OD (#1008) fits inside the local section at every station it
covers. Otherwise split + telescope. **Strength beats part-count.**

### Rear spar — positions the halves, reacts torsion
- **Always present**, aft region, collinear across the root.
- Primary role: align the two halves and lock the incidence / react torsion (the
  front+rear pair forms the couple against wing twist). Secondary: carry local aft
  moments (sized to the aft-station loads).
- **Strong-dihedral fallback:** if a straight collinear rear member would exit the
  envelope, emit a **bent steel pin** spec (a rod following the dihedral V) that
  joins the two halves instead of a straight Spare.

## Why (rationale, for the record)
- Front=bending / rear=torsion is the standard two-spar principle; one spar lets
  the section rotate about it, the beamed pair fixes incidence and reacts torsion.
- Collinear carry-through transfers root bending wing-to-wing directly; joints are
  stress risers and weight, so we prefer none — but where geometry forbids a
  straight continuous spar, a short collinear reinforcement at the max-moment
  station preserves the clean transfer while the main spar follows the geometry.
- A straight collinear rod can't span two strongly-dihedral halves inside the
  skin; a bent pin follows the V and stays contained.

## Algorithm

Natural break points are **segment boundaries** (each `WingSegment` is a ruled
loft between two airfoils → a straight line at a constant chord+depth fraction
stays approximately in-envelope within one segment).

For each spar (front at max-thickness x/c; rear at an aft x/c, default ~0.65):

1. **Per-station target & envelope.** From `SectionGeometry`, at the spar's x/c,
   get `center_z` and the contained band `[bottom_z + clr, top_z − clr]` at sampled
   y-stations (clr = skin/packing clearance, default from #1008 packing_factor).
2. **Strength diameter per station.** From #1008 sizing at that station
   (required section modulus → OD for shape=tube/rod, with ID from wall).
3. **Greedy straight-piece fit, root→tip.** Extend a straight piece while a single
   straight tube of the piece's governing OD (the most-inboard, highest-moment
   station it covers) stays inside every covered station's band. When containment
   OR strength-fit fails → close the piece, start the next; joint = telescoping
   (next OD = this ID; overlap length sized for load transfer). One piece covering
   all segments ⇒ `continuous`.
4. **Root collinearity (front).** Test whether the inboard pieces of left+right can
   be one straight collinear line through `y=0` within envelope+strength. Yes ⇒
   single carry-through. No ⇒ emit the reinforcement spar (step 2-3 restricted to
   the root region, forced collinear) + joiner metadata.
5. **Rear spar.** Same fit at the aft x/c, require root collinearity; if a straight
   collinear member exits the envelope under the wing's dihedral ⇒ emit `bent-pin`
   joiner spec instead of a straight Spare.

## Output

Per wing: a **SparPlan** = list of spar pieces, each with
`spare_origin` (mm), `spare_vector` (unit dir), `outer_d`, `inner_d`/`wall`,
`shape`, governing station + utilisation, and a **joint type** between consecutive
pieces / across the root:
`continuous | telescoping(overlap, OD=ID) | reinforcement+joiner | bent-pin`.

Each piece maps to a `cad_designer` `Spare` (construct instances — do NOT modify
the read-only `Spare`/`WingSegment` topology; add via the existing
`WingSegment.spare_list` / converter path). Units mm.

## Architecture / decomposition (epic + sub-issues)

1. **Spar-vector solver core** — `cad_designer` module consuming SectionGeometry +
   #1008 sizing + #1002 loads → SparPlan (front + rear, continuous/telescoping,
   root collinearity/reinforcement, bent-pin detection). Pure-ish; slow
   (requires_cadquery, real geometry) + fast (mocked SectionGeometry/sizing) tests.
2. **v2 `spar-plan` endpoint + schemas** — `POST /aeroplanes/{id}/spar-plan`
   returns the SparPlan for review/visualisation. Fast mocked tests.
3. **CAD insertion** — emit the SparPlan's `Spare`s into the WingConfiguration /
   construction (existing Spare insertion path). Round-trip test.
4. **Frontend (later)** — visualise the plan (overlay on the planform/3D) + an
   "insert into construction" action.

## Defaults to confirm at review
- Front spar at the **max-thickness** x/c; rear spar at **~0.65 c** (configurable).
- Spar shape **round tube** (telescoping + bent-pin both assume round); rod where a
  solid is needed. The #1008 rectangular/capped shapes are not telescoping-friendly
  → tube/rod for the auto-plan; other shapes remain a manual override.
- Clearance band from #1008 `packing_factor` (skin + glue allowance).
- Dihedral threshold for "bent-pin instead of straight rear spar": default where a
  straight collinear rod's mid-span leaves the envelope (geometry-derived, not a
  fixed angle).

## Out of scope
- Buckling of the spar (#1011 feeds the strength diameter once available).
- Multi-spar (>2) layouts; rib/shear-web design.
- Automatic overlap-length structural proof for telescoping joints beyond a
  rule-of-thumb (flag for a follow-up if needed).
