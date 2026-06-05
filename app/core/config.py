import os
from pathlib import Path

# Canonical, absolute project paths — the single source of truth.
#
# These MUST be absolute and CWD-independent: airfoil .dat files are written
# by the OpenVSP importer and read back by analysis/UI from (potentially)
# different working directories. A CWD-relative airfoils dir made
# procedurally-generated airfoils (e.g. Spitfire's naca14012 / naca4-923-a0.6)
# land outside the read directory, so they appeared "missing" after import.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
AIRFOILS_DIR: Path = REPO_ROOT / "components" / "airfoils"


class Settings:
    PROJECT_NAME: str = "My FastAPI Project"
    VERSION: str = "1.0.0"
    UVICORN_HOST: str = "127.0.0.1"

    # Construction plan artifacts directory
    ARTIFACTS_BASE_DIR: Path = Path(
        os.environ.get("ARTIFACTS_BASE_DIR", "/tmp/da3dalus_artifacts")
    ).resolve()


settings = Settings()
