from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    provider: str = "mock"
    model: str = ""
    api_key: str = ""
    system_prompt: str = "You are a helpful, concise assistant."
    max_history: int = 20
    rate_limit_per_min: int = 15
    static_dir: str = "../frontend/dist"
    cors_origins: str = "http://localhost:5173"

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
