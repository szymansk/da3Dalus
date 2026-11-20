# WP-P7a — Importer, check_canon, Navigator-Build

Self-contained brief for one implementer subagent. Frozen review state: commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

- **Production code under test:** aero_kernel/importer/, scripts/check_canon.py, scripts/build_canon_navigator.py
- **Requirement sources:** ARCHITECTURE §8.9, §8.6
- **Test files you may change:** `aero_kernel/tests/test_importer_approval.py`, `aero_kernel/tests/test_importer_data_sources.py`, `aero_kernel/tests/test_importer_hardening.py`, `aero_kernel/tests/test_importer_stage1.py`, `aero_kernel/tests/test_importer_stage2.py`, `aero_kernel/tests/test_importer_taxonomy.py`, `aero_kernel/tests/test_importer_write.py`, `scripts/tests/test_build_canon_navigator.py`, `scripts/tests/test_check_canon.py`
- **Findings:** 18 (1 high, 10 medium, 7 low)

A finding marked **DECISION** needs the maintainer's answer first: do not write its test, list it in your report as open.

## P7a-F01 · high · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_importer_approval.py` · existing test `test_stage_2_counts_supplied_inputs_with_a_source` (line 90)
- **Production:** `aero_kernel/importer/pipeline.py:45`
- **Gap:** The pipeline may ignore the formula entry's 'status:' completely (every formula reported as draft, no formula ever fully approved in IMPORT_REPORT.md) and no test fails. Stage 1 of the two-stage approval is never tested from the canon document to the report.
- **Evidence:** approval = derive_approval(model_of(result), {"weight-from-mass": "approved"})  -- stage1 is hand-built in every approval test; the golden mini canon has only 'status: draft'. Mutation '_status() -> return "draft"' : 577 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M15:** in `aero_kernel/importer/pipeline.py` line 48: _status: return the entry's status -> always return 'draft'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, in aero_kernel/tests/test_importer_approval.py. Mini canon (importer_builders) with formulas/weight-from-mass.md changed 'status: draft' -> 'status: approved' and quantities/gravity.md given 'data: default:gravity'. result = import_canon(canon). Assert the report line '| weight-from-mass | approved | 2 of 2 |  |' is in result.report (both inputs mapped: aircraft-mass has geometry:total_mass_kg, gravity default:gravity) and that '| weighing | draft |' is still there. Second case: 'status: 5' (not a string) -> row shows 'draft'. Third: a weigh-twice entry set to approved while weight-from-mass stays draft -> its row lists 'embedded: weight-from-mass: not approved'.

## P7a-F02 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_importer_data_sources.py` · existing test `test_the_real_canon_states_the_mass_source_and_the_geometry_check` (line 101)
- **Production:** `aero_kernel/importer/data_sources.py:259`
- **Gap:** A 'consistency:' source that names a location which does not exist (e.g. geometry:total_mas_kg) is accepted without a finding; README: consistency sources are 'validated the same way' as data.
- **Evidence:** assert mass["consistency"] == ["geometry:total_mass_kg"]  -- the only assert on consistency; mutation dropping ("consistency", quantity.consistency) from check_data_sources: 577 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M03:** in `aero_kernel/importer/data_sources.py` line 259: check_data_sources: iterate ('data',) only, consistency sources no longer checked. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_importer_approval.py next to test_a_default_source_must_exist_in_defaults_yaml: mini canon, quantities/ratio.md with 'consistency: default:aircraft-mass' (no such key in defaults.yaml); import_canon(canon, repo_root=tmp_path). Expect exactly one finding 'quantities/ratio.md: consistency: default:aircraft-mass: 'aircraft-mass' is not a key of defaults.yaml'. Add a geometry case against REPO_ROOT: 'consistency: geometry:total_mas_kg' -> finding with field 'consistency' and text "the document has no property 'total_mas_kg'".

## P7a-F03 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_importer_taxonomy.py` · existing test `test_a_group_must_agree_with_its_stage_and_module` (line 264)
- **Production:** `aero_kernel/importer/tag_rules.py:179`
- **Gap:** A quantity whose group belongs to another stage is accepted; only the module half of 'a group that disagrees with its stage or module' is tested.
- **Evidence:** result = run(tmp_path, retag(WEIGHT, "group/air", "stage/early", "module/body")) ... "group 'air' belongs to module 'goals'; this quantity has module 'body'"  -- the stage given equals the group's stage. Mutation removing the ("stage", group.stage, quantity.stage) row: 577 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M02:** in `aero_kernel/importer/tag_rules.py` line 179: _group_agrees: dropped the ('stage', group.stage, quantity.stage) comparison. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_importer_taxonomy.py: add a second stage to FAMILIES ('{id: late, label: Late, explanation: Later.}'), tag weight with group/air, stage/late, module/goals is not possible for a derived quantity (targets only), so declare a second group '{id: wind, label: Wind, explanation: x, stage: early}' without module and tag weight with 'group/wind', 'stage/late'. Expect exactly ["quantities/weight.md: group: group 'wind' belongs to stage 'early'; this quantity has stage 'late'"] (plus adjust point/stage tags so no 'missing' finding appears: weight must be consumed by a formula to be an intermediate, or accept the additional exact findings in the expected list).

