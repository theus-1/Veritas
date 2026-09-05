import os

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    app_name: str = "Veritas"
    app_env: str = "development"
    database_url: str = Field(default="sqlite:///./veritas.db", repr=False)
    cors_origins: str = "http://localhost:5173"

    gnews_api_keys: str = Field(
        default="",
        repr=False,
    )
    gnews_base_url: str = "https://gnews.io/api/v4"
    gnews_enabled: bool = True

    gemini_enabled: bool = False
    gemini_api_key: str = Field(
        default="",
        repr=False,
    )
    gemini_model: str = Field(
        default="gemini-3.8-flash",
        pattern=r"^gemini-[a-z0-9.-]+$",
    )

    openai_api_key: str = Field(
        default="",
        repr=False,
    )

    groq_api_key: str = Field(
    default="",
    repr=False,
    )

    groq_model: str = Field(
        default="openai/gpt-oss-20b",
    )

    model_config = SettingsConfigDict(
        env_file=None if os.getenv("APP_ENV") == "production" or os.getenv("VERITAS_DISABLE_DOTENV") == "1" else ".env",
        hide_input_in_errors=True,
    )

    @property
    def parsed_cors_origins(self) -> list[str]:
        return [origin.strip().rstrip("/") for origin in self.cors_origins.split(",") if origin.strip()]

    @model_validator(mode="after")
    def validate_production(self):
        if self.app_env == "production":
            if not self.database_url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
                raise ValueError("Production requires PostgreSQL")
            if not self.parsed_cors_origins or any(not origin.startswith("https://") or "*" in origin for origin in self.parsed_cors_origins):
                raise ValueError("Production requires explicit HTTPS CORS origins")
        return self

    @property
    def parsed_gnews_api_keys(
        self,
    ) -> list[str]:
        # Preserve order and try each
        # distinct credential only once
        # per search.
        return list(
            dict.fromkeys(
                key.strip()
                for key
                in self.gnews_api_keys.split(",")
                if key.strip()
            )
        )
