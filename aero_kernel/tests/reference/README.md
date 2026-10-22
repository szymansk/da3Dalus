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

## Additions to the JSON (the only differences from the source)

`surface_type` (ARCHITECTURE 8.5, D9) on every wing, inserted after `name`. The role follows the
function (conventional layout): `Tragflaeche` is `main_wing`, `Hoehenleitwerk` is
`horizontal_tail`, `Seitenleitwerk` is `vertical_tail`, for both aircraft. Assigned from the wing
names, not computed; the app-side migration is #1187.

## Airfoil files (byte-identical copies)

| file | SHA-256 |
|---|---|
| `bryan/bryan_profil.dat` | `75fc1827fb3059c6525464032b3a9c95f48c1205ef513750fd34532ebb69eb62` |
| `bryan/bryan_platte.dat` | `d221c31868aa05d295488b2286f66352406fe6b8649084bc98fb8737bd414595` |
| `jaguar/jaguar_test_da3dalus_export__tragflaeche_kulfan.dat` | `51eadb6d6121bd31cacfb08dead004223142b4f665eedc90e273953af4b92755` |
| `jaguar/jaguar_test_da3dalus_export__hoehenleitwerk_kulfan.dat` | `b902ac2c03d07c19921cbdaf522a4bd47aacf2c6d7f7c7365b8065856ba06003` |
| `jaguar/jaguar_test_da3dalus_export__seitenleitwerk_kulfan.dat` | `9a24aa95dc458b6c5a67965ad97a3797dc638ad06ec76250f8b4dbae651d8cb6` |

BRYAN's sources are under `scripts/canon_checks/reference_fleet/bryan/`; JAGUAR's under
`~/Downloads/da3dalus-import/modelle/jaguar/profile/` (the same files the source JSON names under
`./components/airfoils/`).
