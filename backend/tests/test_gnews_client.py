import httpx
import pytest

from app.clients.gnews_client import GNewsClient
from app.core.config import Config
from app.core.exceptions import ExternalServiceException


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
                    },
                }
            ]
        },
        request=httpx.Request(
            "GET",
            "https://gnews.io/api/v4/search",
        ),
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


def test_gnews_client_uses_second_key_when_first_has_no_quota(
    monkeypatch,
):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    responses = [
        httpx.Response(
            403,
            request=httpx.Request(
                "GET",
                "https://gnews.io/api/v4/search",
            ),
        ),
        httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "title": "Notícia com chave 2",
                        "url": "https://exemplo.com/chave-2",
                        "description": (
                            "Resultado usando a segunda chave."
                        ),
                        "source": {
                            "name": "Fonte de teste"
                        },
                    }
                ]
            },
            request=httpx.Request(
                "GET",
                "https://gnews.io/api/v4/search",
            ),
        ),
    ]

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params["apikey"])
        return responses.pop(0)

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    results = client.search("teste")

    assert len(results) == 1
    assert results[0].title == "Notícia com chave 2"

    assert calls == [
        client.config.parsed_gnews_api_keys[0],
        client.config.parsed_gnews_api_keys[1],
    ]


def test_gnews_client_tries_all_keys_for_auth_errors(
    monkeypatch,
):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    calls = []

    fake_response = httpx.Response(
        401,
        request=httpx.Request(
            "GET",
            "https://gnews.io/api/v4/search",
        ),
    )

    def fake_get(url, params=None, timeout=None):
        calls.append(params["apikey"])
        return fake_response

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(
        ExternalServiceException
    ) as exc_info:
        client.search("teste")

    assert exc_info.value.code == "GNEWS_AUTH_ERROR"

    assert calls == [
        client.config.parsed_gnews_api_keys[0],
        client.config.parsed_gnews_api_keys[1],
    ]


