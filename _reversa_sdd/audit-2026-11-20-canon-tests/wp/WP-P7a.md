# WP-P7a — Importer, check_canon, navigator build

Self-contained brief for one implementer subagent. Base commit `72c4b5c6`. Read `../README.md` section „Regeln für alle Arbeitspakete“ first; it is binding.

Every finding below was checked by an independent verifier on 2026-11-21 (`../rework/`). The line **Verified** says how. Where **Correction** appears, it overrides the text under **Test to write**.

- **Production code under test:** aero_kernel/importer/, scripts/check_canon.py, scripts/build_canon_navigator.py
- **Requirement sources:** ARCHITECTURE §8.9, §8.6
- **Test files you may change:** `aero_kernel/tests/test_importer_approval.py`, `aero_kernel/tests/test_importer_data_sources.py`, `aero_kernel/tests/test_importer_hardening.py`, `aero_kernel/tests/test_importer_taxonomy.py`, `aero_kernel/tests/test_importer_write.py`, `scripts/tests/test_build_canon_navigator.py`, `scripts/tests/test_check_canon.py`
- **Findings to work on:** 13 (0 high, 9 medium, 4 low)

## P7a-F01 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_importer_approval.py` · existing test `test_stage_2_counts_supplied_inputs_with_a_source` (line 90)
- **Production:** `aero_kernel/importer/pipeline.py:45`
- **Gap:** The pipeline may ignore the formula entry's 'status:' completely (every formula reported as draft, no formula ever fully approved in IMPORT_REPORT.md) and no test fails. Stage 1 of the two-stage approval is never tested from the canon document to the report.
- **Evidence:** approval = derive_approval(model_of(result), {"weight-from-mass": "approved"})  -- stage1 is hand-built in every approval test; the golden mini canon has only 'status: draft'. Mutation '_status() -> return "draft"' : 577 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. The mutation is observable: on the unmodified code a mini canon with weight-from-mass 'status: approved' and gravity 'data: default:gravity' renders the report row '| weight-from-mass | approved | 2 of 2 |  |'; the committed real IMPORT_REPORT.md has rows like '| aerobuildup-evaluation | approved | 6 of 6 |  |' that would all read 'draft'. Every approval test hand-builds stage 1: `approval = derive_approval(model_of(result), {"weight-from-mass": "approved"})`.
- **Verifier's note:** No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F01.patch` (from the audit folder; aero_kernel/importer/pipeline.py:48  `return status if isinstance(status, str) else "draft"` -> `return "draft"`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, in aero_kernel/tests/test_importer_approval.py. Mini canon (importer_builders) with formulas/weight-from-mass.md changed 'status: draft' -> 'status: approved' and quantities/gravity.md given 'data: default:gravity'. result = import_canon(canon). Assert the report line '| weight-from-mass | approved | 2 of 2 |  |' is in result.report (both inputs mapped: aircraft-mass has geometry:total_mass_kg, gravity default:gravity) and that '| weighing | draft |' is still there. Second case: 'status: 5' (not a string) -> row shows 'draft'. Third: a weigh-twice entry set to approved while weight-from-mass stays draft -> its row lists 'embedded: weight-from-mass: not approved'.

## P7a-F02 · medium · missing_requirement_test

- **Test file:** `aero_kernel/tests/test_importer_data_sources.py` · existing test `test_the_real_canon_states_the_mass_source_and_the_geometry_check` (line 101)
- **Production:** `aero_kernel/importer/data_sources.py:259`
- **Gap:** A 'consistency:' source that names a location which does not exist (e.g. geometry:total_mas_kg) is accepted without a finding; README: consistency sources are 'validated the same way' as data.
- **Evidence:** assert mass["consistency"] == ["geometry:total_mass_kg"]  -- the only assert on consistency; mutation dropping ("consistency", quantity.consistency) from check_data_sources: 577 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. Unmodified code reports "quantities/ratio.md: consistency: default:aircraft-mass: 'aircraft-mass' is not a key of defaults.yaml"; under the mutation the import is clean. The only assert on consistency in the tests is `assert mass["consistency"] == ["geometry:total_mass_kg"]`.
- **Verifier's note:** No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F02.patch` (from the audit folder; aero_kernel/importer/data_sources.py:259  `(("data", quantity.data), ("consistency", quantity.consistency))` -> `(("data", quantity.data),)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_importer_approval.py next to test_a_default_source_must_exist_in_defaults_yaml: mini canon, quantities/ratio.md with 'consistency: default:aircraft-mass' (no such key in defaults.yaml); import_canon(canon, repo_root=tmp_path). Expect exactly one finding 'quantities/ratio.md: consistency: default:aircraft-mass: 'aircraft-mass' is not a key of defaults.yaml'. Add a geometry case against REPO_ROOT: 'consistency: geometry:total_mas_kg' -> finding with field 'consistency' and text "the document has no property 'total_mas_kg'".

