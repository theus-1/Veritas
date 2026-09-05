import os
import tempfile
from pathlib import Path

import dotenv
from app.core.config import Config

# Isolate before test collection imports app/database modules. Never load dotenv.
Config.model_config["env_file"] = None
dotenv.load_dotenv = lambda *args, **kwargs: False
_test_directory = tempfile.TemporaryDirectory(prefix="veritas-tests-")
os.environ.update({
    "APP_NAME": "Veritas",
    "APP_ENV": "development",
    "DATABASE_URL": "sqlite:///" + (Path(_test_directory.name) / "tests.db").as_posix(),
    "GNEWS_API_KEYS": "dummy-one,dummy-two",
    "GNEWS_BASE_URL": "https://gnews.io/api/v4",
    "GNEWS_ENABLED": "false",
    "GEMINI_ENABLED": "false",
    "GEMINI_API_KEY": "dummy-gemini",
})

import socket

import httpx
import pytest


@pytest.fixture(autouse=True)
def disable_gnews(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "false")


@pytest.fixture(autouse=True)
def block_gnews_network(monkeypatch):
    original_connect = socket.socket.connect

    def blocked_connect(self, address):
        host = address[0]

        try:
            resolved_ips = socket.getaddrinfo(
                "gnews.io",
                None
            )
            gnews_ips = {
                result[4][0]
                for result in resolved_ips
            }
        except socket.gaierror:
            gnews_ips = set()

        if host in gnews_ips:
            raise RuntimeError(
                "TESTE TENTOU FAZER UMA CONEXÃO REAL COM GNEWS.IO."
            )

        return original_connect(self, address)

    monkeypatch.setattr(
        socket.socket,
        "connect",
        blocked_connect
    )


@pytest.fixture(autouse=True)
def block_external_http_requests(monkeypatch):
    def blocked_get(*args, **kwargs):
        raise RuntimeError(
            "TESTE TENTOU FAZER UMA REQUISIÇÃO HTTP REAL. "
            "Use mock/monkeypatch."
        )

    monkeypatch.setattr(httpx, "get", blocked_get)
    monkeypatch.setattr(httpx, "post", blocked_get)

@pytest.fixture(autouse=True)
def no_request_delay(monkeypatch):
    monkeypatch.setattr("app.clients.gnews_client.GNewsClient.REQUEST_DELAY", 0)


def pytest_sessionfinish(session, exitstatus):
    from app.core.database import engine
    engine.dispose()
    _test_directory.cleanup()


@pytest.fixture(scope="session", autouse=True)
def initialize_test_database():
    from app.core.database import Base, engine
    import app.models
    Base.metadata.create_all(bind=engine)
