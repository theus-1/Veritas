import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.rate_limit import RateLimiter
from app.schemas.search import SearchResult
from app.services.evidence_service import EvidenceService
from app.services.search_service import SearchService

CLAIM = "Urna eletronica foi invadida por hackers em teste público de segurança"
DENIAL = "Urna não foi invadida por hackers em teste público de segurança"


def source(title, snippet="", name="G1", index=1):
    return SearchResult(title=title, snippet=snippet, source_name=name, url=f"https://example.com/{index}")


@pytest.mark.parametrize("claim,title,expected", [
    (CLAIM, DENIAL, "CONTRADICTS"),
    (CLAIM, "É falso que " + CLAIM, "CONTRADICTS"),
    (CLAIM, "É FAKE: " + CLAIM, "CONTRADICTS"),
    (CLAIM, "É #FAKE que " + CLAIM, "CONTRADICTS"),
    (CLAIM, "É FATO: " + CLAIM, "SUPPORTS"),
    (DENIAL, "É falso que " + CLAIM, "SUPPORTS"),
    ("Vacina contém microchip", "É falso que vacina contém microchip", "CONTRADICTS"),
    ("Lula morreu", "É falso que Lula morreu", "CONTRADICTS"),
    ("Lula morreu", "Lula não morreu", "CONTRADICTS"),
    ("Empresa recebeu 20 milhões em 2026", "É falso que empresa recebeu 30 milhões em 2026", "NEUTRAL"),
    ("Empresa recebeu 20 milhões em 2026", "É falso que empresa recebeu 20 milhões em 2025", "NEUTRAL"),
    ("Empresa Alfa recebeu recursos", "É falso que empresa Beta recebeu recursos", "NEUTRAL"),
    (CLAIM, DENIAL + "?", "NEUTRAL"),
    (CLAIM, "Se " + DENIAL + ", haverá investigação", "NEUTRAL"),
    (CLAIM, "Circula boato de que " + DENIAL, "NEUTRAL"),
    (CLAIM, "Urna não foi invadida por hackers em teste privado de segurança", "NEUTRAL"),
    ("Alfa atacou Beta", "É falso que Beta atacou Alfa", "NEUTRAL"),
    ("Vacina contém microchip", "É falso que vacina não contém microchip", "SUPPORTS"),
])
def test_explicit_verdict_preserves_proposition_and_scope(claim, title, expected):
    assert EvidenceService().determine_verdict(claim, source(title)).value == expected


def test_snippet_denial_and_conflict():
    service = EvidenceService()
    assert service.determine_verdict(CLAIM, source("Checagem", DENIAL)).value == "CONTRADICTS"
    conflicting = source("É falso que " + CLAIM, "É fato que " + CLAIM)
    assert service.determine_verdict(CLAIM, conflicting).value == "NEUTRAL"


@pytest.mark.parametrize("count,expected", [(1, "PROVAVELMENTE_FALSA"), (2, "FALSA")])
def test_denial_reaches_final_verdict(monkeypatch, count, expected):
    monkeypatch.setattr("app.api.routers.analysis.analysis_rate_limiter", RateLimiter())
    # Full-text exact contradiction from independently named test publishers.
    results = [source(DENIAL, DENIAL, f"Publisher {i}", i) for i in range(count)]
    monkeypatch.setattr(SearchService, "search", lambda *args: results)
    response = TestClient(app).post("/analysis/", json={"title": "Teste de desmentido", "input_text": CLAIM})
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == expected
    assert all(e["verdict"] == "CONTRADICTS" for e in data["evidences"])
    assert data["confidence"] > 0


ROBOT = "Video de Robo de entregas da amazon se jogou no mar"
ROBOT_CHECK = "É falso vídeo de robô de entregas da Amazon se jogando no mar"


@pytest.mark.parametrize("claim,title,expected", [
    (ROBOT, ROBOT_CHECK, "CONTRADICTS"),
    (ROBOT, ROBOT_CHECK.replace("É falso", "É falso o"), "CONTRADICTS"),
    (ROBOT, ROBOT_CHECK.replace("É falso", "É verdadeiro"), "SUPPORTS"),
    (ROBOT, ROBOT_CHECK.replace("Amazon", "OutraEmpresa"), "NEUTRAL"),
    (ROBOT, ROBOT_CHECK.replace("mar", "rio"), "NEUTRAL"),
    (ROBOT, ROBOT_CHECK + "?", "NEUTRAL"),
    (ROBOT, "Se " + ROBOT_CHECK, "NEUTRAL"),
    (ROBOT, "Vídeo mostra robô identificando um pacote falso", "NEUTRAL"),
    ("Robô de entregas da Amazon se jogou no mar", ROBOT_CHECK, "NEUTRAL"),
    ("Foto de nave no mar", "É falsa foto de nave no mar", "CONTRADICTS"),
    ("Imagem de nave no mar", "É falsa imagem de nave no mar", "CONTRADICTS"),
    (ROBOT + " em 2026", ROBOT_CHECK + " em 2025", "NEUTRAL"),
])
def test_media_fact_check_scope(claim, title, expected):
    assert EvidenceService().determine_verdict(claim, source(title)).value == expected


def test_robot_screenshot_reaches_probably_false(monkeypatch):
    monkeypatch.setattr("app.api.routers.analysis.analysis_rate_limiter", RateLimiter())
    monkeypatch.setattr(SearchService, "search", lambda *args: [source(ROBOT_CHECK)])
    response = TestClient(app).post("/analysis/", json={"title": "Teste robo", "input_text": ROBOT})
    assert response.status_code == 200
    assert response.json()["verdict"] == "PROVAVELMENTE_FALSA"
    assert response.json()["evidences"][0]["verdict"] == "CONTRADICTS"
