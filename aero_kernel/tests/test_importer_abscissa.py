"""The abscissa of a curve in the import (gh-1424): present, an existing scalar, only on curves."""

from pathlib import Path

import pytest
from aero_kernel.importer.pipeline import ImportResult, import_canon
from aero_kernel.tests.importer_builders import quantity_text, write_canon

CURVE = "quantities/profile.md"


def run(tmp_path: Path, *, type_: str, extra: str) -> ImportResult:
    """Import the mini canon with one extra supplied quantity of ``type_``."""
    text = quantity_text("profile", "p(r)", "1", "input", extra, type_)
    return import_canon(write_canon(tmp_path, {CURVE: text}))


def findings(result: ImportResult) -> list[str]:
    return [str(finding) for finding in result.findings]


def test_a_curve_with_an_existing_scalar_abscissa_imports(tmp_path: Path) -> None:
    result = run(tmp_path, type_="curve", extra="abscissa: ratio\n")
    assert findings(result) == []
    assert result.model is not None
    assert result.model.namespaces["calc"].quantities["profile"].abscissa == "ratio"


def test_a_curve_pair_needs_one_too(tmp_path: Path) -> None:
    result = run(tmp_path, type_="curve_pair", extra="abscissa: ratio\n")
    assert findings(result) == []


@pytest.mark.parametrize("type_", ["curve", "curve_pair"])
def test_a_curve_without_an_abscissa_is_a_finding(tmp_path: Path, type_: str) -> None:
    (message,) = findings(run(tmp_path, type_=type_, extra=""))
    assert message.startswith("quantities/profile.md")
    assert "needs an abscissa" in message


def test_an_unknown_abscissa_is_a_finding(tmp_path: Path) -> None:
    (message,) = findings(run(tmp_path, type_="curve", extra="abscissa: ghost\n"))
    assert message == (
        "quantities/profile.md: abscissa: abscissa ghost is no quantity of the canon"
    ) or ("abscissa ghost is no quantity of the canon" in message)


def test_a_non_scalar_abscissa_is_a_finding(tmp_path: Path) -> None:
    (message,) = findings(run(tmp_path, type_="curve", extra="abscissa: airplane\n"))
    assert "abscissa airplane is a airplane, not a scalar" in message


def test_an_abscissa_on_a_scalar_is_a_finding(tmp_path: Path) -> None:
    (message,) = findings(run(tmp_path, type_="scalar", extra="abscissa: ratio\n"))
    assert "only allowed on a curve or curve_pair" in message
