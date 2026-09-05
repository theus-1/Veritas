import pytest
from pydantic import ValidationError

from app.core.config import Config


def test_production_rejects_ephemeral_sqlite():
    with pytest.raises(ValidationError, match="requires PostgreSQL"):
        Config(app_env="production", database_url="sqlite://", cors_origins="https://veritas.example")


@pytest.mark.parametrize("origin", ["*", "http://localhost:5173", ""])
def test_production_rejects_unsafe_cors(origin):
    with pytest.raises(ValidationError, match="HTTPS CORS"):
        Config(app_env="production", database_url="postgresql://user:secret@localhost/db", cors_origins=origin)


def test_production_accepts_postgres_and_explicit_origins():
    config = Config(app_env="production", database_url="postgresql://user:secret@localhost/db", cors_origins="https://veritas.example/")
    assert config.parsed_cors_origins == ["https://veritas.example"]
    assert "secret" not in repr(config)
