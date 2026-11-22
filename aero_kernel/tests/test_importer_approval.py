"""Two-stage approval (#1251): ``data:`` sources on supplied quantities, derived status, stage 2."""

from pathlib import Path

from aero_kernel.canon.model import CanonModel
from aero_kernel.importer.approval import derive_approval
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import (
    MINI_CANON,
    formula_text,
    quantity_text,
    write_canon,
)

RATIO = "quantities/ratio.md"
GRAVITY = "quantities/gravity.md"
WEIGHT = "quantities/weight.md"


def run(tmp_path: Path, overrides: dict[str, str | None]) -> ImportResult:
    return import_canon(write_canon(tmp_path, overrides))


def with_data(name: str, data: str) -> dict[str, str | None]:
    """Return an override that adds a ``data:`` line to one mini-canon quantity."""
    return {name: MINI_CANON[name].replace("type: scalar\n", f"type: scalar\n{data}\n", 1)}


def model_of(result: ImportResult) -> CanonModel:
    assert result.model is not None, [str(finding) for finding in result.findings]
    return result.model


def test_data_is_carried_into_the_model_as_a_list(tmp_path: Path) -> None:
    result = run(tmp_path, {})
    assert model_of(result).namespaces["calc"].quantities["aircraft-mass"].data == [
        "geometry:total_mass_kg"
    ]


def test_data_may_name_several_sources(tmp_path: Path) -> None:
    data = "data: [default:gravity, 'app:OperatingPointSchema.altitude']"
    result = run(tmp_path, with_data(GRAVITY, data))
    assert model_of(result).namespaces["calc"].quantities["gravity"].data == [
        "default:gravity",
        "app:OperatingPointSchema.altitude",
    ]


def test_an_unknown_source_kind_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, with_data(RATIO, "data: spreadsheet:cell"))
    assert result.model is None
    assert any(f.file == RATIO and f.field == "data[0]" for f in result.findings)


def test_a_source_without_a_location_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, with_data(RATIO, "data: 'geometry:'"))
    assert any(f.file == RATIO and f.field == "data[0]" for f in result.findings)


def test_data_on_a_produced_quantity_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, with_data(WEIGHT, "data: default:gravity"))
    messages = [f.message for f in result.findings if f.file == WEIGHT and f.field == "data"]
    assert len(messages) == 1
    assert "produced" in messages[0]


def test_a_hand_set_status_on_a_quantity_is_a_finding(tmp_path: Path) -> None:
    result = run(tmp_path, with_data(RATIO, "status: approved"))
    messages = [f.message for f in result.findings if f.file == RATIO and f.field == "status"]
    assert len(messages) == 1
    assert "derived" in messages[0]


def test_a_default_source_must_exist_in_defaults_yaml(tmp_path: Path) -> None:
    canon = write_canon(tmp_path, with_data(RATIO, "data: default:aircraft-mass"))
    result = import_canon(canon, repo_root=tmp_path)
    assert any(
        f.file == RATIO and f.field == "data" and "defaults.yaml" in f.message
        for f in result.findings
    )


def test_a_default_source_in_defaults_yaml_resolves(tmp_path: Path) -> None:
    canon = write_canon(tmp_path, with_data(GRAVITY, "data: default:gravity"))
    result = import_canon(canon, repo_root=tmp_path)
    assert result.findings == ()


def test_stage_2_counts_supplied_inputs_with_a_source(tmp_path: Path) -> None:
    result = run(tmp_path, {})
    approval = derive_approval(model_of(result), {"weight-from-mass": "approved"})
    row = next(r for r in approval.formulas if r.formula == "weight-from-mass")
    assert (row.stage1, row.mapped, row.total) == ("approved", 1, 2)
    assert [i.quantity for i in row.inputs if not i.mapped] == ["gravity"]
    assert approval.quantity_status["aircraft-mass"] == "approved"
    assert approval.quantity_status["gravity"] == "unmapped"


def test_a_produced_quantity_is_approved_when_its_producers_hold_both_stages(
    tmp_path: Path,
) -> None:
    result = run(tmp_path, with_data(GRAVITY, "data: default:gravity"))
    stage1 = {"weight-from-mass": "approved", "weigh-twice": "draft"}
    approval = derive_approval(model_of(result), stage1)
    assert approval.quantity_status["weight"] == "approved"
    assert approval.quantity_status["weight-twice"] == "draft"


