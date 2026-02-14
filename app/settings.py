from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    base_url: str = "http://localhost:8000"
    openai_api_key: str = "sk*"

settings = Settings()

@lru_cache()
def get_settings() -> Settings:
    return Settings()
