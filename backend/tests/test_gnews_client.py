import httpx
import pytest

from app.clients.gnews_client import GNewsClient
from app.core.config import Config


def test_gnews_client_returns_search_results(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    fake_response = httpx.Response(
        200,
        json={
            "articles": [
                {
                    "title": "Notícia de teste",
                    "url": "https://exemplo.com/noticia",
                    "description": "Descrição da notícia.",
                    "source": {
                        "name": "Fonte de teste"
                    }
                }
            ]
        },
        request=httpx.Request(
            "GET",
            "https://gnews.io/api/v4/search"
        )
    )

    def fake_get(*args, **kwargs):
        return fake_response

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    results = client.search("teste")

    assert len(results) == 1
    assert results[0].title == "Notícia de teste"
    assert results[0].url == "https://exemplo.com/noticia"
    assert results[0].source_name == "Fonte de teste"
    assert results[0].snippet == "Descrição da notícia."


def test_gnews_client_does_not_call_api_when_disabled(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "false")

    def blocked_get(*args, **kwargs):
        raise AssertionError(
            "GNews fez uma requisição mesmo estando desativado."
        )

    monkeypatch.setattr(httpx, "get", blocked_get)

    client = GNewsClient(Config())

    results = client.search("teste")

    assert results == []


def test_gnews_client_uses_second_key_when_first_has_no_quota(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    responses = [
        httpx.Response(
            403,
            request=httpx.Request(
                "GET",
                "https://gnews.io/api/v4/search"
            )
        ),
        httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "title": "Notícia com chave 2",
                        "url": "https://exemplo.com/chave-2",
                        "description": "Resultado usando a segunda chave.",
                        "source": {
                            "name": "Fonte de teste"
                        }
                    }
                ]
            },
            request=httpx.Request(
                "GET",
                "https://gnews.io/api/v4/search"
            )
        )
    ]

    calls = []

    def fake_get(url, params=None):
        calls.append(params["apikey"])
        return responses.pop(0)

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    results = client.search("teste")

    assert len(results) == 1
    assert results[0].title == "Notícia com chave 2"

    assert len(calls) == 2
    assert calls[0] == client.config.gnews_api_key
    assert calls[1] == client.config.gnews_api_key2


def test_gnews_client_does_not_use_second_key_for_other_errors(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    calls = []

    fake_response = httpx.Response(
        401,
        request=httpx.Request(
            "GET",
            "https://gnews.io/api/v4/search"
        )
    )

    def fake_get(url, params=None):
        calls.append(params["apikey"])
        return fake_response

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(httpx.HTTPStatusError):
        client.search("teste")

    assert len(calls) == 1
    assert calls[0] == client.config.gnews_api_key


def test_gnews_client_raises_error_when_both_keys_have_no_quota(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    calls = []

    def fake_get(url, params=None):
        calls.append(params["apikey"])

        return httpx.Response(
            403,
            request=httpx.Request(
                "GET",
                "https://gnews.io/api/v4/search"
            )
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(
        RuntimeError,
        match="As duas chaves da GNews estão sem cota disponível."
    ):
        client.search("teste")

    assert len(calls) == 2
    assert calls[0] == client.config.gnews_api_key
    assert calls[1] == client.config.gnews_api_key2
