from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    # extra="ignore" so developer-local variables in .env (GITHUB_TOKEN, etc.)
    # do not break application startup or test collection.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    base_url: str = "http://localhost:8000"
    openai_api_key: str = "sk*"
    version: str = "0.1.0"

settings = Settings()

@lru_cache()
def get_settings() -> Settings:
    return Settings()
