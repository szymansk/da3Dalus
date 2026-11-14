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

### The plan batch (#1372)

The 28 plan models of the maintainer's plugin batch 2026-11-05 (DB ids 99 to 126, reconstructed from
real building plans) were exported the same way, on 2026-11-08, against a copy of `db/test.db` made
with `sqlite3 .backup` (`db/test.db` was not written). By then the app states the `surface_type` of
every wing (#1187) and the `role` of every body (#1355) itself, so the export carries both and the
copies carry **no** addition: each copy is its source. As for WIESEL and RV-7, the export serves the
spar dimensions in millimetres and `total_mass_kg` as `null` (#1147); the copies keep the spar fields
verbatim (no solver reads them) and the tests pass the mass as a value. The masses were settled with
the maintainer on 2026-11-07 and equal the DB's `aeroplanes.total_mass_kg` since then.

| model | DB id | copy | SHA-256 of the raw export | SHA-256 of the source as canonical JSON | mass | source of the mass |
|---|---|---|---|---|---|---|
| A6M2_ZERO | 99 | `a6m2_zero/a6m2_zero.airplane.json` | `5ba48fc6f5ac1869f353fb76398e9efa360d8f8c3013ab045aaa0f24ef093f7e` | `68bff8aa9958e8ee5c0f936cc78576ac6a4a430d3746c9cb560bc37468832123` | 0.36 kg | DB value; the six 0.75 m warbirds share dimensions, equal mass accepted as consistent (maintainer) |
| AERONCA_CHAMP | 100 | `aeronca_champ/aeronca_champ.airplane.json` | `3c974aa4baff4c0308d2c3022ce092fb1b96da9b8511650193fe9998eab927e9` | `fb26cd7b3b16b837bd6ad5e35c3b26cee78e3e90225e9329fa4d66f40d315fca` | 0.39 kg | RC parkflyer: median wing loading of comparable models of the RC-Network table x S (accepted by the maintainer) |
| ALBATROS_4 | 101 | `albatros_4/albatros_4.airplane.json` | `95cefc65ec642040655daf1a433ec91225ceaae0cb5fc86e47aa4c01162bd395` | `c6e29d57f6d2c8ab1da3916323d29b0a725f2e8456811d34af6c52f338375026` | 5.0 kg | DB, unverified (from the plugin, not confirmed) |
| BARRACUDA | 102 | `barracuda/barracuda.airplane.json` | `b313f595c8506583773ace37297779e6cb4394e4b32463ab74a4ac31efea49f1` | `6938594724c24320375b7bd388d99b3ae842159e5d2bc47c7a79f303bfe42d58` | 1.54 kg | slope glider: median wing loading of comparable models of the RC-Network table x S (accepted by the maintainer) |
| BF109_E | 103 | `bf109_e/bf109_e.airplane.json` | `8ddf1b5dc2cef9decce99da5ba22a0d4dcf49818a117f7145f801d093bef33ac` | `a285c94a9f1ad455a949f2056dad1fdcc765fad42b0afd16d4a92e78e36bb886` | 0.36 kg | DB value; the six 0.75 m warbirds share dimensions, equal mass accepted as consistent (maintainer) |
| D520_DEWOITINE | 104 | `d520_dewoitine/d520_dewoitine.airplane.json` | `297c6048bda161332b780d7d2b5fef0fdc02992a86012758030530f1af299072` | `6ade3b0b673d3501abf5f92d2155e1ddcfd8c94aaccec82f6a473086c9fd102f` | 0.36 kg | DB value; the six 0.75 m warbirds share dimensions, equal mass accepted as consistent (maintainer) |
| DARDO | 105 | `dardo/dardo.airplane.json` | `f87d948c34ee09379b688d85994e0be0983e2e60f18ad7deb31c8e213423e6e6` | `17e4f522c175448470d843aea3c0039d6e7680ed6d729d2696f882831f206431` | 1.35 kg | DB, unverified (from the plugin, not confirmed) |
| ESTRELA | 106 | `estrela/estrela.airplane.json` | `c7991271094d3dfde5162e8a7dea8bbd2d154c2a19a35b7907293ac3636d8321` | `f82a8550724dc81c91ac7c0c845cc13f427a584010b098e54631f918d3c03477` | 1.7 kg | plan, ~74 g/dm2, confirmed by the maintainer |
| EXTRA_300_EP | 107 | `extra_300_ep/extra_300_ep.airplane.json` | `ceb5e536dcf7da253dacee7a0bdfe961916740f8c099a98da8c013160d694cc3` | `cda24eeb81ecc7c84ee8a5a8a8db63366fd5b9fde3ef4727ef1d5a3e55a79e85` | 0.75 kg | DB, unverified (from the plugin, not confirmed) |
| F3A_COMPETICION | 108 | `f3a_competicion/f3a_competicion.airplane.json` | `68ad557be34a1d9fcba05bf6401436797a0ab3926140441dc25ce0830f0f6534` | `7c44d960180bc82cf87fc823a4950172ea23fb314e3951a9d8ec64b716a2e275` | 4.7 kg | DB, unverified (from the plugin, not confirmed); its ~70 g/dm2 was raised as a question and is not answered |
| FORCE_5 | 109 | `force_5/force_5.airplane.json` | `bcc34f8323499b58acc34b19356f8786a0d25c1524173ee846a72f9a2e4b8324` | `5a4cda0c4023db7481a24381a21a8fc4e55b7416848d303018ac1f639cc6b0df` | 1.22 kg | DB, unverified (from the plugin, not confirmed) |
| FORCE_FOUR | 110 | `force_four/force_four.airplane.json` | `c5c39e26e7458ec18911bf498d5270654717ca1a751907cd0defcc14ff8059c7` | `2bf10ca4b23c32b3564645415ad3d2dc9a53af3726643b8286ace55f8e052d0f` | 0.68 kg | DB, unverified (from the plugin, not confirmed) |
| FW190_A8 | 111 | `fw190_a8/fw190_a8.airplane.json` | `fd17ce3660f925812f10b6e050461fce417c62104c6ce06a8bbe3be58fc450b4` | `1e14ba92cac62d4c5912d5b831e287b6e1d7b86aabf7515407a7644f8f902da9` | 0.35 kg | DB value; the six 0.75 m warbirds share dimensions, equal mass accepted as consistent (maintainer) |
| GEE_BEE_R3 | 112 | `gee_bee_r3/gee_bee_r3.airplane.json` | `c766e53511183824cb8f83a81481d2ea1bbdc325265e4e6e2947244b1ca0f101` | `4d6fa0e7d4c1f1eae7d4d8a565f0c4419b9a7d08323fc602d3652c7ed396ce5f` | 12.0 kg | plan: estimated dry weight 26-27 lb (maintainer); fuel not added |
| KASTAWAY | 113 | `kastaway/kastaway.airplane.json` | `9e32c61126ab46a55953affe863154b12d96d8268edce21ebc9ec9e07ae49e47` | `44f36fc31904967273527e86ad316b5c4820533cd16d4ce4acbd5e6cf3ac17d3` | 0.65 kg | RE glider: median wing loading of comparable models of the RC-Network table x S (accepted by the maintainer) |
| MILES_MAGISTER | 114 | `miles_magister/miles_magister.airplane.json` | `564001bdb08899de04827380d62964b0cfd0b675a229cea612635185bd6e6740` | `8e5c45ee9484cb18244e7bf8ad4cb20afc1650956d2a68203ace8de733cce329` | 0.36 kg | DB value; the six 0.75 m warbirds share dimensions, equal mass accepted as consistent (maintainer) |
| MINI_FUNTANA | 115 | `mini_funtana/mini_funtana.airplane.json` | `07c04dede17c578ff77b8ea63ff74be2d3edd0e6c446fd6e49080db1000bded2` | `0c1f02282c382b4b4b76abea1c30a195ada281e6a4656e12e6ec6b4d91462ed5` | 0.539 kg | DB, unverified (from the plugin, not confirmed) |
| P36_HAWK | 116 | `p36_hawk/p36_hawk.airplane.json` | `f3cde7e17511d40df411220684084f210b813b5fdc46c087e664841fcd448f21` | `45b0854f9d56d8cb11e1664b8e10518061b7a7526ef5e3be87de1069ab7464b5` | 0.36 kg | DB value; the six 0.75 m warbirds share dimensions, equal mass accepted as consistent (maintainer) |
| P39 | 117 | `p39/p39.airplane.json` | `0f0f8eae1682b2feaaf3a934267f6189a011f2b5d26c1450712fd0a43f657db5` | `bc099584d33f10b6f3d0c939d73ddc4dbd21de3afea8bb78ac97c434a72a594e` | 9.5 kg | median wing loading of comparable models of the RC-Network table x S (accepted by the maintainer) |
| SNOOPY | 118 | `snoopy/snoopy.airplane.json` | `17255588bf298fe7a616ce648994e198aa33386c6ffb53c1ce593e221e14a7f3` | `c02bd4b1f6b082670d8fb08f62aae1fefee6564e868691ba4e3c6de85fece627` | 1.474 kg | DB, unverified (from the plugin, not confirmed) |
| SONAS_40 | 119 | `sonas_40/sonas_40.airplane.json` | `7ae2641c148da17720cbd6430e43e7426c07de36207f4ad952e7e671890655f4` | `73a4af4ecf0ca96849a40d0d01c16459d76b9d6aca44fe03932f043c51e15842` | 2.1 kg | median wing loading of comparable models of the RC-Network table x S (accepted by the maintainer) |
| SPIRIT_100 | 120 | `spirit_100/spirit_100.airplane.json` | `0dbabc165ddbd47031d063ca1b360ffe3813cda3db7c7297f7b6fa523c11f1b2` | `2a78862b02e9d495c4fd75c5c4207c7a7822ad096ec1041aa33adb9111731a37` | 1.26 kg | median wing loading of comparable models of the RC-Network table x S (accepted by the maintainer) |
| SPRITE | 121 | `sprite/sprite.airplane.json` | `aa4ed847e6cf1de0a1acdd396a619c5083dbaa4d61bcffc48cba0458bb7c6911` | `93f4f22972e2379e129b88e5af90f79a6ca4d7f94a371c3eff600a21963512da` | 1.0 kg | basic RC aerobatic, 1.5 cc diesel (maintainer); median 53 g/dm2 of the 1.5 cc models of about 1 m of the RC-Network table (Bronco, Race Rat, Amateur II, Auster Aiglet, Amateur) x 19.0 dm2 |
| SUPER_TRIDENT | 122 | `super_trident/super_trident.airplane.json` | `67df09772adfd25b13cc20c0b84b5cd9569965775ead13c2c68ac96d4dbafa03` | `58687c7004680f61099811430075d27a4e5d275d2386fbb95ad137274c26b6d0` | 1.05 kg | DB, unverified (from the plugin, not confirmed) |
| ULTRA_MINI_STICK | 123 | `ultra_mini_stick/ultra_mini_stick.airplane.json` | `0713d43c3ecf23e2818e31f892a5cf66bf44143a9f435b0a51143b4e0e6a0b31` | `8fd656a65a27e34fbaacdea5c5bb7c29cb43749e53b523f2c362bc0670d0b057` | 0.35 kg | DB, unverified (from the plugin, not confirmed) |
| VOODOO | 124 | `voodoo/voodoo.airplane.json` | `2bda5ead168160ec35664489677999876c6cb3303e3706f7b92408fada2690d5` | `b10bb0ef0b2b9b0290254e341f8c675062a5789f1e92c7851d31e025224c5945` | 1.16 kg | no weight in plan or article (A. Searl, Radio Modeller 7/1971, 69.5 in tailless slope glider, no motor); median 21.5 g/dm2 of the unpowered flying wings of the RC-Network comparison table (Slowing, Little Big Wing, Hot Shot, Chinook, Geier, Solo) x 54.1 dm2 |
| WINDFREAK | 125 | `windfreak/windfreak.airplane.json` | `fe813b25fb2171b878c626f5d8ef70af1d7bd74bb4df872de591d434c98b4145` | `42ffcf810fd42b1f560db9b4920945772e3ea79fb0a15f348bc850df614feb31` | 2.6 kg | no weight on the plan; median 28.8 g/dm2 of the plank flying wings of the RC-Network table x 90.7 dm2 |
| WRISTOCRAT | 126 | `wristocrat/wristocrat.airplane.json` | `7ab0dcb459db3b3ca6991d1e845ed3b4b9a7986b668a9e77efae0446d059e263` | `f51ea5f344750d13d4f216075c7abfe1b2a6656ca93326f67576c64680fa5fce` | 0.34 kg | DB, unverified (from the plugin, not confirmed) |

The surface types are the DB's: a horizontal and a vertical tail, except ALBATROS_4 and BARRACUDA
(`v_tail`, 37.5 and 45 deg from the horizontal, root to tip leading edge), the flying wings VOODOO and WINDFREAK (a main
wing and a fin, no pitch surface) and WINDFREAK's `tip_plate` (`winglet`, the canted plate at the
tip). The bodies named `canopy` (A6M2_ZERO, BF109_E, D520_DEWOITINE, EXTRA_300_EP, F3A_COMPETICION,
FW190_A8, P36_HAWK), AERONCA_CHAMP's `equipment_box` and D520_DEWOITINE's `radiator` carry the
role `fuselage` without attachment in the DB, so the solvers see them as bodies of their own (no
canopy merge). Several vertical tails start with a zero chord at the root rib; that is the DB's
geometry too.

The DB's CHEKKER is not used: its fin has 48 ribs against the source's 12 and its wings and airfoil
files carry other names; the source file is the better document.

### The validation aircraft (#1388, #1392)

AVISTAR_ELITE is the Great Planes Avistar Elite of the UAVDB project, one of the two aircraft of the
fleet with published measurements (see `avistar_elite/MEASUREMENTS.md`). It exists neither in the app DB
nor as a plan: its source is the generator
`scripts/canon_checks/reference_fleet/avistar_elite/build_document.py`, which names the origin of
every number, and `test_a_validation_copy_is_what_its_generator_builds` checks that the copy is what
the generator builds.

| | AVISTAR_ELITE |
|---|---|
| copy | `avistar_elite/avistar_elite.airplane.json` |
| SHA-256 of the copy as canonical JSON | `14bbbf2fef893b850f31fc67041ea76df3b5a898c34f6acf8fc014b5ad118593` |
| mass | 3.70 kg, gross weight of [P] Table 1 (3.07 kg empty + 0.63 kg battery) |
| reference point | `xyz_ref` (0.4644, 0, 0) m: the manual's balance point, see the assumptions |

Sources: **[P]** Dantsker, Caccamo, Vahora, Mancuso, "Flight & Ground Testing Data Set for an
Unmanned Aircraft: Great Planes Avistar Elite", AIAA 2020-0780
(https://cs-people.bu.edu/rmancuso/files/papers/UAVDB_Avistar_AIAAScitech20.pdf); **[M]** Great
Planes, Avistar Elite instruction manual GPMA1005
(http://manuals.hobbico.com/gpm/gpma1005-manual.pdf).

Published and taken as is:

- Wing, horizontal and vertical stabiliser: leading-edge position, span station, chord, offset and
  dihedral of [P] Table 4, measured on a 3D scan (x towards the tail, y towards the right wing, z
  up, the same axes as the format); the incidence of the wing and of the horizontal stabiliser. The
  fin's "y span pos" is the height above its root.
- Wing airfoil AVISTAR ([P]: verified against the UIUC Airfoil Database; the file is that
  database's `avistar.dat`).
- Control-surface chords from [M] p. 29: each throw is given as a length at the trailing edge,
  measured at the widest part of the surface, and an angle, so chord = throw / sin(angle): aileron
  50 mm, elevator 41 mm, rudder 58 mm. The stops are the manual's high rates (17, 16 and 22 deg).

Assumptions, because no source publishes the value:

| value | assumed | why it matters |
|---|---|---|
| aileron span | from 400 mm to 770 mm of the 793.75 mm half span | the roll rate |
| control-surface chord along the span | the chord at the widest part ([M]) over the whole span | roll rate, control power |
| fin incidence | 0 deg; [P] Table 4 prints 2.36 deg in the fin's row, the stabiliser's value, taken as a copying slip | side force at zero sideslip |
| flaps | not modelled: every published test flew with 0 deg ([P] section V); span and throw are unpublished | none for the published tests |
| tail airfoils | NACA 0006 for both stabilisers ([P] Figure 8 only plots the thin symmetric sections, which vary from root to tip) | tail lift slope and drag, weakly |
| fuselage | twelve sections read off [P] Figures 4 and 5 (about +-5 mm), superellipse exponent 4 | drag, the body's share of the neutral point |
| centre of gravity | the manual's balance point, 84 mm behind the leading edge ([M]), at z = 0 of the scan; [P] does not publish the tested aircraft's and no source gives a height | the measured static margin |
| landing gear, propeller, spinner | not modelled | drag |

The wing area of the document is 37.6 dm2 (2 x 793.75 mm x 237.1 mm, the scan). [P] Table 1 gives
an aspect ratio of 6.62, which with its 1.59 m span means 38.2 dm2, close to the scan (6.70); the
43.3 dm2 that [P] Table 1 and [M] state fit neither. The scan is used.

ULTRA_STICK_120 is the Hangar 9 Ultra Stick 120, the kit NASA Langley flew and tested at full scale
in its 12-foot tunnel as FASER and the University of Minnesota flies as a research aircraft (see
`ultra_stick_120/MEASUREMENTS.md`). Its source is the generator
`scripts/canon_checks/reference_fleet/ultra_stick_120/build_document.py`.

| | ULTRA_STICK_120 |
|---|---|
| copy | `ultra_stick_120/ultra_stick_120.airplane.json` |
| SHA-256 of the copy as canonical JSON | `ff3d0523a6b829e178ba2548c1c2a4f30d018d6b51a15b1dec8475cc7ff38cd3` |
| mass | 8.95 kg (19.72 lbf, [F] Table 2) |
| reference point | `xyz_ref` (0.3020, 0, 0.0714) m: [F] Table 2, a quarter of the 1.42 ft chord behind the leading edge, 0.165 of it above the bottom of the fuselage |
| origin | x from the kit firewall aft, z from the flat bottom of the fuselage up |

Sources: **[A]** Jim Feldmann, "Ultra Stick LW - A Modified Hangar 9 Ultra Stick", RCM February
2002, pp. 100-114 (the table of dimensions on p. 101; the conversion to a low wing leaves wing,
stabiliser and elevator "just as they come"); **[L]** RCM plan no. 1307 of that article (Outerzone
oz13447, https://outerzone.co.uk/plan_details.asp?ID=13447), a side view at full size, measured on
the bitmap at 72 points per inch and checked on the plan's own scale bar; **[F]** Owens, Cox,
Morelli, "Development of a Low-Cost Sub-Scale Aircraft for Flight Research: The FASER Project", NASA
NTRS 20060022541 (2006), Tables 1 and 2. Plan and article are not copied into the repository.

Published, or measured on the plan:

- [A]: wing span 76 in, wing area 1214 in2, symmetrical section, dihedral 1 in at each tip;
  stabiliser span 28-3/4 in, chord with elevator 11-1/4 in, area 302 in2, flat section.
- [L]: the outline of the kit fuselage (flat bottom, sloping top, 52.0 in from the firewall to the fin
  post; [F] gives 4.31 ft), the positions of wing and stabiliser, the outline of fin and rudder with
  the hinge line, the wing's thickness (2.54 in) and the place where the aileron starts (14.2 in
  behind the leading edge). All incidences are zero ("0-0" on the plan, 0 deg in [F]).
- [F]: mass, centre of gravity, the greatest width of the fuselage (0.3958 ft).

An independent check: the University of Minnesota (Jaeger et al., AIAA 2026-4164, Table 2) gives for
its Ultra Stick 120 the leading edges of wing, stabiliser and fin 0.666 ft, 3.708 ft and 3.375 ft
behind the firewall and tail areas of 2.06 ft2 and 0.718 ft2. The plan gives 0.636 ft, 3.677 ft and
3.25 ft (the fin at the stabiliser plane), [A] 2.10 ft2 for the stabiliser, and fin with rudder
measure 0.69 ft2 from the stabiliser plane up on the plan.

Assumptions:

| value | assumed | why it matters |
|---|---|---|
| wing planform | constant chord = area / span = 15.97 in. [A] says "slight taper" and an average chord of 16-3/4 in, which with 76 in is 1273 in2, not its own 1214 in2; [F] gives taper ratio 1, 8.28 ft2 and 6.29 ft (a mean of 15.8 in) and a mean geometric chord of 1.42 ft | area, aspect ratio, every coefficient |
| wing section | NACA 0015; the drawn section is 15.9 % thick with its thickest point at 22 % of the chord, not 30 % | maximum lift, stall angle |
| aileron | from 19 in to 37 in of the 38 in half span; the kit has an inboard flap and an outboard aileron of unpublished spans | roll rate |
| flaps | not modelled | none at 0 deg |
| stabiliser planform | straight taper with an unswept trailing edge, tip chord 9.76 in from span, root chord and area | tail lift slope, weakly |
| elevator | a third of the root chord, constant | control power |
| tail sections | NACA 0006 for the flat plates (0.5 in thick on [L]) | tail lift slope and drag, weakly |
| fin | from the stabiliser plane to its top as outlined on [L]; its lowest inch lies beside the aft fuselage | side force, weathercock stability |
| fuselage width | the greatest width of [F] from the firewall to the wing's hinge line, narrowing in a straight line to 1 in at the fin post; superellipse exponent 4 | drag, the body's share of the neutral point |
| deflection stops | none: [A] gives throws as lengths only | none |
| engine, landing gear, propeller | not modelled | drag |
| same kit | that NASA's and Minnesota's aircraft are the kit of [A] and [L]; the positions above agree within 0.4 in (the fin within 1.5 in) | everything |

With exponent 10 for the box-shaped body and its open front face the kernel's best-glide optimisation
returned NaN; exponent 4 is used and the cause is not investigated here.

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
| A6M2_ZERO | 0.747 m | 9.5 dm2 | 0.134 m | 37 N/m2 | 0.9e5 |
| AERONCA_CHAMP | 0.906 m | 12.9 dm2 | 0.146 m | 30 N/m2 | 1.0e5 |
| ALBATROS_4 | 4.065 m | 113.1 dm2 | 0.294 m | 43 N/m2 | 2.0e5 |
| BARRACUDA | 2.457 m | 40.2 dm2 | 0.164 m | 38 N/m2 | 1.1e5 |
| BF109_E | 0.749 m | 9.6 dm2 | 0.134 m | 37 N/m2 | 0.9e5 |
| D520_DEWOITINE | 0.747 m | 9.5 dm2 | 0.134 m | 37 N/m2 | 0.9e5 |
| DARDO | 1.928 m | 36.9 dm2 | 0.196 m | 36 N/m2 | 1.3e5 |
| ESTRELA | 1.018 m | 23.2 dm2 | 0.227 m | 72 N/m2 | 1.6e5 |
| EXTRA_300_EP | 1.041 m | 19.2 dm2 | 0.190 m | 38 N/m2 | 1.3e5 |
| F3A_COMPETICION | 1.949 m | 67.6 dm2 | 0.373 m | 68 N/m2 | 2.6e5 |
| FORCE_5 | 2.528 m | 57.2 dm2 | 0.230 m | 21 N/m2 | 1.6e5 |
| FORCE_FOUR | 1.553 m | 18.0 dm2 | 0.118 m | 37 N/m2 | 0.8e5 |
| FW190_A8 | 0.750 m | 9.6 dm2 | 0.134 m | 36 N/m2 | 0.9e5 |
| GEE_BEE_R3 | 2.640 m | 128.7 dm2 | 0.517 m | 91 N/m2 | 3.5e5 |
| KASTAWAY | 1.500 m | 24.4 dm2 | 0.167 m | 26 N/m2 | 1.1e5 |
| MILES_MAGISTER | 0.749 m | 8.2 dm2 | 0.112 m | 43 N/m2 | 0.8e5 |
| MINI_FUNTANA | 0.940 m | 21.0 dm2 | 0.228 m | 25 N/m2 | 1.6e5 |
| P36_HAWK | 0.764 m | 9.5 dm2 | 0.133 m | 37 N/m2 | 0.9e5 |
| P39 | 2.335 m | 100.6 dm2 | 0.459 m | 93 N/m2 | 3.1e5 |
| SNOOPY | 3.202 m | 59.7 dm2 | 0.191 m | 24 N/m2 | 1.3e5 |
| SONAS_40 | 1.417 m | 36.4 dm2 | 0.259 m | 57 N/m2 | 1.8e5 |
| SPIRIT_100 | 2.554 m | 61.5 dm2 | 0.245 m | 20 N/m2 | 1.7e5 |
| SPRITE | 0.991 m | 19.0 dm2 | 0.193 m | 52 N/m2 | 1.3e5 |
| SUPER_TRIDENT | 2.533 m | 42.2 dm2 | 0.168 m | 24 N/m2 | 1.1e5 |
| ULTRA_MINI_STICK | 0.831 m | 15.0 dm2 | 0.186 m | 23 N/m2 | 1.3e5 |
| VOODOO | 1.764 m | 54.1 dm2 | 0.321 m | 21 N/m2 | 2.2e5 |
| WINDFREAK | 2.493 m | 90.7 dm2 | 0.365 m | 28 N/m2 | 2.5e5 |
| WRISTOCRAT | 1.456 m | 21.3 dm2 | 0.148 m | 16 N/m2 | 1.0e5 |
| AVISTAR_ELITE | 1.588 m | 37.6 dm2 | 0.237 m | 96 N/m2 | 1.6e5 |
| ULTRA_STICK_120 | 1.931 m | 78.3 dm2 | 0.406 m | 112 N/m2 | 2.8e5 |

The first six are in the regime: a 0.5 to 1.5 m RC model at 5 to 20 m/s has a chord Reynolds number of
0.5e5 to 2.5e5 and a Mach number below 0.06. The RV-7 is an RC scale model (0.82 m span, MAC
0.183 m), not the 7.0 m aeroplane the name suggests. Its tail chords (rudder tip 0.080 m,
elevator tip 0.076 m) fall below the 7e4 bubble-sensitive line at 10 m/s, as BRYAN's do; the
kernel says so in its warnings.

The plan batch spans 0.75 to 4.1 m and 16 to 93 N/m2; its MAC Reynolds numbers at 10 m/s lie between
0.8e5 and 3.5e5 (GEE_BEE_R3, MAC 0.517 m), and stay below 1e6 up to about 28 m/s for the largest MAC.
At the C_L 1.4 stall estimate the horizontal tails of BF109_E, D520_DEWOITINE, FW190_A8 and
WRISTOCRAT fall below 3e4 (`test_regime_fleet.py`).

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

No aircraft of the first six has a canard, twin fins or winglets; of the plan batch, WINDFREAK has
a winglet (see above).

`role` and `attached_to` (format 7.6, #1355) on BRYAN's body `Haube`, inserted after `name`:
`"role": "canopy"`, `"attached_to": "Rumpf"`. `Haube` is the canopy on `Rumpf` (its x range
0.134 to 0.238 m lies inside the fuselage's, its lower edge at the fuselage's top z = 0.027 m, its
half-width that of the fuselage). The marking is done by hand and explicitly, for slice 2 (the
canopy merge, canon rule `canopy-merge`): since then the solvers see one merged body instead of
the fuselage and the whole canopy, and BRYAN's goldens moved (before/after in the PR of #1355
slice 2). No other aircraft of the first six has a canopy body; every other body keeps the default
role `fuselage` without attachment. The plan batch's canopies are bodies of role `fuselage` in the
DB (see above); they are not marked.

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
| `a6m2_zero/a6m2_zero_main_wing_kulfan.dat` | `ef3def7c95da5cacac76714c3997e3e3c90ba4e1799057beb9386d2cd5228f3b` |
| `a6m2_zero/a6m2_zero_horizontal_tail_kulfan.dat` | `59f3e2994f5edcd758e606735aaf560af8bc867c8a316c15da69374b7e42ae8e` |
| `a6m2_zero/a6m2_zero_vertical_tail_kulfan.dat` | `52a2cf69950a36fe06879bc3d1f50c9450702994debb558bc24b9788bb4e399e` |
| `aeronca_champ/aeronca_champ_main_wing_kulfan.dat` | `a04ad110eb8205f034f273a05e1049c552bd4a7e56d25c48cddcb14e7860697e` |
| `aeronca_champ/aeronca_champ_horizontal_tail_kulfan.dat` | `c5e1bd2672b27fee18476eda3dc905e0f302021e46aae18967a0dbaa48314f72` |
| `aeronca_champ/aeronca_champ_vertical_tail_kulfan.dat` | `ecddd48808e3027a34fd63aa5777bae6c7aa9e1806a90e55fcd6391513decbda` |
| `albatros_4/sd7037.dat` | `58dc2b375e8c96c4b2ad7acd2968de9d69334ec80c656da10a022981e470784f` |
| `albatros_4/albatros_4_v_tail_kulfan.dat` | `f2d83d6cb4907b688acafd5d1e9e7f569f49697effb18e0f64e395d6da1cad01` |
| `barracuda/barracuda_main_wing_kulfan.dat` | `99daaf9a65e34c4aa416de90a42cd73e00a32ad367cc661f1f4f9467f8234b25` |
| `barracuda/barracuda_v_tail_kulfan.dat` | `56737465686a728ac459688eaa652ee80f3d8807c516ac2ad42abb0804052aa1` |
| `bf109_e/bf109_e_main_wing_kulfan.dat` | `5f4b6d902b4495b6ed1d5afa1cfbcec1d23d66d9269d657f709acf4dd78549a3` |
| `bf109_e/bf109_e_horizontal_tail_kulfan.dat` | `d2ea328bc26738140d555155807f52d8cc25ce3f0093858f8f1e3b08d439bb7e` |
| `bf109_e/bf109_e_vertical_tail_kulfan.dat` | `2edb28ddf0cb1894cf1879937f175957a63d9084c71a4983709aed3294149abe` |
| `d520_dewoitine/d520_dewoitine_main_wing_kulfan.dat` | `48645ca42c612c0fd153c2d4aa02fd9d188b3b1b886ba48fee3adf9de246b85f` |
| `d520_dewoitine/d520_dewoitine_horizontal_tail_kulfan.dat` | `235e3dce2f7e70458886081e3ec7f4f1a85e7360b04317149d890ace502ad08f` |
| `d520_dewoitine/d520_dewoitine_vertical_tail_kulfan.dat` | `0a659002364927c8b720db9bc2d5038677391bef620a6d401307b63742d65c24` |
| `dardo/naca2410.dat` | `3f523e19178b501a0a19b07871299277a2fd9f39e47d8f08ce955949ec3c5c2d` |
| `dardo/naca0006.dat` | `b4393d8fc137a5915778896ba5111c7672afd12c84058d62361f79e4a645cd4d` |
| `dardo/dardo_vertical_tail_kulfan.dat` | `f7b5444985f1257584f3e6300b01dcbba270ef367b62229299b7183c169f6f4c` |
| `estrela/estrela_main_wing_kulfan.dat` | `354876e2c46083b09268fcd837a1d429dd40d91ecaec3a62515970c4fff4a125` |
| `estrela/estrela_horizontal_tail_kulfan.dat` | `6c2eb133fb1255cc00eff99c179888d564b8e282a469bc48e3aba541cda7a86a` |
| `estrela/estrela_vertical_tail_kulfan.dat` | `7a34c2eb2f6bf9a47f438009f2da843110ae2f155f390cc9589fe700243139ac` |
| `extra_300_ep/extra_300_ep_main_wing_kulfan.dat` | `414a36af9620cfc9fa081fd0f07c5384cfaaafbfe7a578c65231de7d59efb88b` |
| `extra_300_ep/extra_300_ep_horizontal_tail_kulfan.dat` | `a2d03425322374516e901410ee7ff833eea3f399cd93c6dc399bdaba85435fba` |
| `extra_300_ep/extra_300_ep_vertical_tail_kulfan.dat` | `88031b4d388269ea9a114a58a268c99d2995334f961a95fe35fb840a00455c4f` |
| `f3a_competicion/f3a_competicion_main_wing_kulfan.dat` | `a3e6a0e0ed3a36743d037731439bfb37f87f13ca23027e3fedafed91d852a1d2` |
| `f3a_competicion/f3a_competicion_horizontal_tail_kulfan.dat` | `11560244f92b1b77ede210d9030c17a8ee29f957408595973678f63d83e3a8cf` |
| `f3a_competicion/f3a_competicion_vertical_tail_kulfan.dat` | `4cfcbbd58657e5c6d3215c3aa51bb8d650326221b7f72db03698ed4b5dc458fe` |
| `force_5/force_5_main_wing_kulfan.dat` | `9c4641c18aae7022ef8e3b3958d84b6732184825564cb43456f12bae8f9a3729` |
| `force_5/force_5_horizontal_tail_kulfan.dat` | `8619716d5b5d5a977c149754d3d871785fde48180ba4dc8b3fc58365e99310e6` |
| `force_5/force_5_vertical_tail_kulfan.dat` | `16f9d8279f1d519f6c604cb4182108d2ec081d274a983cc067d1dfb19ca6670c` |
| `force_four/force_four_main_wing_kulfan.dat` | `fea8bc0d0afd08faf247b28dcacd57f4d808b30cf3d18a1337fae44c4bfb1bbd` |
| `force_four/force_four_horizontal_tail_kulfan.dat` | `0cb52bf19c7e8989bd7ed7d75ee9b6028ce47bccff0830a4d702027c69373bcb` |
| `force_four/bryan_platte.dat` | `d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595` |
| `fw190_a8/fw190_a8_main_wing_kulfan.dat` | `80a570b28d44422200b18855c77033a3a0d018091f6fc217ec24dceb0a96cb18` |
| `fw190_a8/fw190_a8_horizontal_tail_kulfan.dat` | `1a684258caeac32caa56ef8c27fdff231349ab958f52ce8e5a9abbd8bc719476` |
| `fw190_a8/fw190_a8_vertical_tail_kulfan.dat` | `6dbe0ff203b1b540e4b70dadff1b95f020eba3017a3193b4ea6c59e51a81f6e6` |
| `gee_bee_r3/gee_bee_r3_main_wing_kulfan.dat` | `737ea33e71f217056f6d38db2e5e0872f3463bd9c7848c0eac671e9b12a5b84f` |
| `gee_bee_r3/gee_bee_r3_horizontal_tail_kulfan.dat` | `547def8bcc18fb3e1f80eff92efd25f47d0d21ac61c0a5a435c0b2a843cb4409` |
| `gee_bee_r3/gee_bee_r3_vertical_tail_kulfan.dat` | `52b984b883089760a823ffac2c37a26665ecf9af86d3d4066a6d11f7ea92038b` |
| `kastaway/kastaway_main_wing_kulfan.dat` | `016c8743003ea2fefce2f831b4071de53d79b576588f956928b2c21093549ccc` |
| `kastaway/kastaway_horizontal_tail_kulfan.dat` | `3f99d4fc4b51534f008928bf7c75e5b78ecf03947f71053379251adb2f536b00` |
| `kastaway/kastaway_vertical_tail_kulfan.dat` | `a9acf1c0c67c6605a312eaa90313972cf45eb2a1b1089afc1c28ce65edf7063e` |
| `miles_magister/miles_magister_main_wing_kulfan.dat` | `bbe7f91f9e0b6929ff7d27a2cd5f24c615e9d77bfc7087a9753a3642f34f4eef` |
| `miles_magister/bryan_platte.dat` | `d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595` |
| `miles_magister/miles_magister_vertical_tail_kulfan.dat` | `f19a080a6a946da400db3bfc088c6f913e033d071af071fd71b15aa517788d67` |
| `mini_funtana/mini_funtana_main_wing_kulfan.dat` | `5bcf54cb7549ee6521ecf9121d8804fbb73508dae6e60a409a13fe8d6ce19794` |
| `mini_funtana/mini_funtana_horizontal_tail_kulfan.dat` | `c23a38823b551ac620ae10375974daec2f504cdf61963fe4be563c03c495f51f` |
| `mini_funtana/bryan_platte.dat` | `d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595` |
| `p36_hawk/p36_hawk_main_wing_kulfan.dat` | `9dff6c273fddb0adb104ec7954c3a2a3f993549e7ca731ded8dfa48d52fce483` |
| `p36_hawk/p36_hawk_horizontal_tail_kulfan.dat` | `3a90eab9ecfcd36c13c6c7945c284eda9c36557480fcfa292595e7ce16765867` |
| `p36_hawk/bryan_platte.dat` | `d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595` |
| `p39/p39_main_wing_kulfan.dat` | `a607da7ce2b6c2f45c2ca4a5b33e22626302a75dc2f3d1b2afb9f30bf9ec0e5a` |
| `p39/naca0210.dat` | `b2d9e2c90465517cfec859a5b6aceac28ce5cb22280f15aa51725bc6f56e7695` |
| `snoopy/snoopy_main_wing_kulfan.dat` | `55d83bcc143f19334c8cd57eee403d2c818f5caf149ee0dd499ebf6d6f5e1cb9` |
| `snoopy/naca0008.dat` | `e1fc6db22dd2d270076bc625274608aee674fae367f537d4f47019742c1ff276` |
| `snoopy/snoopy_vertical_tail_kulfan.dat` | `0d230f5b0e6a376b521452708398557ed700d4348266c964582e50bfc444b9f7` |
| `sonas_40/sonas_40_main_wing_kulfan.dat` | `9c4084c87f2b7df9a5062287701069329e6bcbe4f72f2d259ebbd547faa30a2a` |
| `sonas_40/sonas_40_horizontal_tail_kulfan.dat` | `1c5b71c917763b81a078746f9328cc6cbb61c79f93140e9ffbf397eb9c8b065c` |
| `sonas_40/sonas_40_vertical_tail_kulfan.dat` | `4c824abf832f736bd9d53108f3739f95ab60674eeb291af16a0395f750a15142` |
| `spirit_100/spirit_100_main_wing_kulfan.dat` | `39a88d985a692acfe9b84cce5470ed8521bb737e6ecaee7fe5c4185f6c4301aa` |
| `spirit_100/spirit_100_horizontal_tail_kulfan.dat` | `d134507b09ef64c97a38cbdfd682c4c27c82673cf55c173e546e17525ad3d045` |
| `spirit_100/spirit_100_vertical_tail_kulfan.dat` | `6ac6d51b39a9842f37471f55e98f15337944af2c21216602a655bc8c95d999bc` |
| `sprite/sprite_main_wing_kulfan.dat` | `e0767394202405d782f3848f6b590a40db0d719fd831ec11ca376e7fc4b5305c` |
| `sprite/sprite_horizontal_tail_kulfan.dat` | `3b2fd6af37c100a79f0ca985fef53779a928d2b98353ee03ae29291aed32d39e` |
| `sprite/sprite_vertical_tail_kulfan.dat` | `f222fe14f364432adcd10a9178ad62ce0267c5ad85d945d69c175df6d6c759a3` |
| `super_trident/super_trident_main_wing_kulfan.dat` | `a545907391d544c56d71980b30a953b2e0f307d0baeab1b148defdb2fdd4093e` |
| `super_trident/super_trident_horizontal_tail_kulfan.dat` | `9e980a193e51791966d02e04e48e3ffe7b5ca66414b43e186ea7099a99aac98d` |
| `super_trident/super_trident_vertical_tail_kulfan.dat` | `91dcd89a35b7742486f28c08cbabb18c397ebeed6dd698c732f71e148637c4c9` |
| `ultra_mini_stick/e168_15.dat` | `48f7e73386ab23a1e6b0e939e1dd02db5109851452dbe54e9270ce460031ba26` |
| `ultra_mini_stick/ultra_mini_stick_horizontal_tail_kulfan.dat` | `31ba99893f126a27c0db01d9fc53b14df1c20c5f87785618df09cd78fcf8d63b` |
| `ultra_mini_stick/ultra_mini_stick_vertical_tail_kulfan.dat` | `b3c696002c0058d9808fe5b73b53d9beb2ef2557dbb619549ba8ca1fdae06a05` |
| `voodoo/voodoo_main_wing_kulfan.dat` | `5d8eb98e2d854f630e7eb2c1f1fa4aa63b8da42d53aae311c1c63ca28be00e9b` |
| `voodoo/voodoo_vertical_tail_kulfan.dat` | `05a7348f12f0793b6aa9bb5292c80aeb4192f4111d6df7ddcfdf0504d334ec14` |
| `windfreak/windfreak_main_wing_kulfan.dat` | `62915d86a07f05ee990e52e0aa7ae6e853a80b41789a3c2114cd8da51b72ce7f` |
| `windfreak/windfreak_vertical_tail_kulfan.dat` | `201c0c7336bb29f14ae46cdd39041f9b5722d21a6dd04792d122ee7dc89718ac` |
| `windfreak/windfreak_tip_plate_kulfan.dat` | `94a0e79400b95365a6bfc4ffb6278e48931916d3a136e4526c7613e987a09275` |
| `wristocrat/wristocrat_main_wing_kulfan.dat` | `17668189add6b04dcb08b9689f6005b6d7bcf2a153b1393b8c0c8cf5f2901081` |
| `wristocrat/wristocrat_horizontal_tail_kulfan.dat` | `7e1ed736e3cb914e6af2079157a3b1202260d47e600c570a3652a378b44a88d2` |
| `wristocrat/wristocrat_vertical_tail_kulfan.dat` | `285c7673e2e8e19fad721c09abb99a26ae47ac2f9388c23bdc72ad56cca9993f` |
| `avistar_elite/avistar.dat` | `b71d63826ada136382d26bb4df7954cefce0b2f49ca5910c16c13d6ddb48dce5` |
| `avistar_elite/naca0006.dat` | `b4393d8fc137a5915778896ba5111c7672afd12c84058d62361f79e4a645cd4d` |
| `ultra_stick_120/naca0015.dat` | `645e867c98ddbc808b315c0c0a672cf390aac23fe32112f83b560efb1b0e7bf9` |
| `ultra_stick_120/naca0006.dat` | `b4393d8fc137a5915778896ba5111c7672afd12c84058d62361f79e4a645cd4d` |

BRYAN's sources are under `scripts/canon_checks/reference_fleet/bryan/`; JAGUAR's under
`~/Downloads/da3dalus-import/modelle/jaguar/profile/` (the same files the source JSON names under
`./components/airfoils/`).
CHEKKER's and BELEMNITOS' sources are under `~/Downloads/da3dalus-import/modelle/chekker/profile/`
and `~/Downloads/da3dalus-import/belemnitos/profile/` (BELEMNITOS' `mh32.dat` differs from
`components/airfoils/mh32.dat` in its name line, so the source's file is the copy; the other
`belemnitos_vlw_*.dat` and the CHEKKER files equal those in `components/airfoils/`). WIESEL's
and RV-7's come from `components/airfoils/` of the main checkout (the `wiesel_*_kulfan.dat` files are
untracked there), which is where the DB's airfoil paths point. The plan batch's come from the same
place (the plugin's `*_kulfan.dat` files and `e168_15.dat` are untracked there; `bryan_platte.dat`,
`naca0006.dat`, `naca0008.dat`, `naca0210.dat`, `naca2410.dat` and `sd7037.dat` are tracked). AVISTAR_ELITE's
`avistar.dat` is https://m-selig.ae.illinois.edu/ads/coord/avistar.dat (UIUC Airfoil Database,
fetched 2026-11-14) and its `naca0006.dat` is `components/airfoils/naca0006.dat`. ULTRA_STICK_120's two files are
`components/airfoils/naca0015.dat` and `naca0006.dat`.

## Results recorded for the fleet (regression, not validated)

The goldens in the `test_*_fleet.py` files pin what this build computes (NeuralFoil xlarge, AVL
3.40). Where a formula does not compute for an aircraft, the structured error is the recorded
expected result:

| aircraft | recorded outcome |
|---|---|
| BRYAN, JAGUAR | every formula computes (values in the test files) |
| BELEMNITOS | stall, glide, sink, stall-break and roll-rate compute (the roll in the AeroBuildup world only: AVL's `p'b/2V` is beyond its range, as for BRYAN and JAGUAR). The neutral point computes since #1208 (the V-tail is the horizontal tail with `S_h,eff = sum S_i cos^2(nu_i)` and the true panel aspect ratio; regression values in the test files); the AVL neutral-point mesh is declared not converged (`avl_mesh_not_converged`, 1.27 % MAC against the 0.5 % tolerance). It has ailerons, so the turn sideslip and the rudder roll authority are `not_applicable`. The mass equals the source's, so no `conflicting_mass` is declared |
| RV-7 | clean stall, glide, sink, stall-break and the neutral point compute. The DB gives its flaps no deflection; the flap deflections are the maintainer's guess (take-off 15 deg, landing 30 deg, "guessed, maintainer 2026-10-26"), passed as caller parameters (`FLAP_DEFLECTIONS_DEG` in `reference_fleet.py`). Since #1212 the configured flaps reach AeroBuildup and AVL: `stall-speed-takeoff/-landing` (7.368 / 6.808 m/s, against 6.600 clean; AeroBuildup's flap shifts the lift curve but not C_L,max, so the flapped first peak is lower than the clean one) and the speeds from them are regression values, the roll rate on approach (landing configuration) is the AVL world's value with the AeroBuildup world declared `not_converged` (its flapped curve peaks at C_L 0.651 below the 0.681 the weight needs at V_app). Its export carries no mass, so there is no source mass to conflict with the 0.500 kg |
| CHEKKER | 37 of the 48 fuselage sections of `Rumpf` have `n_lower != n`; the kernel takes each as the equivalent symmetric section of equal cross-section area (#1307) and declares it per section (`fuselage_section_equivalent`). Stall, glide, sink, stall-break, the neutral point and the tail arms compute (regression values in the test files). The AVL neutral-point mesh is declared not converged (`avl_mesh_not_converged`, 0.55 % MAC against the 0.5 % tolerance). The roll rate is `not_applicable` (no aileron) |
| WIESEL | 46 of the 61 fuselage sections of `fuselage` have `n_lower != n`; as CHEKKER, with the same quantities computed and the AVL mesh converged. The inverted stall `inverted-max-lift-coefficient` is `not_converged` (the sweep has no trough, as for BRYAN). The roll rate is computed in the AeroBuildup world only (AVL's `p'b/2V` = 0.258 is beyond its range); NeuralFoil's lowest analysis confidence at the deflected strips is 0.028 (Re of the main wing from 170 to 1.1e5) |
| plan batch (28, #1372) | one compute per aircraft in `test_plan_batch_fleet.py` (stall, glide, sink, neutral point, design CG, roll rate on approach and the lateral chain of `test_mvp_chain_fleet.py`, at SM_target 0.10 and an aileron deflection of 20 deg); the golden is the value, or `not_applicable`, or the error with its causes. Every aircraft gives V_S, V_md, (L/D)max and V_mp except AERONCA_CHAMP, whose stall is `not_converged` (the optimum lies on the alpha bound, 5 deg), so its approach quantities are `upstream_failed`. VOODOO and WINDFREAK (flying wings) have no neutral point (`unsupported_layout`: one main wing with one horizontal tail or V-tail) and everything after it fails upstream. ALBATROS_4, GEE_BEE_R3, P39 and SPIRIT_100 have flaps without a deflection, so the approach (landing configuration) is `upstream_failed` (`airplane-landing` `missing_input`). MINI_FUNTANA's AVL lateral runs give no derivatives and come back `internal` (bug #1373). The aircraft without an aileron have no roll rate (`not_applicable`); five declare the AVL neutral-point mesh as not converged (BARRACUDA, DARDO, FORCE_FOUR, SNOOPY, SPIRIT_100) |

The static-margin goldens of the aircraft that compute use the design CG of the canon
(`cg-for-target-margin`: x_cg = x_NP - SM_target c_MAC with SM_target = 0.10, the canon's start
value) taken from the kernel, per neutral-point world; never a hand-chosen position. Where one CG
is needed, it is that of the AVL world. It moves the static margin, never the neutral point.