## P7a-F03 · medium · missing_edge_case

- **Test file:** `aero_kernel/tests/test_importer_taxonomy.py` · existing test `test_a_group_must_agree_with_its_stage_and_module` (line 264)
- **Production:** `aero_kernel/importer/tag_rules.py:179`
- **Gap:** A quantity whose group belongs to another stage is accepted; only the module half of 'a group that disagrees with its stage or module' is tested.
- **Evidence:** result = run(tmp_path, retag(WEIGHT, "group/air", "stage/early", "module/body")) ... "group 'air' belongs to module 'goals'; this quantity has module 'body'"  -- the stage given equals the group's stage. Mutation removing the ("stage", group.stage, quantity.stage) row: 577 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. Unmodified code, with a second stage 'late' and a group 'wind' of stage 'early', reports "quantities/weight.md: group: group 'wind' belongs to stage 'early'; this quantity has stage 'late'"; under the mutation nothing. The one existing test gives the group's own stage: `result = run(tmp_path, retag(WEIGHT, "group/air", "stage/early", "module/body"))`.
- **Verifier's note:** No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F03.patch` (from the audit folder; aero_kernel/importer/tag_rules.py:179  row `("stage", group.stage, quantity.stage),` removed from _group_agrees). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, test_importer_taxonomy.py: add a second stage to FAMILIES ('{id: late, label: Late, explanation: Later.}'), tag weight with group/air, stage/late, module/goals is not possible for a derived quantity (targets only), so declare a second group '{id: wind, label: Wind, explanation: x, stage: early}' without module and tag weight with 'group/wind', 'stage/late'. Expect exactly ["quantities/weight.md: group: group 'wind' belongs to stage 'early'; this quantity has stage 'late'"] (plus adjust point/stage tags so no 'missing' finding appears: weight must be consumed by a formula to be an intermediate, or accept the additional exact findings in the expected list).

## P7a-F07 · medium · missing_requirement_test

- **Test file:** `scripts/tests/test_check_canon.py` · existing test `test_a_statement_finding_fails_the_run` (line 601)
- **Production:** `scripts/check_canon.py:484`
- **Gap:** An ANGLE finding (degrees meet radians without a conversion) may stop failing the run: the verdict is still computed, but nothing pins that it is among the failing classes.
- **Evidence:** assert check_canon.print_statements(check_canon.check_statements(canon)) == 1  (form 'p = b_ref * V_app', a MISMATCH); assert "SCALE" in check_canon.STATEMENT_ERRORS. Mutation removing "ANGLE" from STATEMENT_ERRORS: 82 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. Unmodified code: print_statements returns 1 for 'p_hat = p * b_ref / (2 * V_app)' and prints '    f [ANGLE] p_hat = p * b_ref / (2 * V_app)'; print_statements filters by `failing = [r for r in rows if r.verdict in STATEMENT_ERRORS]`, so the mutated run returns 0. The existing tests pin the ANGLE verdict (`("p_hat = p * b_ref / (2 * V_app)", "ANGLE") in _verdicts(canon)`) but the exit value only for a MISMATCH.
- **Verifier's note:** No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F07.patch` (from the audit folder; scripts/check_canon.py:484  `STATEMENT_ERRORS = ("MISMATCH", "ANGLE", "ADDS_UNLIKE", "SCALE")` -> `("MISMATCH", "ADDS_UNLIKE", "SCALE")`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, scripts/tests/test_check_canon.py: canon = _statement_canon(tmp_path, 'p_hat = p * b_ref / (2 * V_app)', ROLL_IN, ROLL_OUT, ROLL_UNITS) (p in deg/s, p_hat dimensionless); assert print_statements(check_statements(canon)) == 1 and 'f [ANGLE] p_hat = p * b_ref / (2 * V_app)' in stdout. Parametrise the same test over one form per class in STATEMENT_ERRORS (MISMATCH, ANGLE, ADDS_UNLIKE 'L = m * g + V', SCALE 'x = x_mm') and assert STATEMENT_ERRORS == ('MISMATCH','ANGLE','ADDS_UNLIKE','SCALE').

