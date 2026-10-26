# Reference fleet copies

Geometry documents of the MVP aircraft, used by the kernel tests as real input. Each copy equals
its source except for the **additions** listed here; `test_reference_fleet.py` strips the
additions and compares the result with the recorded SHA-256 of the source, so "unchanged
otherwise" is checked, not claimed. The sources are never touched.

The kernel rejects airfoil file paths (ARCHITECTURE 8.11), so the copies keep the sources' paths
verbatim and the `.dat` files lie next to the JSON; `reference_fleet.py` resolves each path by its
file name into inline coordinates when it loads a document.

| | BRYAN | JAGUAR |
|---|---|---|
| copy | `bryan/bryan.airplane.json` | `jaguar/flugzeug.json` |
| source | `scripts/canon_checks/reference_fleet/bryan/bryan.airplane.json` | `~/Downloads/da3dalus-import/modelle/jaguar/flugzeug.json` |
| SHA-256 of the source file | `1e66f95731c52413a57ce92bbc145a4d8d0e96249a3b3b912fb7fc2f1b1994ed` | `763d7299d27e8cd43fc91a264b2c34d3b1f1780cf3a1fa63b97aa7391982dfad` |
| SHA-256 of the source as canonical JSON (sorted keys, compact) | `09952f107c1204abdd160fb59e668c0bc13131b2a4112a270d77470c9c15d4e1` | `92e8ad7c5b29df99175b1c2306b5a4b5509bf753736e853b12114660c2f1bed6` |
| mass | 0.151 kg (`total_mass_kg` in the source) | 0.160 kg, approx., maintainer 2026-10-14 (`total_mass_kg` is `null` in the source, so tests pass the mass as a value) |

| | CHEKKER | BELEMNITOS |
|---|---|---|
| copy | `chekker/flugzeug.json` | `belemnitos/flugzeug.json` |
| source | `~/Downloads/da3dalus-import/modelle/chekker/flugzeug.json` | `~/Downloads/da3dalus-import/belemnitos/flugzeug.json` |
| SHA-256 of the source file | `7be944658e150e02c389650dbb8a1e2103e096052547213640bb11f2b154cd6f` | `ef8c818d4a38cf5a30087530a4dfcaef544d975b9fac98535433cd9bccfa9023` |
| SHA-256 of the source as canonical JSON | `01779a0cc90e44b98ea4a49ab8fd949472f0305f1701f60b39b0e8aaf755e3c4` | `747c570e5527ccfc604a7e466ed2049d96b04b29b05550d07940230241a5754e` |
| mass | 0.439 kg (`total_mass_kg` in the source; it is also the DB's value) | 0.280 kg, estimated total mass, maintainer 2026-10-26, exact value after the build (equal to the source's `total_mass_kg`, which stays in the copy; tests pass the mass as a value) |
| reference point | `xyz_ref` (0.17893, 0, -0.0264) m | `xyz_ref` (0.0564, 0, 0) m |

| | WIESEL | RV-7 |
|---|---|---|
| copy | `wiesel/wiesel.airplane.json` | `rv7/rv7.airplane.json` |
| source | the app's own export, see below | the app's own export, see below |
| SHA-256 of the raw export | `d69886bd93a817c9bdb1d0d82176dcac3e24c2215ac0762e94434e00eedf5ac5` | `34e9f6fb1bb961d4d8a3843912c321e0fd0906c793a696bbce16375aaafea2af` |
| SHA-256 of the source (export without its `null` fields) as canonical JSON | `f8528c5a688219caa834ac73eb190f1d7aa3cd04045d6abfaaed48b77f423e06` | `72e8f9e0c5307a001b89b841d6f486eb23624c2ce71f54503dad56350abd06b2` |
| mass | 0.625 kg (`aeroplanes.total_mass_kg` of the DB; the export carries `null`, so tests pass it as a value) | 0.500 kg, approx., maintainer 2026-10-25 (the DB has no mass; its `mass` design assumption of 1.5 kg is the default and is ignored) |
| reference point | `xyz_ref` (0, 0, 0) m: the DB has none | `xyz_ref` (0, 0, 0) m: the DB has none |

