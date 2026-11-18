# Published powertrain data (gh-1397)

`powertrain.json` holds component data that a manufacturer or a paper **publishes**, for the tests of
`airplane-components`. Each value has its page and the published wording. Rules:

- Only published values. A field nobody publishes is absent; nothing is estimated or derived (no `R_m` from
  `K_v` and `I_0`, no pack mass from a total).
- Names and units are the catalogue's (`kv_rpm_per_volt`, `rm_ohm`, `io_no_load_a`, ...), so a set maps one to
  one onto `aero_kernel.components.Components`.
- The resistance convention (phase-to-phase or per phase) and the voltage of `I_0` are recorded where the
  source states them; where it does not, that is written down.
- Resistances are all inside roughly 10-300 mOhm (26-95 mOhm among the pages read); a value far outside that
  would be a finding to report, not a value to take.

Read on 2026-11-18. The T-Motor, Scorpion and AXI pages were read through a page-to-markdown fetch (the AXI
sheet through `pdftotext` of the PDF); the wording was taken from that text.

**No motor read here publishes all of Rm, Io, a maximum power and an efficiency.** So no set is complete for
`airplane-components`, which needs every one of them. The tests that need a complete component document
add the missing fields as plainly marked test values; the sets here are used to show the honest failure with
real data. Not verified: Hacker and E-flite pages (named in #1149), the AXI generation of the Esprit table.