## P7a-F08 · medium · missing_edge_case

- **Test file:** `scripts/tests/test_check_canon.py` · existing test `test_a_readme_example_that_drifted_from_its_entry_is_reported` (line 273)
- **Production:** `scripts/check_canon.py:454`
- **Gap:** A README example whose 'kind' or 'tool' (any key outside the fixed machine-readable list) differs from the entry is not reported, although the README promises 'every example above equals the front matter of the entry it names'.
- **Evidence:** _readme_with_example(root, "f", "kind: law\ninputs: {a: speed-a}\n") ... assert any("README" in m and "f" in m and "inputs" in m for m in msgs)  -- every example in the tests has kind equal to the entry's. Mutation 'for key in keys' (example's own keys dropped): 82 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. 'kind' is not in EXAMPLE_KEYS_FORMULA, so only the example's own keys bring it into the comparison; unmodified code reports "README examples: f: kind differs from the entry's front matter" for an example with 'kind: fit', the mutated code nothing. Existing drift test: `_readme_with_example(root, "f", "kind: law\ninputs: {a: speed-a}\n")` keeps kind equal to the entry.
- **Verifier's note:** No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F08.patch` (from the audit folder; scripts/check_canon.py:454  `for key in dict.fromkeys([*example, *keys]):` -> `for key in keys:`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, scripts/tests/test_check_canon.py: _canon(tmp_path, quantities=typed_quantities); _readme_with_example(root, 'f', 'kind: fit\ninputs: {a: speed-a, b: speed-b}\noutputs: {v: speed-v}\n') (entry has kind: law). Expect _messages(_errors(root)) == ["README examples: f: kind differs from the entry's front matter"].

## P7a-F09 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · existing test `test_the_data_carries_the_taxonomy` (line 31)
- **Production:** `scripts/build_canon_navigator.py:385`
- **Gap:** The navigator may show every implemented scalar quantity as 'nonscalar' and every curve as 'done' (and likewise mark wrong implementation files): kernel_status runs in the 'built' fixture but none of its outputs is asserted.
- **Evidence:** The only asserts on build() data: taxonomy["modules"] ids, taxonomy tools, quantities[...]["checks"], plausibility(...). Mutation swapping 'done'/'nonscalar': 82 passed. CI's 'build_canon_navigator.py --check' would report the page stale, which leads to regenerating, not to noticing the error.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. The real build has status counts done 122, nonscalar 8, open 8, input 32, so the swap changes 130 quantities on the page. No test in scripts/tests or aero_kernel/tests/test_canon_navigator_*.py reads data['status'] or F[...]['impl'] (grep for kernel_status in the tests: no hit).
- **Verifier's note:** No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F09.patch` (from the audit folder; scripts/build_canon_navigator.py:385  `"done" if d["type"] in ("scalar", "airplane") else "nonscalar"` -> `"nonscalar" if ... else "done"`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast, scripts/tests/test_build_canon_navigator.py, on a tiny hand-built data dict (Q: a scalar produced by an implemented formula, a curve produced by an implemented formula, a scalar produced by an unimplemented formula, an input; F with 'out' and 'direction'; edges) and a tmp kernel dir holding one file with @formula("f-done"): call nav.kernel_status(data, tmp_dir) and assert data['status'] == {'q-scalar': 'done', 'q-curve': 'nonscalar', 'q-open': 'open', 'q-in': 'input'} and F['f-done']['impl'] == 'aero_kernel/formulas/<file>.py'. Also: a file with @formula("ghost") -> SystemExit naming ghost.

