# Path 1 — the speeds

> **62 canonical quantities · 46 canonical formulas**, collapsed from 157 register nodes.
> 74 nodes are deliberately outside the skeleton (echoes, plot parameters, plumbing).

Every entry is `status: draft` — **it cites nothing and decides nothing** until you approve it.

## Where it stands

| | |
|---|---|
| dimensional check | 🟢 29 balance · ⚪ 15 not algebraic · 🔴 2 do not balance |
| provenance | 🟢 28 sourced · 🟡 13 partial · 🔴 5 unsourced |
| implementations | 77 agree · 5 deviate undeclared · 1 mismapped |
| **conflicts** | **10** quantities produced by genuinely different laws |

## Conflicts — decide these, do not merely read them

- [[stall-speed]] — Three genuinely different laws produce V_S across six producers.
- [[high-lift-clmax]] — Two different laws for the same quantity.
- [[max-lift-to-drag-parabolic]] — One user-visible number, two different laws behind it.
- [[minimum-drag-speed-closed-form]] — V_md is produced by three mutually independent laws in this application -- see also minimum-drag-speed-from-polar and minimum-drag-speed-heuristic.
- [[minimum-drag-speed-from-polar]] — Second of three independent laws for V_md (see minimum-drag-speed-closed-form).
- [[minimum-drag-speed-heuristic]] — Third of three independent laws for V_md.
- [[minimum-sink-speed-heuristic]] — V_mp has two independent producers -- argmin of the computed sink rate, and this flat 1.
- [[cruise-speed-resolution]] — Three incompatible definitions of V_cruise coexist.
- [[operating-point-speed-from-stall-margin]] — V_x and V_y are labelled best-angle and best-rate-of-climb speeds but contain no climb relation at all -- no thrust, no drag polar, no excess power.
- [[zero-lift-drag-from-sweep]] — Two genuinely different laws produce a number labelled C_D0.

## Approval order

A formula is approvable only once its inputs are. Work down the layers.

**Layer 1** — [[air-density-isa]] · [[weight-from-mass]] · [[wing-loading]] · [[aspect-ratio]] · [[mean-geometric-chord]] · [[high-lift-clmax]] · [[dive-speed]] · [[climb-speed-for-power-loading]] · [[turn-load-factor]] · [[inverted-max-lift-coefficient]] · [[negative-limit-load-factor]] · [[mean-thrust-derate]] · [[battery-mass-from-capacity]] · [[mass-summation]]

**Layer 2** — [[induced-drag-factor]] · [[stall-speed]] · [[stall-wing-loading-limit]] · [[gust-mass-ratio]] · [[thrust-to-weight]] · [[relative-mass-deviation]]

**Layer 3** — [[minimum-drag-speed-heuristic]] · [[minimum-sink-speed-heuristic]] · [[operating-point-speed-from-stall-margin]] · [[stall-speed-in-turn]] · [[gust-alleviation-factor]] · [[stall-margin-ratio]]

**Layer 4** — [[cruise-speed-resolution]]

**Not reachable from the declared inputs (19)** — these need an input that no formula in this path produces:

[[dynamic-pressure]] · [[lift-balance-speed]] · [[clmax-from-polar]] · [[linear-lift-curve-inverse]] · [[lift-to-drag-ratio]] · [[max-lift-to-drag-parabolic]] · [[sink-rate]] · [[minimum-drag-speed-closed-form]] · [[minimum-drag-speed-from-polar]] · [[minimum-sink-speed-from-polar]] · [[lift-coefficient-required]] · [[gust-velocity-schedule]] · [[gust-load-increment]] · [[cruise-thrust-constraint]] · [[power-required-electrical]] · [[endurance-from-battery]] · [[zero-lift-drag-from-sweep]] · [[reynolds-scheduled-polar]] · [[stall-onset-detection]]

