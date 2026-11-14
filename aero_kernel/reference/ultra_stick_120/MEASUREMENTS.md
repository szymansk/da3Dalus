# Ultra Stick 120 (FASER): published reference values

What has been measured on the real aircraft and published, for comparison with the kernel's results
on `ultra_stick_120.airplane.json`. Nothing here is used by a test: the kernel marks no value as
validated (A11).

Sources:

- **[F]** Owens, Cox, Morelli, "Development of a Low-Cost Sub-Scale Aircraft for Flight Research:
  The FASER Project", NASA NTRS 20060022541 (2006): "extensive wind tunnel testing was conducted
  with the same aircraft used for flight testing", so no Reynolds scaling lies between model and
  aircraft. (The tunnel is named in Hoe, Owens, Denham, NASA NTRS 20120014506: the NASA Langley
  12-Foot Low Speed Tunnel.)
- **[S]** University of Minnesota, UAV simulation package `UMNUAV_sim_v4`
  (https://dept.aem.umn.edu/~uav/downloads.html), file `Simulation/Libraries/FASER_Aero.mat`:
  FASER aerodynamic data as tables over angle of attack (-5 to 40 deg) and sideslip (-30 to 30 deg),
  with increments for aileron, elevator, rudder, flap and power. `FASER_config.m` says the data
  come from NASA's FASER simulation and gives S = 0.7692 m2, b = 1.9172 m, c = 0.4336 m. How the
  tables were derived from the tunnel runs is not documented in the package, and they are **not**
  the curve [F] prints (below). The package is copyrighted by the Regents of the University of
  Minnesota and is not copied here; the numbers were read from it on 2026-11-14.
- **[J]** Jaeger et al., "Parametric Thrust and Drag Identification from Flight Test via Energy
  Maneuverability", AIAA 2026-4164: flight identification on Minnesota's Ultra Stick 120 (20.17 lb).

## Aircraft as tested

| | value | source |
|---|---|---|
| mass | 8.95 kg (19.72 lbf) | [F] Table 2 |
| centre of gravity | 0.25 c behind the leading edge, 0.165 c above the bottom of the fuselage | [F] Table 2 |
| moments of inertia | I_x 0.496, I_y 0.656, I_z 1.164, I_xz 0.560 slug ft2 | [F] Table 2 |
| propeller | 14 x 9.5 folding, electric | [F] Table 1 |

## Wind tunnel as printed in [F] (Figure 2a, read off the plot)

Lift coefficient about -0.29 at -5 deg and 0.06 at 0 deg; "two stall points, a minor one at
alpha = 12 deg and the main one at alpha = 15 deg" ([F]), about 0.89 and 0.94; about 0.84 beyond.
The slope between -5 and 5 deg is about 4.0 to 4.1 per rad.

## The tables of [S], sideslip 0, controls neutral, base table (reduced here)

The base table is the one to which the power increment adds nothing at its last advance ratio; that
it is the power-off case is an inference.

| quantity | value | how it was reduced |
|---|---|---|
| lift curve slope | 4.42 per rad | straight line through -5, 0 and 5 deg |
| lift coefficient at 0 deg | 0.107 | the same line |
| first lift maximum | 1.007 at 12.5 deg | the table; beyond it C_L stays between 0.94 and 1.01 up to 40 deg |
| minimum drag coefficient | 0.0370 at 0 deg | the table |
| best lift-to-drag ratio | 11.1 at 5 deg (C_L 0.49) | the table's points, no interpolation |
| dC_m / dC_L | -0.079 | straight line through -5, 0 and 5 deg |
| neutral point | 0.079 c behind the moment reference; 0.136 to 0.143 m behind the leading edge | -dC_m/dC_L * c. ASSUMPTION: the moments refer to the centre of gravity of [F], a quarter chord behind the leading edge; the package only comments "CG set to be quarter-chord point". The range is a quarter of the document's chord (0.4057 m) or of c = 0.4336 m |
| C_l,beta | -0.044 per rad at 0 deg | difference between -5 and 5 deg of sideslip |
| C_n,beta | 0.053 per rad at 0 deg | the same |
| rolling moment of the ailerons | 0.0155 at 5 deg, 0.0634 at 25 deg | the table (magnitude) |

The roll damping C_l,p = -0.373 in [S] is, by [F], "from analytical methods", not a measurement.

## Flight ([J], Minnesota's aircraft)

| quantity | value |
|---|---|
| C_D0 identified from flight | 0.0377, standard deviation 0.0018 |
| C_D0 of the paper's own build-up | 0.0353 |

## First comparison (2026-11-14, ISA sea level, 8.95 kg, kernel on the document as built)

The kernel's coefficients refer to its own wing area, 0.7833 m2 (the full planform); those of [S] to
0.7692 m2. The third column gives the value of [S] on the kernel's area where that matters.

| quantity | kernel | [S] | [S] on the kernel's area | [F] Figure 2a |
|---|---|---|---|---|
| neutral point behind the leading edge | 0.148 to 0.178 m (three method worlds) | 0.136 to 0.143 m | | |
| lift curve slope | 5.18 per rad (minimum sink), 5.26 (best glide) | 4.42 | 4.34 | about 4.0 to 4.1 |
| maximum lift coefficient | 1.38 at 20.5 deg | 1.007 at 12.5 deg | 0.99 | about 0.89 at 12 deg, 0.94 at 15 deg |
| stall speed at 8.95 kg | 11.5 m/s | 13.6 m/s from 1.007 | | 14.1 m/s from 0.94 |
| best lift-to-drag ratio | 15.9, no landing gear, engine or propeller | 11.1, complete aircraft | | |
| C_n,beta | 0.029 to 0.052 per rad over the operating points | 0.053 at 0 deg | | |
| C_l,beta | -0.073 to -0.140 per rad over the operating points | -0.044 at 0 deg | | |

Not converged on this aircraft: `stall-break` (the lift maximum at 20.5 deg leaves no room for the
break below the sweep's 25 deg) and the inverted maximum lift (the sweep ends at -15 deg).

The largest difference is the lift: the kernel's maximum is 40 to 50 % above the measurements, its
stall 5 to 8 deg later, and its lift curve slope about 20 % steeper. The wing section is not the
cause: with NACA 0015 as a stand-in (#1392) the kernel gave 1.30 at 21 deg and 4.79 per rad; with
the section fitted to the plan (#1394) the difference grew. For comparison, lifting-line theory
gives 2 pi / (1 + 2 / AR) = 4.42 per rad for the wing alone at AR = 4.76.
