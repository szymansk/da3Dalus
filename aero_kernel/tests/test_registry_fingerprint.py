"""Registry: the interface fingerprint and its command line (ARCHITECTURE ch. 8.12)."""

import hashlib
import runpy
import sys
from pathlib import Path

import pytest
from aero_kernel.canon.model import CanonModel
from aero_kernel.registry import interface_fingerprint, main

FIXTURE = Path(__file__).resolve().parent / "fixtures" / "flight_canon.json"


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def test_fingerprint_hashes_sorted_inputs_outputs_and_optional(flight_canon: CanonModel) -> None:
    formula = flight_canon.formula("airplane-configuration")
    assert formula is not None
    expected = _digest(
        '{"inputs":["airplane","flap_deflection"],"optional":["flap_deflection"],'
        '"outputs":["airplane_cfg"]}'
    )
    assert interface_fingerprint(formula) == expected


def test_fingerprint_is_independent_of_declaration_order(flight_canon: CanonModel) -> None:
    formula = flight_canon.formula("stall-speed")
    assert formula is not None
    reordered = formula.model_copy(
        update={
            "inputs": dict(reversed(formula.inputs.items())),
            "outputs": dict(reversed(formula.outputs.items())),
        }
    )
    assert interface_fingerprint(reordered) == interface_fingerprint(formula)


@pytest.mark.parametrize("change", ["inputs", "outputs", "optional"])
def test_fingerprint_changes_with_any_part_of_the_interface(
    flight_canon: CanonModel, change: str
) -> None:
    formula = flight_canon.formula("stall-speed")
    assert formula is not None
    update = {
        "inputs": {**formula.inputs, "extra": None},
        "outputs": {**formula.outputs, "extra": None},
        "optional": ("n_load",),
    }
    changed = formula.model_copy(update={change: update[change]})
    assert interface_fingerprint(changed) != interface_fingerprint(formula)


def test_cli_prints_the_fingerprint_of_a_slug(
    flight_canon: CanonModel, capsys: pytest.CaptureFixture[str]
) -> None:
    formula = flight_canon.formula("stall-speed")
    assert formula is not None
    assert main(["fingerprint", str(FIXTURE), "stall-speed"]) == 0
    assert capsys.readouterr().out == interface_fingerprint(formula) + "\n"


def test_cli_reports_an_unknown_slug(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["fingerprint", str(FIXTURE), "no-such-formula"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "no-such-formula" in captured.err


def test_cli_reports_a_model_that_cannot_be_loaded(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    broken = tmp_path / "model.json"
    broken.write_text("{}", encoding="utf-8")
    assert main(["fingerprint", str(broken), "stall-speed"]) == 2
    assert "could not be loaded" in capsys.readouterr().err


# runpy re-executes a module the package import already loaded; that is the point of this test.
@pytest.mark.filterwarnings("ignore:'aero_kernel.registry' found in sys.modules:RuntimeWarning")
def test_module_runs_as_a_script(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["registry", "fingerprint", str(FIXTURE), "stall-speed"])
    with pytest.raises(SystemExit) as raised:
        runpy.run_module("aero_kernel.registry", run_name="__main__")
    assert raised.value.code == 0
    assert capsys.readouterr().out.startswith("sha256:")