WIESEL and RV-7 exist only in the app DB. They were exported through the app's own endpoint
`GET /aeroplanes/{id}` (`aeroplane_service.get_aeroplane_schema`, the `AeroplaneSchema` the geometry
format is the documented form of) in-process (FastAPI `TestClient`) against a **copy** of `db/test.db`
made with `sqlite3 .backup` on 2026-10-25; `db/test.db` itself was not written. The schema's
unset fields are `null` in the export; the source is the export with every `null` field removed
(the format says an absent field and a `null` are the same, and JAGUAR's source is written that way).

The DB's CHEKKER is not used: its fin has 48 ribs against the source's 12 and its wings and airfoil
files carry other names; the source file is the better document.

Regime (ADR 0028), chord Reynolds number 3e4 to 1e6 at ISA sea level, Mach <= 0.3. The numbers
are AeroSandbox's `include_centerline_distance` values of the main wing (`FleetMember.asb_reference`):

| | span | S | MAC | wing loading | Re at 10 m/s (MAC) |
|---|---|---|---|---|---|
| BRYAN | 0.547 m | 7.0 dm2 | 0.133 m | 21 N/m2 | 0.9e5 |
| JAGUAR | 0.624 m | 6.5 dm2 | 0.105 m | 24 N/m2 | 0.7e5 |
| CHEKKER | 0.864 m | 13.6 dm2 | 0.161 m | 32 N/m2 | 1.1e5 |
| BELEMNITOS | 1.499 m | 20.0 dm2 | 0.140 m | 27 N/m2 | 1.0e5 |
| WIESEL | 0.915 m | 14.0 dm2 | 0.163 m | 44 N/m2 | 1.1e5 |
| RV-7 | 0.820 m | 15.0 dm2 | 0.183 m | 33 N/m2 | 1.3e5 |

All six are in the regime: a 0.5 to 1.5 m RC model at 5 to 20 m/s has a chord Reynolds number of
0.5e5 to 2.5e5 and a Mach number below 0.06. The RV-7 is an RC scale model (0.82 m span, MAC
0.183 m), not the 7.0 m aeroplane the name suggests. Its tail chords (rudder tip 0.080 m,
elevator tip 0.076 m) fall below the 7e4 bubble-sensitive line at 10 m/s, as BRYAN's do; the
kernel says so in its warnings.

## Additions to the JSON (the only differences from the source)

`surface_type` (ARCHITECTURE 8.5, D9) on every wing, inserted after `name`. The role follows the
function, never the name, and is assigned by hand from the geometry; it is not computed. The
app-side migration is #1187.

| aircraft | wing (as named in the copy) -> `surface_type` | remarks |
|---|---|---|
| BRYAN, JAGUAR | `Tragflaeche` -> `main_wing`, `Hoehenleitwerk` -> `horizontal_tail`, `Seitenleitwerk` -> `vertical_tail` | conventional layout; the assignment is the team-lead's (2026-10-22) |
| CHEKKER | the same three names, the same types | conventional; one fin (`symmetric` false, 12 ribs up to z = 0.115 m) |
| BELEMNITOS | `Tragflaeche` -> `main_wing`, `V-Leitwerk` -> `v_tail` | **V-tail**: one mirrored surface, 37.6 deg from the horizontal; there is no horizontal or vertical tail |
| WIESEL | `main_wing` -> `main_wing`, `horizontal_tail` -> `horizontal_tail`, `vertical_tail` -> `vertical_tail` | conventional; the main wing's tip curls up 11 mm over its last 25 mm of span, which is a rounded tip, not a winglet |
| RV-7 | `main_wing` -> `main_wing`, `elevator` -> `horizontal_tail`, `rudder` -> `vertical_tail` | conventional; the DB names the surfaces after the moving part, so the name says "elevator" and "rudder" for the whole tail surface; each has two ribs |

No aircraft of the fleet has a canard, twin fins or winglets.

BELEMNITOS' source carries a top-level `quelle` ("e-Hawk_Segler.airplane.json (aiHawk), umgewandelt
2026-10-13"), a provenance note for which the format has no field (the kernel rejects unknown
keys). The copy **omits** it; the test puts it back before it hashes.

