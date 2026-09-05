from pydantic_settings import BaseSettings, SettingsConfigDict


class Config(BaseSettings):
    app_name: str
    app_env: str
    database_url: str

    gnews_api_key: str
    gnews_api_key2: str
    gnews_base_url: str
    gnews_enabled: bool = True

    model_config = SettingsConfigDict(env_file=".env")