def test_the_report_lists_unmapped_inputs(tmp_path: Path) -> None:
    result = run(tmp_path, {})
    assert result.report is not None
    assert "## Approval, stage 2" in result.report
    unmapped = result.report.split("### Unmapped inputs")[-1]
    assert "| gravity |" in unmapped
    assert "| aircraft-mass |" not in unmapped


def read_canon(data: str) -> dict[str, str | None]:
    """A catalogue read (tool KAT) producing one quantity, and a formula that consumes it."""
    return {
        "quantities/stored-mass.md": quantity_text("stored-mass", "m_s", "kg", "derived", data),
        "quantities/weight-read.md": quantity_text("weight-read", "W_r", "N", "derived"),
        "formulas/catalogue-read.md": formula_text(
            "catalogue-read",
            "kind: procedure\ntool: KAT\ninputs: {m: aircraft-mass}\noutputs: {x: stored-mass}\n",
        ),
        "formulas/weight-of-stored.md": formula_text(
            "weight-of-stored",
            "kind: law\ntool: APP\ninputs: {m: stored-mass, g: gravity}\noutputs: {w: weight-read}\n",
        ),
    }


def test_a_catalogue_read_may_name_the_field_it_reads(tmp_path: Path) -> None:
    result = run(tmp_path, read_canon("data: component:battery.capacity_mah\n"))
    assert model_of(result).namespaces["calc"].quantities["stored-mass"].data == [
        "component:battery.capacity_mah"
    ]


def test_a_quantity_read_from_the_catalogue_counts_when_it_names_its_field(tmp_path: Path) -> None:
    model = model_of(run(tmp_path, read_canon("data: component:battery.capacity_mah\n")))
    stage1 = {"catalogue-read": "approved", "weight-of-stored": "draft"}
    approval = derive_approval(model, stage1)
    row = next(r for r in approval.formulas if r.formula == "weight-of-stored")
    assert [i.quantity for i in row.missing] == ["gravity"]
    assert approval.quantity_status["stored-mass"] == "approved"


def test_a_quantity_the_catalogue_does_not_carry_is_unmapped_for_its_consumer(
    tmp_path: Path,
) -> None:
    model = model_of(run(tmp_path, read_canon("")))
    stage1 = {"catalogue-read": "approved", "weight-of-stored": "draft"}
    approval = derive_approval(model, stage1)
    row = next(r for r in approval.formulas if r.formula == "weight-of-stored")
    missing = {i.quantity: i.basis for i in row.missing}
    assert "stored-mass" in missing
    assert "catalogue" in missing["stored-mass"]
    assert approval.quantity_status["stored-mass"] == "unmapped"
    assert "stored-mass" in approval.unmapped


def chain_canon(data: str) -> dict[str, str | None]:
    """The catalogue read of ``read_canon``, a consumer of it, and a consumer of that consumer."""
    return {
        **read_canon(data),
        "quantities/weight-read-twice.md": quantity_text(
            "weight-read-twice", "W_r2", "N", "derived"
        ),
        "formulas/weight-of-weight.md": formula_text(
            "weight-of-weight",
            "kind: law\ntool: APP\ninputs: {w: weight-read, g: gravity}\noutputs: {w2: weight-read-twice}\n",
        ),
    }


ALL_APPROVED = {
    "catalogue-read": "approved",
    "weight-of-stored": "approved",
    "weight-of-weight": "approved",
}


def test_a_gap_two_levels_up_makes_the_input_unmapped_and_names_the_root_cause(
    tmp_path: Path,
) -> None:
    model = model_of(run(tmp_path, chain_canon("")))
    approval = derive_approval(model, ALL_APPROVED)
    row = next(r for r in approval.formulas if r.formula == "weight-of-weight")
    missing = {i.quantity: i.basis for i in row.missing}
    assert "weight-read" in missing
    assert "stored-mass" in missing["weight-read"]
    assert "via weight-of-stored" in missing["weight-read"]
    assert not row.fully_approved


def test_the_chain_is_covered_when_every_level_is(tmp_path: Path) -> None:
    canon = {
        **chain_canon("data: component:battery.capacity_mah\n"),
        **with_data(GRAVITY, "data: default:gravity"),
    }
    approval = derive_approval(model_of(run(tmp_path, canon)), ALL_APPROVED)
    row = next(r for r in approval.formulas if r.formula == "weight-of-weight")
    assert row.missing == ()
    assert row.fully_approved
    assert approval.quantity_status["weight-read"] == "approved"


