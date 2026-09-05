from app.core.config import Config


def test_config_loads_environment_variables():

    config = Config()

    assert config.app_name == "Veritas"
    assert config.app_env == "development"
    assert config.database_url.startswith("sqlite:///")
    assert config.gnews_base_url == "https://gnews.io/api/v4"


def test_config_has_gnews_api_key():

    config = Config()

    assert config.parsed_gnews_api_keys
    assert isinstance(config.parsed_gnews_api_keys, list)
    assert len(config.parsed_gnews_api_keys) > 0


import pytest
from pydantic import ValidationError


@pytest.mark.parametrize("raw,expected", [
    (" a, b ,,,c, d ,a ", ["a", "b", "c", "d"]),
    (" , , ", []), ("", []), ("single", ["single"]),
])
def test_pool_parsing(raw, expected):
    assert Config(gnews_api_keys=raw).parsed_gnews_api_keys == expected


def test_pool_rejects_invalid_type_without_exposing_input():
    with pytest.raises(ValidationError) as error:
        Config(gnews_api_keys=["private-placeholder"])
    assert "private-placeholder" not in str(error.value)


def test_pool_is_hidden_from_config_repr():
    assert "private-placeholder" not in repr(Config(gnews_api_keys="private-placeholder"))
