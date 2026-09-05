from app.core.config import Config


def test_config_loads_environment_variables():

    config = Config()

    assert config.app_name == "Veritas"
    assert config.app_env == "development"
    assert config.database_url == "sqlite:///./veritas.db"
    assert config.gnews_base_url == "https://gnews.io/api/v4"


def test_config_has_gnews_api_key():

    config = Config()

    assert config.gnews_api_key
    assert isinstance(config.gnews_api_key, str)
    assert len(config.gnews_api_key) > 0