## P7a-F10 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · no test exists
- **Production:** `scripts/build_canon_navigator.py:373`
- **Gap:** The MVP marking may shrink to the listed MVP results without anything upstream of them (the closure dropped), and no test notices.
- **Evidence:** No test reads data['mvp'] or data['mvp_results']. Mutation 'mvp = set(MVP_RESULTS)': 82 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. On the real canon data['mvp'] has 25 quantities for 6 MVP results, so the mutation drops 19 marked quantities. The only 'mvp' in the navigator tests is the stub `{"Q": {}, "F": {}, "edges": [], "order": {}, "inputs": [], "outputs": [], "mvp": []}`.
- **Verifier's note:** Shares the fixture and the function with P7a-F09 but needs its own assert; not a duplicate. No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F10.patch` (from the audit folder; scripts/build_canon_navigator.py:373  `mvp = closure(set(MVP_RESULTS), pred)` -> `mvp = set(MVP_RESULTS)`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Same hand-built fixture as P7a-F09 with edges a -> b -> c and monkeypatched nav.MVP_RESULTS = ('c',): assert data['mvp'] == ['a', 'b', 'c'] and data['mvp_results'] == ['c']. Add nav.closure({'c'}, pred) == {'a','b','c'} as a unit test, with a diamond and a cycle in pred.