RV-7's export gives the root rib of the main wing the bare designation `naca23013.5`, its other five
ribs the path `./components/airfoils/naca23013.5.dat`. The copy gives the root rib the same path
(the kernel resolves airfoil files by path); the test puts the designation back before it hashes.

## Airfoil files (byte-identical copies)

| file | SHA-256 |
|---|---|
| `bryan/bryan_profil.dat` | `75fc1827fb3059c6525464032b3a9c95f48c1205ef513750fd34532ebb69eb62` |
| `bryan/bryan_platte.dat` | `d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595` |
| `jaguar/jaguar_test_da3dalus_export__tragflaeche_kulfan.dat` | `51eadb6d6121bd31cacfb08dead004223142b4f665eedc90e273953af4b92755` |
| `jaguar/jaguar_test_da3dalus_export__hoehenleitwerk_kulfan.dat` | `b902ac2c03d07c19921cbdaf522a4bd47aacf2c6d7f7c7365b8065856ba06003` |
| `jaguar/jaguar_test_da3dalus_export__seitenleitwerk_kulfan.dat` | `9a24aa95dc458b6c5a67965ad97a3797dc638ad06ec76250f8b4dbae651d8cb6` |
| `chekker/chekker_test_da3dalus_export__tragflaeche_kulfan.dat` | `67fd4dedb24e60450644ac2820fc6ac999b54802af4c253b5e27c9785d516e5b` |
| `chekker/chekker_test_da3dalus_export__hoehenleitwerk_kulfan.dat` | `7b3d6d3664542a344b0485c6ba3f54978dfdcf580acb5e50b56a17fe63da8b47` |
| `chekker/chekker_test_da3dalus_export__seitenleitwerk_kulfan.dat` | `a246dcdebed289a8acb57ac88afd05e48c0d3df6085c5cc8d866fb4ad09f41bd` |
| `belemnitos/mh32.dat` | `ad0928ce919261d66d0f58fa22bb450c5cb7f5f5710f8c5bd334005c5e48af4c` |
| `belemnitos/belemnitos_vlw_00.dat` | `55a9987860ab6f75de8c1c3c94f109eabf77d4a389cb8ba54a5e3258c63c0afb` |
| `belemnitos/belemnitos_vlw_01.dat` | `10c7e2d9c33fe6e8ef0dbafd3c9182886864b53e3f43a2cfd4c6165a1afdfec6` |
| `belemnitos/belemnitos_vlw_02.dat` | `ce30712593da820c9a1cbc3de18e92217325c4d92837289404753cbdf536659e` |
| `belemnitos/belemnitos_vlw_03.dat` | `1b1984d95564d7b828c96045c45e2dd86749d74b6df4dcd8fa02c53c12187dd3` |
| `belemnitos/belemnitos_vlw_04.dat` | `fe7f88c0651a1e4bf83e14719b53873b937cb4c07b32cfd2d9944892c3fe5c42` |
| `belemnitos/belemnitos_vlw_05.dat` | `15e69a3bd5289e786682db8fae5ecece396b43eac50b59dbba29604863d455c2` |
| `belemnitos/belemnitos_vlw_06.dat` | `5991bde121db4dd967c47580e74242b4a5b30a545ca07ee3b5844f541a185e8e` |
| `belemnitos/belemnitos_vlw_07.dat` | `c4fc111644816911b722c3ce0b1756311a0d16afa8e37f89f7e94f985614b84d` |
| `belemnitos/belemnitos_vlw_08.dat` | `32299353ef395127caf81fee23404854f110e872ec3e57e464b4b7e0fe79cb11` |
| `belemnitos/belemnitos_vlw_09.dat` | `93171808ee6f7171b6df2a60beb656095296ea1f2ae78ef3906e764164eed109` |
| `wiesel/wiesel_main_wing_kulfan.dat` | `3d9c5083d2b78957c9dbd9d1d062d5705106502fd0e4547238991e7ab7549f4a` |
| `wiesel/wiesel_horizontal_tail_kulfan.dat` | `433c17dc888ef530cccb0485ff2d691e23545c963f39cd99825f719c90cb2917` |
| `wiesel/wiesel_vertical_tail_kulfan.dat` | `43f596a38e6291726dee681c7b3b50e45faa2f60014f4e1fc1aed48778cebfcf` |
| `rv7/naca23013.5.dat` | `54262966a988b6e3839e035a860e7030fd41b8a4a1bb554ca0a1e93d98baa882` |
| `rv7/naca0015.dat` | `645e867c98ddbc808b315c0c0a672cf390aac23fe32112f83b560efb1b0e7bf9` |
| `rv7/n12.dat` | `82c981d6576fe7793e6657774b2d12ed36c14ec69237a9b72e99dbdbf9d8ddc0` |