def test_gnews_client_raises_error_when_both_keys_have_no_quota(
    monkeypatch,
):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    calls = []

    def fake_get(url, params=None, timeout=None):
        calls.append(params["apikey"])

        return httpx.Response(
            403,
            request=httpx.Request(
                "GET",
                "https://gnews.io/api/v4/search",
            ),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(
        ExternalServiceException,
        match="A cota da GNews está indisponível no momento.",
    ) as exc_info:
        client.search("teste")

    assert exc_info.value.status_code == 503
    assert exc_info.value.code == "GNEWS_QUOTA_EXCEEDED"

    assert calls == [
        client.config.parsed_gnews_api_keys[0],
        client.config.parsed_gnews_api_keys[1],
    ]


def test_gnews_client_inspects_real_response(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    captured = {}

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "articles": [
                    {
                        "title": "Teste",
                        "url": "https://exemplo.com",
                        "source": {
                            "name": "Fonte de teste"
                        },
                        "description": "Descrição de teste",
                    }
                ]
            }

    def fake_get(url, params=None, timeout=None):
        captured["url"] = url
        captured["params"] = params
        captured["timeout"] = timeout

        return FakeResponse()

    monkeypatch.setattr(
        "app.clients.gnews_client.httpx.get",
        fake_get,
    )

    client = GNewsClient(Config())

    results = client.search(
        "Produto Interno Bruto Brasil cresceu "
        "0 5 segundo trimestre 2026"
    )

    assert len(results) == 1

    assert captured["url"] == (
        f"{client.config.gnews_base_url}/search"
    )

    assert captured["params"]["q"] == (
        "Produto Interno Bruto Brasil cresceu "
        "0 5 segundo trimestre 2026"
    )

    assert captured["timeout"] == client.REQUEST_TIMEOUT


def test_gnews_client_handles_timeout(monkeypatch):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    def fake_get(url, params=None, timeout=None):
        request = httpx.Request(
            "GET",
            url,
        )

        raise httpx.TimeoutException(
            "Timeout",
            request=request,
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(
        ExternalServiceException
    ) as exc_info:
        client.search("PIB Brasil")

    assert exc_info.value.code == "GNEWS_TIMEOUT"
    assert exc_info.value.status_code == 503


def test_gnews_client_handles_connection_error(
    monkeypatch,
):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    def fake_get(url, params=None, timeout=None):
        request = httpx.Request(
            "GET",
            url,
        )

        raise httpx.ConnectError(
            "Connection failed",
            request=request,
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(
        ExternalServiceException
    ) as exc_info:
        client.search("PIB Brasil")

    assert (
        exc_info.value.code
        == "GNEWS_CONNECTION_ERROR"
    )

    assert exc_info.value.status_code == 503


def test_gnews_client_handles_server_error(
    monkeypatch,
):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(
            503,
            request=httpx.Request(
                "GET",
                url,
            ),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(
        ExternalServiceException
    ) as exc_info:
        client.search("PIB Brasil")

    assert exc_info.value.code == "GNEWS_UNAVAILABLE"
    assert exc_info.value.status_code == 503


def test_gnews_client_handles_invalid_json(
    monkeypatch,
):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(
            200,
            content=b"isso nao e json",
            request=httpx.Request(
                "GET",
                url,
            ),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    with pytest.raises(
        ExternalServiceException
    ) as exc_info:
        client.search("PIB Brasil")

    assert (
        exc_info.value.code
        == "GNEWS_INVALID_RESPONSE"
    )

    assert exc_info.value.status_code == 503


def test_gnews_client_ignores_invalid_articles(
    monkeypatch,
):
    monkeypatch.setenv("GNEWS_ENABLED", "true")

    def fake_get(url, params=None, timeout=None):
        return httpx.Response(
            200,
            json={
                "articles": [
                    {
                        "title": "Notícia válida",
                        "url": "https://example.com/noticia",
                        "description": "Descrição",
                        "source": {
                            "name": "Fonte válida",
                        },
                    },
                    {
                        "title": None,
                        "url": None,
                        "source": {},
                    },
                ]
            },
            request=httpx.Request(
                "GET",
                url,
            ),
        )

    monkeypatch.setattr(httpx, "get", fake_get)

    client = GNewsClient(Config())

    results = client.search("PIB Brasil")

    assert len(results) == 1
    assert results[0].title == "Notícia válida"


@pytest.mark.parametrize("statuses,code", [
    ([403, 401, 200], None), ([401, 200], None),
    ([403, 403, 403], "GNEWS_QUOTA_EXCEEDED"),
    ([401, 401, 401], "GNEWS_AUTH_ERROR"),
    ([401, 403, 401], "GNEWS_QUOTA_EXCEEDED"),
    ([429, 429], "GNEWS_RATE_LIMIT"), ([503], "GNEWS_UNAVAILABLE"),
])
def test_pool_failover_and_no_rotation_on_global_errors(monkeypatch, statuses, code):
    config = Config(gnews_enabled=True, gnews_api_keys="one,two,three")
    calls = []
    responses = iter(statuses)
    def get(*args, **kwargs):
        calls.append(kwargs["params"]["apikey"])
        return httpx.Response(next(responses), json={"articles": []})
    monkeypatch.setattr(httpx, "get", get)
    client = GNewsClient(config)
    if code:
        with pytest.raises(ExternalServiceException) as error:
            client.search("test")
        assert error.value.code == code
        assert error.value.status_code == 503
    else:
        assert client.search("test") == []
    expected = ["one", "one"] if statuses[0] == 429 else ["one", "two", "three"][:len(statuses)]
    assert calls == expected


@pytest.mark.parametrize("raw", ["", " , , "])
def test_empty_pool_is_structured_without_network(raw):
    with pytest.raises(ExternalServiceException) as error:
        GNewsClient(Config(gnews_enabled=True, gnews_api_keys=raw)).search("test")
    assert error.value.code == "GNEWS_CONFIG_ERROR"


@pytest.mark.parametrize("failure,code", [(httpx.ReadTimeout, "GNEWS_TIMEOUT"), (httpx.ConnectError, "GNEWS_CONNECTION_ERROR")])
def test_transport_errors_do_not_rotate_pool(monkeypatch, failure, code):
    calls = []
    def get(*args, **kwargs):
        calls.append(kwargs["params"]["apikey"])
        raise failure("private transport details")
    monkeypatch.setattr(httpx, "get", get)
    with pytest.raises(ExternalServiceException) as error:
        GNewsClient(Config(gnews_enabled=True)).search("test")
    assert error.value.code == code
    assert "private" not in str(error.value)
    assert calls == ["dummy-one"]
