from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    secret_key: str = "change-me-in-production"
    admin_username: str = "admin"
    admin_password: str = "changeme"
    database_url: str = "sqlite:////data/piruetas.db"
    data_dir: str = "/data"
    port: int = 8000
    secure_cookies: bool = True
    week_start: str = "monday"  # "monday" or "sunday"
    demo_enabled: bool = False
    demo_username: str = "demo"
    demo_password: str = "demo"
    demo_reset_interval: int = 1800  # seconds

    @model_validator(mode="after")
    def validate_settings(self) -> "Settings":
        if self.secret_key == "change-me-in-production" and self.secure_cookies:
            raise ValueError(
                "secret_key must be changed from the default when secure_cookies is True"
            )
        if self.week_start.lower() not in ("monday", "sunday"):
            raise ValueError("week_start must be 'monday' or 'sunday'")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
