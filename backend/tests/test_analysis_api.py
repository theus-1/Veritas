from fastapi.testclient import TestClient

from app.main import app
from app.models.analysis import StatusEnum, VerdictEnum

client = TestClient(app)


def test_create_analysis_endpoint_success(monkeypatch):
    class FakeAnalysis:
        id = "123e4567-e89b-12d3-a456-426614174000"
        title = "PIB do Brasil cresce"
        input_text = (
            "O Produto Interno Bruto do Brasil cresceu "
            "0,5% no segundo trimestre de 2026."
        )
        input_url = None
        verdict = VerdictEnum.PROVAVELMENTE_VERDADEIRA
        confidence = 0.9
        explanation = None
        status = StatusEnum.COMPLETED
        created_at = "2026-09-05T12:00:00"

        claims = []
        evidences = []

    def fake_create_analysis(self, db, data):
        return FakeAnalysis()

    monkeypatch.setattr(
        "app.api.routers.analysis.AnalysisService.create_analysis",
        fake_create_analysis,
    )

    response = client.post(
        "/analysis/",
        json={
            "title": "PIB do Brasil cresce",
            "input_text": (
                "O Produto Interno Bruto do Brasil cresceu "
                "0,5% no segundo trimestre de 2026."
            ),
            "input_url": None,
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["title"] == "PIB do Brasil cresce"
    assert data["verdict"] == "PROVAVELMENTE_VERDADEIRA"
    assert data["confidence"] == 0.9
    assert data["status"] == "Completa"


def test_create_analysis_endpoint_requires_title():
    response = client.post(
        "/analysis/",
        json={
            "input_text": "Texto da notícia",
            "input_url": None,
        },
    )

    assert response.status_code == 422


def test_create_analysis_endpoint_requires_input_text():
    response = client.post(
        "/analysis/",
        json={
            "title": "Título da notícia",
            "input_url": None,
        },
    )

    assert response.status_code == 422


def test_create_analysis_endpoint_accepts_optional_url(monkeypatch):
    class FakeAnalysis:
        id = "123e4567-e89b-12d3-a456-426614174001"
        title = "Notícia de teste"
        input_text = "Texto da notícia"
        input_url = "https://example.com/noticia"
        verdict = VerdictEnum.INCONCLUSIVA
        confidence = None
        explanation = None
        status = StatusEnum.COMPLETED
        created_at = "2026-09-05T12:00:00"

        claims = []
        evidences = []

    def fake_create_analysis(self, db, data):
        return FakeAnalysis()

    monkeypatch.setattr(
        "app.api.routers.analysis.AnalysisService.create_analysis",
        fake_create_analysis,
    )

    response = client.post(
        "/analysis/",
        json={
            "title": "Notícia de teste",
            "input_text": "Texto da notícia",
            "input_url": "https://example.com/noticia",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["input_url"] == "https://example.com/noticia"
    assert data["confidence"] is None
    assert data["verdict"] == "INCONCLUSIVA"


def test_create_analysis_endpoint_rejects_invalid_body():
    response = client.post(
        "/analysis/",
        json={},
    )

    assert response.status_code == 422
