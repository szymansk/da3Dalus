import os
from pathlib import Path


class Settings:
    PROJECT_NAME: str = "My FastAPI Project"
    VERSION: str = "1.0.0"
    UVICORN_HOST: str = "127.0.0.1"

    # Construction plan artifacts directory
    ARTIFACTS_BASE_DIR: Path = Path(
        os.environ.get("ARTIFACTS_BASE_DIR", "/tmp/da3dalus_artifacts")
    ).resolve()


settings = Settings()
