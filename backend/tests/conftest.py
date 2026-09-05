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
