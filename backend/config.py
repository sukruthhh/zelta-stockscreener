from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_url: str = Field(alias="POSTGRES_URL")
    redis_url: str = Field("redis://localhost:6379/0", alias="REDIS_URL")
    finnhub_api_key: str | None = Field(None, alias="FINNHUB_API_KEY")
    openai_api_key: str | None = Field(None, alias="OPENAI_API_KEY")
    supabase_url: str | None = Field(None, alias="SUPABASE_URL")
    supabase_jwt_audience: str = Field("authenticated", alias="SUPABASE_JWT_AUDIENCE")
    cors_origins: list[str] = Field(["http://localhost:3000"], alias="CORS_ORIGINS")
    market_data_timeout_seconds: float = Field(15, alias="MARKET_DATA_TIMEOUT_SECONDS", gt=0)
    news_timeout_seconds: float = Field(10, alias="NEWS_TIMEOUT_SECONDS", gt=0)

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value):
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @property
    def supabase_jwks_url(self) -> str | None:
        if not self.supabase_url:
            return None
        return f"{self.supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"


@lru_cache
def get_settings() -> Settings:
    return Settings()

