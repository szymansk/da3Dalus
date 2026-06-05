"""Regression: the airfoils directory must be one absolute, CWD-independent
path across the writer (OpenVSP import), the API serving endpoint, and the
reader (wing-config resolver).

A previously CWD-relative writer/serving dir made procedurally-generated
airfoils (e.g. the Spitfire's naca14012 / naca4-923-a0.6) land outside the
absolute read directory when the import ran via the API/worker from a
different working directory, so they appeared "missing" in the editor and in
analyses. See app.core.config.AIRFOILS_DIR.
"""

import os
from pathlib import Path


def test_airfoils_dir_is_single_absolute_path_across_modules():
    from app.api.v2.endpoints import airfoils as api_airfoils
    from app.converters import openvsp_airfoil
    from app.core.config import AIRFOILS_DIR as canonical
    from app.services import create_wing_configuration as cwc

    assert canonical.is_absolute()
    assert openvsp_airfoil.AIRFOILS_DIR == canonical, "import writer dir diverged"
    assert api_airfoils.AIRFOILS_DIR == canonical, "API serving dir diverged"
    assert cwc._AIRFOILS_DIR == canonical, "wing-config reader dir diverged"


def test_generated_airfoil_is_found_regardless_of_cwd(tmp_path):
    """Writing a generated NACA airfoil from a foreign CWD must still be
    resolvable by the reader (no stray <cwd>/components/airfoils file)."""
    from app.converters import openvsp_airfoil
    from app.services.create_wing_configuration import _resolve_airfoil_reference

    name = "naca23091"  # unlikely to be a curated/committed file
    target = openvsp_airfoil.AIRFOILS_DIR / f"{name}.dat"
    pre_existing = target.exists()
    cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        openvsp_airfoil.ensure_naca5_dat(
            name=name, camber=0.3, camber_loc=0.15, reflex=0.0, thick_chord=0.091
        )
        # No stray copy under the foreign CWD.
        assert not (Path(tmp_path) / "components" / "airfoils" / f"{name}.dat").exists()
        # The reader (absolute) resolves it to a real file.
        resolved = _resolve_airfoil_reference(name)
        assert os.path.isfile(resolved)
    finally:
        os.chdir(cwd)
        if not pre_existing and target.exists():
            target.unlink()
