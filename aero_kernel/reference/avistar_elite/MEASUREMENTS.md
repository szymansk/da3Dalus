# Avistar Elite: published reference values

What has been measured on the real aircraft and published, for comparison with the kernel's results
on `avistar_elite.airplane.json`. Nothing here is used by a test: the kernel marks no value as
validated (A11), and the published values are coarse.

Source **[P]**: Dantsker, Caccamo, Vahora, Mancuso, "Flight & Ground Testing Data Set for an
Unmanned Aircraft: Great Planes Avistar Elite", AIAA 2020-0780,
https://cs-people.bu.edu/rmancuso/files/papers/UAVDB_Avistar_AIAAScitech20.pdf . The paper shows
time histories as figures; the time series themselves are announced on http://www.uavdb.org , whose
TLS certificate was expired on 2026-11-14, so none was downloaded.

## Aircraft as flown

| | value | source |
|---|---|---|
| gross mass | 3.70 kg (3.07 kg empty, 0.63 kg battery) | [P] Table 1 |
| second test aircraft | 3.95 kg (250 g more, same outer geometry, "very similar" centre of gravity) | [P] section V |
| motor, propeller, battery | Model Motors AXI 4120/14, APC 13x8E, 4S 14.8 V 6 Ah | [P] Table 2 |
| flap setting in every published manoeuvre | 0 deg | [P] section V |
| flight time | 10 to 15 min | [P] Table 2 |

## Flight observations

| observation | value | source |
|---|---|---|
| trimmed level flight | 20 m/s | [P] Table 5 |
| power-off deceleration at 3.70 kg | no stall break up to full elevator; the aircraft mushes and side-slips at approximately 12 m/s | [P] section V, Figures 18 and 19 |
| power-off deceleration at 3.95 kg | visible stall, the nose drops at approximately 14 m/s | [P] section V, Figures 20 and 21 |

Both speeds are read from the paper's text ("approximately"). The airspeed came from the inertial
and GPS system: the pitot-static probe was not yet installed ([P] section II.B). A mass 7 % higher
raises a stall speed by 3 % at equal maximum lift, so the two readings (12 and 14 m/s) do not
describe one maximum lift coefficient; they bound it loosely.

## Not available

- Maximum lift coefficient, polar, glide ratio, roll rate and control derivatives as numbers: the
  manoeuvres were flown (idle descent, aileron, elevator and rudder singlets and doublets), but only
  the time series would give them.
- Centre of gravity of the tested aircraft, wind-tunnel data of the airframe.
- The wind-tunnel data of the APC 13x8E propeller are announced for the UIUC Propeller Database.

## First comparison (2026-11-14, ISA sea level, kernel on the document as built)

| quantity | kernel | published |
|---|---|---|
| `stall-speed` at 3.70 kg | 11.4 m/s (`max-lift-coefficient` 1.22) | mush at approximately 12 m/s |
| `stall-speed` at 3.95 kg | 11.7 m/s | stall at approximately 14 m/s |

The kernel's other results on this aircraft (neutral point 0.494 to 0.528 m behind the nose over
the three method worlds, minimum-sink speed 14.0 m/s, best glide ratio 16.4 without landing gear and
propeller) have no published counterpart.
