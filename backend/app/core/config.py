from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # БД
    database_url: str
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_db: str = "oee_db"

    # Redis
    redis_url: str = "redis://redis:6379/0"

    # Auth
    secret_key: str
    access_token_expire_minutes: int = 480

    # Приложение
    app_env: str = "development"
    debug: bool = False
    allowed_origins: list[str] = ["http://localhost:5173"]


settings = Settings()
