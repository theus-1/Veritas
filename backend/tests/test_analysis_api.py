from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_create_analysis_success(monkeypatch):

    def fake_search(self, query):
        return []

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    response = client.post(
        "/analysis/",
        json={
            "title": "Notícia de teste",
            "input_text": "A água ferve a 100 graus Celsius ao nível do mar.",
            "input_url": "https://exemplo.com/teste"
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["title"] == "Notícia de teste"
    assert data["input_text"] == (
        "A água ferve a 100 graus Celsius ao nível do mar."
    )
    assert data["input_url"] == "https://exemplo.com/teste"
    assert data["status"] == "Completa"


def test_create_analysis_without_url(monkeypatch):

    def fake_search(self, query):
        return []

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    response = client.post(
        "/analysis/",
        json={
            "title": "Notícia sem URL",
            "input_text": "Conteúdo da notícia."
        }
    )

    assert response.status_code == 200

    data = response.json()

    assert "id" in data
    assert data["input_url"] is None
    assert data["status"] == "Completa"


def test_create_analysis_invalid_data():

    response = client.post(
        "/analysis/",
        json={
            "title": "Notícia inválida"
        }
    )

    assert response.status_code == 422