def test_a_draft_formula_two_levels_up_blocks_the_input(tmp_path: Path) -> None:
    canon = {
        **chain_canon("data: component:battery.capacity_mah\n"),
        **with_data(GRAVITY, "data: default:gravity"),
    }
    model = model_of(run(tmp_path, canon))
    stage1 = {**ALL_APPROVED, "weight-of-stored": "draft"}
    row = next(
        r for r in derive_approval(model, stage1).formulas if r.formula == "weight-of-weight"
    )
    assert "weight-of-stored" in {i.quantity: i.basis for i in row.missing}["weight-read"]


def test_a_draft_embedded_formula_blocks_the_embedder(tmp_path: Path) -> None:
    model = model_of(run(tmp_path, {}))
    stage1 = {"weigh-twice": "approved", "weight-from-mass": "draft", "weighing": "approved"}
    row = next(r for r in derive_approval(model, stage1).formulas if r.formula == "weigh-twice")
    assert any("weight-from-mass" in blocker for blocker in row.embed_blockers)
    assert not row.fully_approved


def approved(name: str) -> str:
    """Return a mini-canon formula text whose own ``status`` (stage 1) is ``approved``."""
    return MINI_CANON[name].replace("status: draft", "status: approved")


def report_row(result: ImportResult, prefix: str) -> str:
    """Return the one stage-2 table row of the report that starts with ``prefix``."""
    assert result.report is not None
    rows = [line for line in result.report.splitlines() if line.startswith(prefix)]
    assert len(rows) == 1, rows
    return rows[0]


def test_a_formula_status_in_the_canon_document_reaches_the_report(tmp_path: Path) -> None:
    # Stage 1 comes from the formula entry's own 'status:'; both inputs of weight-from-mass are
    # mapped (aircraft-mass: geometry:total_mass_kg, gravity: default:gravity) -> "2 of 2".
    overrides = {
        **with_data(GRAVITY, "data: default:gravity"),
        "formulas/weight-from-mass.md": approved("formulas/weight-from-mass.md"),
    }
    result = run(tmp_path, overrides)
    assert result.findings == ()
    assert report_row(result, "| weight-from-mass | approved") == (
        "| weight-from-mass | approved | 2 of 2 |  |"
    )
    assert report_row(result, "| weighing | draft") == "| weighing | draft | 2 of 2 |  |"


def test_a_formula_status_that_is_not_a_string_counts_as_draft(tmp_path: Path) -> None:
    overrides = {
        **with_data(GRAVITY, "data: default:gravity"),
        "formulas/weight-from-mass.md": MINI_CANON["formulas/weight-from-mass.md"].replace(
            "status: draft", "status: 5"
        ),
    }
    result = run(tmp_path, overrides)
    assert report_row(result, "| weight-from-mass | draft") == (
        "| weight-from-mass | draft | 2 of 2 |  |"
    )


def test_an_approved_formula_lists_its_embedded_formulas_that_are_not_approved(
    tmp_path: Path,
) -> None:
    overrides = {
        **with_data(GRAVITY, "data: default:gravity"),
        "formulas/weigh-twice.md": approved("formulas/weigh-twice.md"),
    }
    result = run(tmp_path, overrides)
    assert report_row(result, "| weigh-twice | approved") == (
        "| weigh-twice | approved | 2 of 2 |"
        " embedded: weighing: not approved; embedded: weight-from-mass: not approved |"
    )


def test_a_consistency_default_must_exist_in_defaults_yaml(tmp_path: Path) -> None:
    # README: a 'consistency:' source is validated the same way as 'data:'.
    canon = write_canon(tmp_path, with_data(RATIO, "consistency: default:aircraft-mass"))
    result = import_canon(canon, repo_root=tmp_path)
    assert [str(f) for f in result.findings] == [
        "quantities/ratio.md: consistency: default:aircraft-mass: "
        "'aircraft-mass' is not a key of defaults.yaml"
    ]


def test_a_consistency_default_in_defaults_yaml_resolves(tmp_path: Path) -> None:
    canon = write_canon(tmp_path, with_data(RATIO, "consistency: default:gravity"))
    assert import_canon(canon, repo_root=tmp_path).findings == ()


def test_a_consistency_geometry_path_must_exist_in_the_geometry_schema(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    canon = write_canon(tmp_path, with_data(RATIO, "consistency: geometry:total_mas_kg"))
    result = import_canon(canon, repo_root=repo_root)
    mismatches = [f for f in result.findings if f.file == RATIO and f.field == "consistency"]
    assert len(mismatches) == 1
    assert "the document has no property 'total_mas_kg'" in mismatches[0].message