## P7a-F11 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · no test exists
- **Production:** `scripts/build_canon_navigator.py:711`
- **Gap:** to_ascii may destroy every non-ASCII character inside <script> (the template has 32 of them) instead of escaping it; the page still counts as pure ASCII.
- **Evidence:** build(): assert all(ord(c) < 128 for c in html)  -- the only check. Mutation replacing the \\uXXXX escape by '?': 82 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. The template's script blocks hold 32 non-ASCII characters (counted), each of which the mutation turns into '?'. No test calls to_ascii or asserts anything about the escaped page (grep for to_ascii and 'ord(c) < 128' in scripts/tests and aero_kernel/tests: no hit).
- **Verifier's note:** The reviewer's evidence quote `assert all(ord(c) < 128 for c in html)` is in no test file (grep), so not even the pure-ASCII property is pinned; the gap is wider than stated, the verdict is unchanged. No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F11.patch` (from the audit folder; scripts/build_canon_navigator.py:711  `"\\u%04x" % ord(c)` -> `"?"` in to_ascii, kind 'script'). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast unit test of nav.to_ascii: input '<p>\u00e4</p><style>a::before{content:"\u2192"}</style><script>var s="\u03c1";</script>' -> expected exactly '<p>&#228;</p><style>a::before{content:"\\2192 "}</style><script>var s="\\u03c1";</script>'; plus an attribute-bearing tag '<script type="module">' and text after the last block.

## P7a-F12 · medium · coverage_only

- **Test file:** `scripts/tests/test_build_canon_navigator.py` · no test exists
- **Production:** `scripts/build_canon_navigator.py:228`
- **Gap:** entry_issues may invert its rule (flag approved entries with a missing source and hide the open ones) without a failing test; to_tex, quantity_notes, application_edges, layout and the marks functions are equally unasserted.
- **Evidence:** No test calls nav.entry_issues or reads the issues of build(). Mutation '!= "approved"' -> '== "approved"': 82 passed.
- **Verified:** CONFIRMED (MUTATION_RERUN). Baseline 712 passed, mutated 712 passed. Unmodified code: a draft entry with 'source_status: NO_SOURCE_FOUND' gives [{'kind': 'source', 'title': 'No published source found.', 'text': 'none found.'}], the approved one []; the mutation inverts both. No test calls nav.entry_issues (grep).
- **Verifier's note:** The second half of the claim (to_tex, quantity_notes, application_edges, layout, marks functions unasserted) was not verified one by one; test_canon_navigator_{defaults,rules,figures}.py do cover default_marks, rule_marks and figure_marks, so 'the marks functions are equally unasserted' is too broad. No aero-marked test imports the importer, check_canon or the navigator build (grep), so aero_candidates is empty.
- **Acceptance mutation:** `git apply rework/patches/WP-P7a/P7a-F12.patch` (from the audit folder; scripts/build_canon_navigator.py:228  `status in ("NO_SOURCE_FOUND", "PARTIAL") and _front(text, "status") != "approved"` -> `== "approved"`). Today every fast test stays green; after your change at least one fast test must fail under it.
- **Test to write:** Fast unit tests of nav.entry_issues on literal entry texts: (a) 'source_status: NO_SOURCE_FOUND', 'status: draft', body '**Source.** none found.' -> [{'kind':'source','title':'No published source found.','text':'none found.'}]; (b) the same with 'status: approved' -> []; (c) 'shape: approximation' draft -> one 'approximation' issue, approved -> none; (d) 'dimensional_check: UNPARSEABLE' -> 'dimensions'; (e) tag 'flag/conflict' with a '## ⚠️ Conflict' section -> 'conflict' with its text; (f) a '> 🔴 **Title**' callout -> 'broken'. Likewise to_tex('V_S = sqrt(2*W/(rho*S_ref*C_L,max))') == r'V_{S} = \sqrt{2\,W/(\rho\,S_{ref}\,C_{L,max})}' and to_tex('argmax ...') is None; application_edges: SystemExit on a self-edge and on model/document mismatch.
- **Correction:** (no) Cases (a) and (b) are right as written and kill the mutation (reproduced). The to_tex expectation is wrong: the unmodified code returns r'V_{S} = \sqrt{2\,W/(\rho\,S_{ref}\,C_{L,\max })}', not '...C_{L,max})}'. to_tex('argmax over x') is None as stated. Cases (c) to (f) and application_edges were not run; read the outputs once before pinning.

## P7a-F13 · low · missing_edge_case · do together with P7a-F07

- **Test file:** `scripts/tests/test_check_canon.py` · existing test `test_the_dimensional_check_classifies_each_canonical_form` (line 411)
- **Production:** `scripts/check_canon.py:245`
- **Gap:** The legacy per-formula check may report a millimetre/metre scale difference as BALANCES (informational table only; the per-statement check has its own SCALE tests).
- **Evidence:** assert {f["slug"]: verdict ...} == {"ratio": "BALANCES", ..., "stranger": "UNKNOWN_SYMBOL"}  -- no SCALE, UNPARSEABLE or UNEVALUABLE row. Mutation removing the SCALE branch: 82 passed.
- **Verified:** CONFIRMED_BY_READING (READING). The expected dict of test_the_dimensional_check_classifies_each_canonical_form has no SCALE row: `"unlike": "ADDS_UNLIKE", "wrong": "MISMATCH", "procedure": "PROCEDURAL", "stranger": "UNKNOWN_SYMBOL"`, and _dimensional_canon has only m, s, m/s, m/s^2, m^3 units, so `elif abs(d.scale / want.scale - 1.0) > _TOLERANCE: verdict = "SCALE"` (check_canon.py:245) is never reached by it.
- **Test to write:** Extend _dimensional_canon with a quantity ('distance-mm', 'd_mm', 'mm') and a form 'scaled': ('distance-mm', 'd_mm = V_s * t') -> expected verdict 'SCALE'; add 'broken': ('speed', 'V_s = d /') -> 'UNPARSEABLE'.
- **Correction:** (unclear) Not run. Whether 'd_mm = V_s * t' resolves the symbol d_mm to the new quantity and yields SCALE, and whether 'V_s = d /' yields UNPARSEABLE, must be read off once.

## P7a-F14 · low · missing_edge_case · do together with P7a-F03

- **Test file:** `aero_kernel/tests/test_importer_taxonomy.py` · existing test `test_a_final_result_without_a_point_is_a_finding` (line 180)
- **Production:** `aero_kernel/importer/tag_rules.py:118`
- **Gap:** The rule 'an intermediate quantity needs a stage tag' has no negative test on a hand-built canon; it is guarded only because the real canon stops importing when the rule is removed.
- **Evidence:** Probe P7a-M01 (always require 'point') was killed by test_importer_real_canon.py:23 and test_importer_data_sources.py:103, by no test of test_importer_taxonomy.py.
- **Verified:** CONFIRMED_BY_READING (READING). `grep -n "needs a stage\|intermediate quantity" aero_kernel/tests/*.py` has no hit; test_importer_taxonomy.py pins the three sibling places only ('a final result needs a point tag', 'an input or target needs a module tag', 'a derived quantity needs a discipline tag'). Production: `("stage", "an intermediate quantity") if slug in consumed else ("point", "a final result")`.
- **Test to write:** Fast, test_importer_taxonomy.py: in complete(), aircraft... make 'weight' an intermediate by adding a formula that binds it (e.g. formulas/weight-user.md: inputs {w: weight}, outputs {x: weight-user}, quantity weight-user tagged point/cruise + discipline/forces) and tag weight with discipline/forces only. Expect exactly ['quantities/weight.md: stage: missing: an intermediate quantity needs a stage tag'].
- **Correction:** (unclear) Not run. Adding a consuming formula changes which mini quantities are final, so the 'exactly one finding' list has to be read off once.

## P7a-F16 · low · untested_error_path

- **Test file:** `aero_kernel/tests/test_importer_write.py` · existing test `test_a_failing_write_leaves_the_old_files_and_no_temporary_file` (line 99)
- **Production:** `aero_kernel/importer/write.py:53`
- **Gap:** Only os.replace failures are simulated. A failure while writing the second temporary file (disk full during write, mkstemp refusing) is the case the 'finally' cleanup exists for and has no test.
- **Evidence:** monkeypatch.setattr(os, "replace", refuse)  -- in all three failure tests.
- **Verified:** CONFIRMED_BY_READING (READING). Every simulated failure in test_importer_write.py patches the rename: `monkeypatch.setattr(os, "replace", refuse)` (115, 262), `spy` (201), `second_fails` (242). Nothing makes mkstemp, the stream write or os.chmod fail, so the `finally: for temporary in pending.values(): ... temporary.unlink()` path after a failed write (write.py) is not exercised with a file still pending from an earlier iteration.
- **Verifier's note:** Keep: write_outputs is what keeps the committed canon_model.json (the file the kernel loads) intact when an import fails.
- **Test to write:** Fast, test_importer_write.py: after a good import into out/, monkeypatch tempfile.mkstemp so that the second call raises OSError('disk full'); main([...changed canon..., '--out', out]) == 1; both output files byte-identical to before; sorted(out.iterdir()) == [REPORT, MODEL] (the first temp file is removed); stderr contains 'nothing written'.

## P7a-F17 · low · weak_assertion

- **Test file:** `aero_kernel/tests/test_importer_hardening.py` · existing test `test_a_quantity_slug_must_be_kebab_case` (line 315)
- **Production:** `aero_kernel/importer/assemble.py:126`
- **Gap:** Three tests carry an 'or' branch that reduces an exact comparison to something much weaker, so the finding's field (and for the abscissa test its file and field) is not pinned.
- **Evidence:** assert [(f.file, f.field) for f in result.findings] == [(FROM_MASS, "outputs.w")] or any(f.file == FROM_MASS for f in result.findings)   |   test_importer_abscissa.py:43: assert message == (...) or ("abscissa ghost is no quantity of the canon" in message)   |   test_importer_hardening.py:926: assert all("Mass" not in other for other in rest) or rest == []
- **Verified:** CONFIRMED_BY_READING (READING). All three quotes are in the code: test_importer_hardening.py:316-319 `assert [(f.file, f.field) for f in result.findings] == [(FROM_MASS, "outputs.w")] or any(f.file == FROM_MASS for f in result.findings)`; :926 `assert all("Mass" not in other for other in rest) or rest == []`; test_importer_abscissa.py:41-43 `assert message == (...) or ("abscissa ghost is no quantity of the canon" in message)`.
- **Verifier's note:** Keep: one-line fixes that pin where an import error points. The `or rest == []` at :926 is only redundant (all() of an empty list is true), not weakening. test_importer_abscissa.py is not in the list of files WP-P7a may change.
- **Test to write:** Replace each by the exact list the importer produces today (run once, read, then pin): e.g. assert shown(result) == [f"{FROM_MASS}: outputs.w: String should match pattern ... (got 'calc:Weight')"] with the real text; for the abscissa test assert the full 'quantities/profile.md: <field>: abscissa ghost is no quantity of the canon'.

## Not part of this package's work

| Finding | State | Reason |
|---|---|---|
| P7a-F04 | waiting_for_decision | maintainer decision open (README section 6); do not write its test |
| P7a-F05 | dropped | maintainer 2026-11-21: taxonomy.yaml feeds the tag checks and the navigator, not the calculation; the missing scan is accepted, no ticket |
| P7a-F15 | dropped | Drop: the reviewer found identical bytes for seeds 0..3, and every CI run of `python -m aero_kernel.importer --check` is a fresh interpreter with a random hash seed that compares the content hash with the committed model, so a seed dependen |
| P7a-F18 | dropped | Drop as a gap: test_an_explicit_default_embed_equals_the_bare_one (test_importer_hardening.py:382) applies the identical change `mutate(TWICE, "weight-from-mass,", "weight-from-mass.default,")` and asserts `bare.model_dump() == explicit.mod |
| P7a-F19 | dropped | Drop: BOM and tab already fail loudly at import, CRLF changes nothing; none of it can reach a flight-relevant value. P7a-F05 (defect track) is in the same file should the maintainer want it bundled instead. |
