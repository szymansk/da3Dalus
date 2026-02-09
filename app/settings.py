from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    base_url: str = "http://localhost:8000"
    openai_api_key: str = "sk*"

    class Config:
        env_file = ".env"

settings = Settings()

from functools import lru_cache
@lru_cache()
def get_settings() -> Settings:
    return Settings()
