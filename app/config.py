from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    pincode_api_base_url: str = "https://api.postalpincode.in"
    service_districts: str
    http_timeout_seconds: float = 5.0
    log_level: str = "INFO"
    sql_echo: bool = False
    port: int = 8000
    enable_error_probe: bool = False
    pincode_max_retries: int = 2

    @field_validator("database_url")
    @classmethod
    def database_url_present(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("DATABASE_URL is required")
        return value

    @property
    def districts(self) -> frozenset[str]:
        return frozenset(part.strip() for part in self.service_districts.split(",") if part.strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


def reset_settings_cache() -> None:
    get_settings.cache_clear()
