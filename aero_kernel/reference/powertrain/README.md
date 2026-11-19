# Published powertrain data (gh-1397)

`powertrain.json` holds component data that a manufacturer or a paper **publishes**, for the tests of
`airplane-components`. Each value in `fields` has its page (a URL) and the published wording. Rules:

- Only published values, as the very quantity of the catalogue field. A value that is **derived** (the
  per-cell voltage from the pack voltage), or whose **rating kind** is not that of the field (a 180 s maximum
  power, a continuous power, a bare "25c" label), is not in `fields`: it stands beside them under
  `not_adopted` with its wording and the reason.
- A field nobody publishes is absent; nothing is estimated (no `R_m` from `K_v` and `I_0`, no pack mass from a
  total).
- Names and units are the catalogue's (`kv_rpm_per_volt`, `rm_ohm`, `io_no_load_a`, ...), so a set maps one to
  one onto `aero_kernel.components.Components`.
- The resistance convention (phase-to-phase or per phase) and the voltage of `I_0` are recorded where the
  source states them; where it does not, that is written down.
- The canon does not judge a resistance (ADR 0028); the tests only require `rm_ohm > 0`.

Read on 2026-11-18. The T-Motor, Scorpion and AXI pages were read through a page-to-markdown fetch (the AXI
sheet through `pdftotext` of the PDF); the wording was taken from that text.

**No set is complete for `airplane-components`**, which needs every field it reads. The tests that need a
complete component document add the missing fields (efficiency 80 %, maximum power 650 W, pack mass 560 g,
C-rate 25, cell voltage 3.7 V) as plainly marked **test values**, not published data of any part (see
`aero_kernel/tests/components_builders.py`); the sets here are used to show the honest failure with real data.
Not verified: Hacker and E-flite pages (named in #1149), the AXI generation of the Esprit table.

## The propeller table (gh-1411)

`apc_13x8e.json` is the performance table of the APC 13x8E (the Avistar Elite's propeller), shaped as
`aero_kernel.components.PropellerTable`: 18 rpm blocks (1000 to 18000 rpm), per block 29 or 30 points of the advance
ratio `J`, `C_T` and `C_P`. It is APC's own PER3 performance file `PER3_13x8E.dat`
(https://www.apcprop.com/files/PER3_13x8E.dat, file version v2022-0915), trimmed to those three columns. The numbers were
taken from the repository's snapshot `data/cots/apc_props.json.gz`, which was parsed from that file by
`scripts/parse_apc_props.py`; the file itself was not downloaded again. The data are **computed by APC, not measured in
a wind tunnel** (the file's header says so); they are a published table, not a validation of the propeller's real
performance. `tests/test_propeller_reference.py` checks the shape, the source and that every point equals the snapshot.