BRYAN's sources are under `scripts/canon_checks/reference_fleet/bryan/`; JAGUAR's under
`~/Downloads/da3dalus-import/modelle/jaguar/profile/` (the same files the source JSON names under
`./components/airfoils/`).
CHEKKER's and BELEMNITOS' sources are under `~/Downloads/da3dalus-import/modelle/chekker/profile/`
and `~/Downloads/da3dalus-import/belemnitos/profile/` (BELEMNITOS' `mh32.dat` differs from
`components/airfoils/mh32.dat` in its name line, so the source's file is the copy; the other
`belemnitos_vlw_*.dat` and the CHEKKER files equal those in `components/airfoils/`). WIESEL's
and RV-7's come from `components/airfoils/` of the main checkout (the `wiesel_*_kulfan.dat` files are
untracked there), which is where the DB's airfoil paths point.

## Results recorded for the fleet (regression, not validated)

The goldens in the `test_*_fleet.py` files pin what this build computes (NeuralFoil xlarge, AVL
3.40). Where a formula does not compute for an aircraft, the structured error is the recorded
expected result:

| aircraft | recorded outcome |
|---|---|
| BRYAN, JAGUAR | every formula computes (values in the test files) |
| BELEMNITOS | stall, glide, sink, stall-break and roll-rate compute (the roll in the AeroBuildup world only: AVL's `p'b/2V` is beyond its range, as for BRYAN and JAGUAR). The neutral point is `unsupported_layout`: the surfaces are `main_wing` and `v_tail`. The mass equals the source's, so no `conflicting_mass` is declared. V-tail neutral points come with #1208 |
| RV-7 | clean stall, glide, sink, stall-break and the neutral point compute. The DB gives its flaps no deflection; the flap deflections are the maintainer's guess (take-off 15 deg, landing 30 deg, "guessed, maintainer 2026-10-26"), passed as caller parameters (`FLAP_DEFLECTIONS_DEG` in `reference_fleet.py`). Since #1212 the configured flaps reach AeroBuildup and AVL: `stall-speed-takeoff/-landing` (7.368 / 6.808 m/s, against 6.600 clean; AeroBuildup's flap shifts the lift curve but not C_L,max, so the flapped first peak is lower than the clean one) and the speeds from them are regression values, the roll rate on approach (landing configuration) is the AVL world's value with the AeroBuildup world declared `not_converged` (its flapped curve peaks at C_L 0.651 below the 0.681 the weight needs at V_app). Its export carries no mass, so there is no source mass to conflict with the 0.500 kg |
| CHEKKER | every quantity that builds the AeroSandbox airplane is `unsupported_configuration`: section 0 of the fuselage `Rumpf` has `n_lower != n` (the kernel will take such sections as an equivalent symmetric one: #1307; until then this error is the expected result). The roll rate is `not_applicable` (no aileron) |
| WIESEL | as CHEKKER: section 9 of the fuselage `fuselage` has `n_lower != n` |

The static-margin goldens of the aircraft that compute use the design CG of the canon
(`cg-for-target-margin`: x_cg = x_NP - SM_target c_MAC with SM_target = 0.10, the canon's start
value) taken from the kernel, per neutral-point world; never a hand-chosen position. Where one CG
is needed, it is that of the AVL world. It moves the static margin, never the neutral point.
