from pathlib import Path

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

# Canonical, absolute project paths — the single source of truth.
#
# These MUST be absolute and CWD-independent: airfoil .dat files are written
# by the OpenVSP importer and read back by analysis/UI from (potentially)
# different working directories. A CWD-relative airfoils dir made
# procedurally-generated airfoils (e.g. Spitfire's naca14012 / naca4-923-a0.6)
# land outside the read directory, so they appeared "missing" after import.
REPO_ROOT: Path = Path(__file__).resolve().parents[2]
AIRFOILS_DIR: Path = REPO_ROOT / "components" / "airfoils"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    PROJECT_NAME: str = "My FastAPI Project"
    VERSION: str = "1.0.0"
    UVICORN_HOST: str = "127.0.0.1"

    # Construction plan artifacts directory
    ARTIFACTS_BASE_DIR: Path = Path("/tmp/da3dalus_artifacts")

    # ------------------------------------------------------------------
    # AI Copilot (gh-902 / gh-916)
    # ------------------------------------------------------------------
    # API key for the LiteLLM hub (OpenAI-compatible).  SecretStr so it
    # is masked in repr/logs; access the raw value with .get_secret_value().
    COPILOT_API_KEY: SecretStr | None = None
    # Base URL of the LiteLLM hub.  None → use the OpenAI default endpoint.
    COPILOT_BASE_URL: str | None = None
    # Chat model routed through the hub.
    COPILOT_MODEL: str = "claude-sonnet-4-6"
    # Embedding model (used from Slice 4 / RAG onward).
    COPILOT_EMBEDDING_MODEL: str = "text-embedding-3-large"


settings = Settings()
