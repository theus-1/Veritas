from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.main import (
    unexpected_exception_handler,
    veritas_exception_handler,
)

from app.core.exceptions import (
    ExternalServiceException,
    VeritasException,
)


def create_test_app():
    app = FastAPI()

    app.add_exception_handler(VeritasException, veritas_exception_handler)
    app.add_exception_handler(Exception, unexpected_exception_handler)

    @app.get("/known-error")
    def known_error():
        raise VeritasException(
            message="Erro conhecido.",
            status_code=400,
            code="KNOWN_ERROR",
        )

    @app.get("/external-error")
    def external_error():
        raise ExternalServiceException(
            message="Serviço indisponível.",
            code="SERVICE_UNAVAILABLE",
        )

    @app.get("/unexpected-error")
    def unexpected_error():
        raise RuntimeError("Erro interno sensível")

    return app


def test_veritas_exception_handler():
    client = TestClient(
        create_test_app(),
        raise_server_exceptions=False,
    )

    response = client.get("/known-error")

    assert response.status_code == 400

    data = response.json()

    assert data == {
        "error": {
            "code": "KNOWN_ERROR",
            "message": "Erro conhecido.",
        }
    }


def test_external_service_exception_handler():
    client = TestClient(
        create_test_app(),
        raise_server_exceptions=False,
    )

    response = client.get("/external-error")

    assert response.status_code == 503

    data = response.json()

    assert data["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert data["error"]["message"] == "Serviço indisponível."


def test_unexpected_exception_does_not_expose_details():
    client = TestClient(
        create_test_app(),
        raise_server_exceptions=False,
    )

    response = client.get("/unexpected-error")

    assert response.status_code == 500

    data = response.json()

    assert data == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "Ocorreu um erro interno no servidor.",
        }
    }

    assert "Erro interno sensível" not in response.text