## P7a-F04 · medium · missing_requirement_test · DECISION

- **Test file:** `aero_kernel/tests/test_importer_write.py` · no test exists
- **Production:** `aero_kernel/importer/pipeline.py:51`
- **Gap:** ARCHITECTURE 8.9 stage 4 (diff against the committed model, breaking changes marked with affected implementations and golden tests) is neither implemented nor tested: an import that removes an input or changes a unit of an implemented formula is written without any notice.
- **Evidence:** grep -rniE 'breaking' aero_kernel/importer/*.py -> no hit; report.py renders provenance, Appendix A and the approval tables only; cli.main calls import_canon then write_outputs.
- **Status:** READ_ONLY
- **Test to write:** Once stage 4 exists (maintainer decision: build it or strike it from 8.9): fast test in test_importer_write.py. Import the mini canon into out/, then import a canon where formulas/weight-from-mass.md has 'inputs: {m: aircraft-mass}' (g removed) and quantities/weight.md has unit kg. Expect IMPORT_REPORT.md to list 'weight-from-mass' as changed and breaking (inputs) and 'weight' as breaking (unit), an added entry as added/non-breaking, and an unchanged re-import to list no change. If the maintainer strikes stage 4, the test is the traceability test Q11 instead and 8.9 must say so.

## P7a-F05 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_importer_stage1.py` · existing test `test_defaults_with_an_escalated_comment_are_a_finding` (line 360)
- **Production:** `aero_kernel/importer/parse.py:478`
- **Gap:** taxonomy.yaml is the one canon file that is not scanned: an '# ESCALATED:' comment there imports cleanly, and 'holds_targets: yes' is silently read as true, against 8.9 ('imports nothing until the maintainer has decided', 'the canon uses no key or value that YAML 1.1 reads as a boolean').
- **Evidence:** _read_taxonomy has no call of _scan_front_matter (parse.py:478-519). Observed on the unmodified code: mini canon with 'tools:  # ESCALATED: undecided' -> findings [] and a model; with 'holds_targets: yes' -> no finding of field 'yaml'. Tests exist only for entries and defaults.yaml.
- **Status:** READ_ONLY
- **Test to write:** Fast, test_importer_taxonomy.py: (1) taxonomy.yaml = MINI_TAXONOMY with 'tools:  # ESCALATED: undecided' -> exactly one finding ('taxonomy.yaml', 'ESCALATED') and model None. (2) MINI_TAXONOMY + FAMILIES with 'holds_targets: yes' -> one finding ('taxonomy.yaml', 'yaml') naming 'yes'. (3) the same two for rules.yaml (already implemented through _read_slug_map, currently unpinned). The tests will fail until _read_taxonomy scans the text: that is the defect, fix the production code.

## P7a-F07 · medium · missing_requirement_test

- **Test file:** `scripts/tests/test_check_canon.py` · existing test `test_a_statement_finding_fails_the_run` (line 601)
- **Production:** `scripts/check_canon.py:484`
- **Gap:** An ANGLE finding (degrees meet radians without a conversion) may stop failing the run: the verdict is still computed, but nothing pins that it is among the failing classes.
- **Evidence:** assert check_canon.print_statements(check_canon.check_statements(canon)) == 1  (form 'p = b_ref * V_app', a MISMATCH); assert "SCALE" in check_canon.STATEMENT_ERRORS. Mutation removing "ANGLE" from STATEMENT_ERRORS: 82 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M19:** in `scripts/check_canon.py` line 484: STATEMENT_ERRORS without 'ANGLE'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, scripts/tests/test_check_canon.py: canon = _statement_canon(tmp_path, 'p_hat = p * b_ref / (2 * V_app)', ROLL_IN, ROLL_OUT, ROLL_UNITS) (p in deg/s, p_hat dimensionless); assert print_statements(check_statements(canon)) == 1 and 'f [ANGLE] p_hat = p * b_ref / (2 * V_app)' in stdout. Parametrise the same test over one form per class in STATEMENT_ERRORS (MISMATCH, ANGLE, ADDS_UNLIKE 'L = m * g + V', SCALE 'x = x_mm') and assert STATEMENT_ERRORS == ('MISMATCH','ANGLE','ADDS_UNLIKE','SCALE').

## P7a-F08 · medium · missing_edge_case

- **Test file:** `scripts/tests/test_check_canon.py` · existing test `test_a_readme_example_that_drifted_from_its_entry_is_reported` (line 273)
- **Production:** `scripts/check_canon.py:454`
- **Gap:** A README example whose 'kind' or 'tool' (any key outside the fixed machine-readable list) differs from the entry is not reported, although the README promises 'every example above equals the front matter of the entry it names'.
- **Evidence:** _readme_with_example(root, "f", "kind: law\ninputs: {a: speed-a}\n") ... assert any("README" in m and "f" in m and "inputs" in m for m in msgs)  -- every example in the tests has kind equal to the entry's. Mutation 'for key in keys' (example's own keys dropped): 82 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M20:** in `scripts/check_canon.py` line 454: README example check: 'for key in dict.fromkeys([*example, *keys])' -> 'for key in keys'. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, scripts/tests/test_check_canon.py: _canon(tmp_path, quantities=typed_quantities); _readme_with_example(root, 'f', 'kind: fit\ninputs: {a: speed-a, b: speed-b}\noutputs: {v: speed-v}\n') (entry has kind: law). Expect _messages(_errors(root)) == ["README examples: f: kind differs from the entry's front matter"].

## P7a-F09 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · existing test `test_the_data_carries_the_taxonomy` (line 31)
- **Production:** `scripts/build_canon_navigator.py:385`
- **Gap:** The navigator may show every implemented scalar quantity as 'nonscalar' and every curve as 'done' (and likewise mark wrong implementation files): kernel_status runs in the 'built' fixture but none of its outputs is asserted.
- **Evidence:** The only asserts on build() data: taxonomy["modules"] ids, taxonomy tools, quantities[...]["checks"], plausibility(...). Mutation swapping 'done'/'nonscalar': 82 passed. CI's 'build_canon_navigator.py --check' would report the page stale, which leads to regenerating, not to noticing the error.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M22:** in `scripts/build_canon_navigator.py` line 385: kernel_status: 'done' and 'nonscalar' swapped. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, scripts/tests/test_build_canon_navigator.py, on a tiny hand-built data dict (Q: a scalar produced by an implemented formula, a curve produced by an implemented formula, a scalar produced by an unimplemented formula, an input; F with 'out' and 'direction'; edges) and a tmp kernel dir holding one file with @formula("f-done"): call nav.kernel_status(data, tmp_dir) and assert data['status'] == {'q-scalar': 'done', 'q-curve': 'nonscalar', 'q-open': 'open', 'q-in': 'input'} and F['f-done']['impl'] == 'aero_kernel/formulas/<file>.py'. Also: a file with @formula("ghost") -> SystemExit naming ghost.

## P7a-F10 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · no test exists
- **Production:** `scripts/build_canon_navigator.py:373`
- **Gap:** The MVP marking may shrink to the listed MVP results without anything upstream of them (the closure dropped), and no test notices.
- **Evidence:** No test reads data['mvp'] or data['mvp_results']. Mutation 'mvp = set(MVP_RESULTS)': 82 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M26:** in `scripts/build_canon_navigator.py` line 373: kernel_status: mvp = closure(MVP_RESULTS) -> mvp = set(MVP_RESULTS). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Same hand-built fixture as P7a-F09 with edges a -> b -> c and monkeypatched nav.MVP_RESULTS = ('c',): assert data['mvp'] == ['a', 'b', 'c'] and data['mvp_results'] == ['c']. Add nav.closure({'c'}, pred) == {'a','b','c'} as a unit test, with a diamond and a cycle in pred.

## P7a-F11 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · no test exists
- **Production:** `scripts/build_canon_navigator.py:711`
- **Gap:** to_ascii may destroy every non-ASCII character inside <script> (the template has 32 of them) instead of escaping it; the page still counts as pure ASCII.
- **Evidence:** build(): assert all(ord(c) < 128 for c in html)  -- the only check. Mutation replacing the \\uXXXX escape by '?': 82 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M24:** in `scripts/build_canon_navigator.py` line 711: to_ascii: non-ASCII in <script> replaced by '?' instead of \uXXXX. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast unit test of nav.to_ascii: input '<p>\u00e4</p><style>a::before{content:"\u2192"}</style><script>var s="\u03c1";</script>' -> expected exactly '<p>&#228;</p><style>a::before{content:"\\2192 "}</style><script>var s="\\u03c1";</script>'; plus an attribute-bearing tag '<script type="module">' and text after the last block.

## P7a-F12 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · no test exists
- **Production:** `scripts/build_canon_navigator.py:228`
- **Gap:** entry_issues may invert its rule (flag approved entries with a missing source and hide the open ones) without a failing test; to_tex, quantity_notes, application_edges, layout and the marks functions are equally unasserted.
- **Evidence:** No test calls nav.entry_issues or reads the issues of build(). Mutation '!= "approved"' -> '== "approved"': 82 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M25:** in `scripts/build_canon_navigator.py` line 228: entry_issues: source issue only when status != approved -> only when status == approved. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast unit tests of nav.entry_issues on literal entry texts: (a) 'source_status: NO_SOURCE_FOUND', 'status: draft', body '**Source.** none found.' -> [{'kind':'source','title':'No published source found.','text':'none found.'}]; (b) the same with 'status: approved' -> []; (c) 'shape: approximation' draft -> one 'approximation' issue, approved -> none; (d) 'dimensional_check: UNPARSEABLE' -> 'dimensions'; (e) tag 'flag/conflict' with a '## ⚠️ Conflict' section -> 'conflict' with its text; (f) a '> 🔴 **Title**' callout -> 'broken'. Likewise to_tex('V_S = sqrt(2*W/(rho*S_ref*C_L,max))') == r'V_{S} = \sqrt{2\,W/(\rho\,S_{ref}\,C_{L,max})}' and to_tex('argmax ...') is None; application_edges: SystemExit on a self-edge and on model/document mismatch.

## P7a-F13 · low · missing_edge_case

- **Test file:** `scripts/tests/test_check_canon.py` · existing test `test_the_dimensional_check_classifies_each_canonical_form` (line 411)
- **Production:** `scripts/check_canon.py:245`
- **Gap:** The legacy per-formula check may report a millimetre/metre scale difference as BALANCES (informational table only; the per-statement check has its own SCALE tests).
- **Evidence:** assert {f["slug"]: verdict ...} == {"ratio": "BALANCES", ..., "stranger": "UNKNOWN_SYMBOL"}  -- no SCALE, UNPARSEABLE or UNEVALUABLE row. Mutation removing the SCALE branch: 82 passed.
- **Status:** MUTATION_SURVIVED
- **Acceptance mutation P7a-M21:** in `scripts/check_canon.py` line 245: dimensional_rows: removed the SCALE verdict branch. Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Extend _dimensional_canon with a quantity ('distance-mm', 'd_mm', 'mm') and a form 'scaled': ('distance-mm', 'd_mm = V_s * t') -> expected verdict 'SCALE'; add 'broken': ('speed', 'V_s = d /') -> 'UNPARSEABLE'.

## P7a-F14 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_importer_taxonomy.py` · existing test `test_a_final_result_without_a_point_is_a_finding` (line 180)
- **Production:** `aero_kernel/importer/tag_rules.py:118`
- **Gap:** The rule 'an intermediate quantity needs a stage tag' has no negative test on a hand-built canon; it is guarded only because the real canon stops importing when the rule is removed.
- **Evidence:** Probe P7a-M01 (always require 'point') was killed by test_importer_real_canon.py:23 and test_importer_data_sources.py:103, by no test of test_importer_taxonomy.py.
- **Status:** READ_ONLY
- **Acceptance mutation P7a-M01:** in `aero_kernel/importer/tag_rules.py` line 118: _places: ('stage','an intermediate quantity') if consumed else ('point', ...) -> always ('point','a final result'). Today all tests stay green; after your change at least one test must fail under this mutation.
- **Test to write:** Fast, test_importer_taxonomy.py: in complete(), aircraft... make 'weight' an intermediate by adding a formula that binds it (e.g. formulas/weight-user.md: inputs {w: weight}, outputs {x: weight-user}, quantity weight-user tagged point/cruise + discipline/forces) and tag weight with discipline/forces only. Expect exactly ['quantities/weight.md: stage: missing: an intermediate quantity needs a stage tag'].

## P7a-F15 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_importer_write.py` · existing test `test_importing_twice_is_byte_identical` (line 58)
- **Production:** `aero_kernel/importer/rules.py:336`
- **Gap:** Determinism is asserted within one process only; an output that depended on set iteration order (hash seed) would pass every determinism test and fail the golden test only sporadically.
- **Evidence:** first, second = import_canon(CANON), import_canon(CANON); assert (first.model_json, first.report) == (second.model_json, second.report)  -- same interpreter, same PYTHONHASHSEED. (A manual run with PYTHONHASHSEED 0..3 over the mini canon gave identical bytes, so no defect today.)
- **Status:** READ_ONLY
- **Test to write:** Fast, test_importer_write.py: run 'python -m aero_kernel.importer <canon> --out <dir_i>' in two subprocesses with env PYTHONHASHSEED=1 and PYTHONHASHSEED=2 (cwd = repository root) and compare the bytes of canon_model.json and IMPORT_REPORT.md; a third case imports a canon that yields several rule findings (with_area_user of test_importer_rules.py) and compares stdout across the two seeds.

## P7a-F16 · low · untested_error_path

- **Test file:** `aero_kernel/tests/test_importer_write.py` · existing test `test_a_failing_write_leaves_the_old_files_and_no_temporary_file` (line 99)
- **Production:** `aero_kernel/importer/write.py:53`
- **Gap:** Only os.replace failures are simulated. A failure while writing the second temporary file (disk full during write, mkstemp refusing) is the case the 'finally' cleanup exists for and has no test.
- **Evidence:** monkeypatch.setattr(os, "replace", refuse)  -- in all three failure tests.
- **Status:** READ_ONLY
- **Test to write:** Fast, test_importer_write.py: after a good import into out/, monkeypatch tempfile.mkstemp so that the second call raises OSError('disk full'); main([...changed canon..., '--out', out]) == 1; both output files byte-identical to before; sorted(out.iterdir()) == [REPORT, MODEL] (the first temp file is removed); stderr contains 'nothing written'.

## P7a-F17 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_importer_hardening.py` · existing test `test_a_quantity_slug_must_be_kebab_case` (line 315)
- **Production:** `aero_kernel/importer/assemble.py:126`
- **Gap:** Three tests carry an 'or' branch that reduces an exact comparison to something much weaker, so the finding's field (and for the abscissa test its file and field) is not pinned.
- **Evidence:** assert [(f.file, f.field) for f in result.findings] == [(FROM_MASS, "outputs.w")] or any(f.file == FROM_MASS for f in result.findings)   |   test_importer_abscissa.py:43: assert message == (...) or ("abscissa ghost is no quantity of the canon" in message)   |   test_importer_hardening.py:926: assert all("Mass" not in other for other in rest) or rest == []
- **Status:** READ_ONLY
- **Test to write:** Replace each by the exact list the importer produces today (run once, read, then pin): e.g. assert shown(result) == [f"{FROM_MASS}: outputs.w: String should match pattern ... (got 'calc:Weight')"] with the real text; for the abscissa test assert the full 'quantities/profile.md: <field>: abscissa ghost is no quantity of the canon'.

## P7a-F18 · low · coverage_only

- **Test file:** `aero_kernel/tests/test_importer_stage2.py` · existing test `test_a_bare_embed_of_a_single_application_formula_names_its_application` (line 517)
- **Production:** `aero_kernel/importer/normalise.py:282`
- **Gap:** The test would pass whatever the embed is normalised to.
- **Evidence:** assert result.model is not None
    assert result.model.formula("weigh-twice") is not None
- **Status:** READ_ONLY
- **Test to write:** Assert twice.embeds == ('calc:weight-from-mass.default', 'calc:weighing.clean'), or merge the test into test_an_explicit_default_embed_equals_the_bare_one (test_importer_hardening.py:382), which already pins the same behaviour by model equality.

## P7a-F19 · low · missing_edge_case

- **Test file:** `aero_kernel/tests/test_importer_stage1.py` · existing test `test_stage_1_finding` (line 241)
- **Production:** `aero_kernel/importer/parse.py:104`
- **Gap:** The outcome for a byte-order mark, a tab and CRLF line ends in an entry is not pinned (observed today: BOM -> 'no front matter between '---' lines', tab -> 'invalid YAML', CRLF accepted).
- **Evidence:** STAGE_1_CASES has 'no front matter', 'invalid yaml', 'unterminated front matter'; none with '\ufeff', '\t' or '\r\n'.
- **Status:** READ_ONLY
- **Test to write:** Three STAGE_1_CASES rows on quantities/gravity.md: text prefixed with '\ufeff' -> ('front matter', 'no front matter') (or, if the maintainer wants a BOM tolerated, a clean import); 'symbol:\tg' -> ('front matter', 'invalid YAML'); and a separate test that the entry rewritten with '\r\n' imports to the same content_hash as the '\n' version.
