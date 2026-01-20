from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "Allerac Health API"
    debug: bool = False

    # PostgreSQL
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "allerac_health"
    postgres_user: str = "allerac"
    postgres_password: str = "allerac_secret"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # InfluxDB
    influxdb_host: str = "localhost"
    influxdb_port: int = 8086
    influxdb_db: str = "health_metrics"
    influxdb_user: str = "allerac"
    influxdb_password: str = "allerac_secret"

    # Security
    secret_key: str = "change-me-in-production"
    encryption_key: str = "32-byte-key-for-encryption-here"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000", "*"]

    @property
    def database_url(self) -> str:
        return f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def database_url_sync(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
