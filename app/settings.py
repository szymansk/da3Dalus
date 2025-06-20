from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    base_url: str
    openai_api_key: str

    class Config:
        env_file = ".env"

settings = Settings()

from functools import lru_cache
@lru_cache()
def get_settings() -> Settings:
    return Settings()
