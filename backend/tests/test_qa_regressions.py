from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import Mock

import httpx
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.config import Config
from app.core.database import SessionLocal
from app.core.exceptions import ExternalServiceException
from app.core.rate_limit import RateLimiter
from app.clients.gnews_client import GNewsClient
from app.models.analysis import Analysis, VerdictEnum
from app.models.evidence import EvidenceVerdictEnum
from app.schemas.search import SearchResult
from app.services.analysis_service import AnalysisService
from app.services.claim_service import ClaimService
from app.services.evidence_service import EvidenceService
from app.services.search_service import SearchService


@pytest.fixture(autouse=True)
def fresh_limiter(monkeypatch):
    limiter = RateLimiter()
    monkeypatch.setattr("app.api.routers.analysis.analysis_rate_limiter", limiter)
    monkeypatch.setattr(GNewsClient, "REQUEST_DELAY", 0)
    return limiter


@pytest.mark.parametrize("field,value", [
    ("input_text", "A" * 10001), ("input_text", "A" * 9),
    ("title", "A" * 301), ("title", "AB"), ("input_url", "u" * 2001),
], ids=["text-too-long", "text-too-short", "title-too-long", "title-too-short", "url-too-long"])
def test_validation_precedes_persistence_and_gnews(monkeypatch, field, value):
    search = Mock(side_effect=AssertionError("External call forbidden"))
    create = Mock(side_effect=AssertionError("Persistence forbidden"))
    monkeypatch.setattr(GNewsClient, "search", search)
    monkeypatch.setattr("app.repositories.analysis_repository.AnalysisRepository.create", create)
    payload = {"title": "Teste", "input_text": "Texto de teste válido", "input_url": None}
    payload[field] = value
    response = TestClient(app).post("/analysis/", json=payload)
    assert response.status_code == 422
    search.assert_not_called()
    create.assert_not_called()


def test_schema_accepts_exact_maximum_lengths():
    from app.schemas.analysis import AnalysisCreate
    data = AnalysisCreate(title="T" * 300, input_text="A" * 10000, input_url="u" * 2000)
    assert len(data.input_text) == 10000


def test_sixth_request_never_calls_gnews_or_creates_analysis(monkeypatch):
    search = Mock(return_value=[])
    monkeypatch.setattr(GNewsClient, "search", search)
    client = TestClient(app)
    payload = {"title": "Teste", "input_text": "PIB do Brasil cresceu 0,5%."}
    for _ in range(5):
        assert client.post("/analysis/", json=payload).status_code == 200
    before = search.call_count
    assert before > 0
    with SessionLocal() as db:
        rows = db.query(Analysis).count()
    response = client.post("/analysis/", json=payload)
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_MINUTE"
    assert search.call_count == before
    with SessionLocal() as db:
        assert db.query(Analysis).count() == rows


def test_hour_limit_precedes_gnews(monkeypatch, fresh_limiter):
    fresh_limiter.requests["testclient"].extend([datetime.now(UTC) - timedelta(minutes=2)] * 30)
    search = Mock(return_value=[])
    monkeypatch.setattr(GNewsClient, "search", search)
    response = TestClient(app).post("/analysis/", json={"title": "Teste", "input_text": "Texto de teste válido"})
    assert response.status_code == 429
    assert response.json()["error"]["code"] == "RATE_LIMIT_HOUR"
    search.assert_not_called()


def test_ten_claims_and_three_queries_maximum(monkeypatch):
    monkeypatch.setattr(SearchService, "_build_queries", lambda *a: ["one", "two", "three", "four"])
    search = Mock(return_value=[])
    monkeypatch.setattr(GNewsClient, "search", search)
    response = TestClient(app).post("/analysis/", json={"title": "Teste", "input_text": ". ".join(f"Empresa anunciou investimento {i}" for i in range(12))})
    assert response.status_code == 200
    assert len(response.json()["claims"]) == 10
    assert search.call_count == 30
    assert response.json()["verdict"] == "INCONCLUSIVA"
    assert response.json()["confidence"] is None


def test_decimal_does_not_split_claim():
    assert ClaimService().extract_claims("PIB cresceu 0.5%. Inflação caiu 0,2%.") == ["PIB cresceu 0.5%", "Inflação caiu 0,2%"]


@pytest.mark.parametrize("claim,evidence,expected", [
    ("PIB caiu 8%", "PIB cresceu 0,5%", "CONTRADICTS"),
    ("O Produto Interno Bruto do Brasil caiu 8% no segundo trimestre de 2026 em relação ao primeiro trimestre", "PIB do Brasil cresceu 0,5% no 2º trimestre de 2026 em relação ao primeiro trimestre", "CONTRADICTS"),
    ("PIB cresceu 8%", "PIB cresceu 0,5%", "CONTRADICTS"),
    ("PIB cresceu 0.5%", "PIB cresceu 0,5%", "SUPPORTS"),
    ("PIB do Brasil caiu 8%", "PIB da Argentina cresceu 0,5%", "NEUTRAL"),
    ("PIB caiu 8% em 2026", "PIB cresceu 0,5% em 2025", "NEUTRAL"),
    ("PIB caiu 8% no segundo trimestre", "PIB cresceu 0,5% no primeiro trimestre", "NEUTRAL"),
    ("PIB caiu 8% no segundo trimestre em relação ao primeiro trimestre", "PIB cresceu 0,5% no segundo trimestre em relação ao ano anterior", "NEUTRAL"),
    ("PIB caiu 8%", "Inflação cresceu 0,5%", "NEUTRAL"),
    ("PIB caiu 8% em janeiro", "PIB cresceu 0,5% em fevereiro", "NEUTRAL"),
    ("PIB caiu 8%", "PIB não cresceu 0,5%", "NEUTRAL"),
    ("PIB cresceu 8%", "PIB cresceu", "NEUTRAL"),
    ("PIB caiu 8% em 2026", "PIB cresceu 0,5%", "NEUTRAL"),
    ("Brasil ganhou da Argentina", "Brasil perdeu para Argentina", "CONTRADICTS"),
])
def test_direction_numbers_and_context(claim, evidence, expected):
    result = SearchResult(title=evidence, snippet=evidence, url="https://example.com/news", source_name="Fonte")
    assert EvidenceService().determine_verdict(claim, result).value == expected


def evidence(relevance, direction, source):
    return SimpleNamespace(relevance=relevance, verdict=direction, source_name=source, claim_id="claim")


@pytest.mark.parametrize("direction,probable,definitive", [
    ("SUPPORTS", VerdictEnum.PROVAVELMENTE_VERDADEIRA, VerdictEnum.VERDADEIRA),
    ("CONTRADICTS", VerdictEnum.PROVAVELMENTE_FALSA, VerdictEnum.FALSA),
])
def test_calibration_is_symmetric_and_quality_weighted(direction, probable, definitive):
    service = AnalysisService()
    weak = [evidence(.29, direction, "A"), evidence(.27, direction, "B")]
    assert service.calculate_confidence(weak) < .30
    assert service.generate_verdict(weak) == probable
    strong = [evidence(.95, direction, "A"), evidence(.90, direction, "B")]
    assert service.generate_verdict(strong) == definitive
    assert .8 <= service.calculate_confidence(strong) <= .95
    duplicated = [evidence(.95, direction, "A")] * 10
    assert service.generate_verdict(duplicated) == probable
    assert service.calculate_confidence(duplicated) < .8


def test_conflict_and_missing_evidence():
    service = AnalysisService()
    assert service.generate_verdict([]) == VerdictEnum.INCONCLUSIVA
    assert service.calculate_confidence([]) is None
    neutral = [evidence(.99, "NEUTRAL", "A")]
    assert service.generate_verdict(neutral) == VerdictEnum.INCONCLUSIVA
    assert service.calculate_confidence(neutral) is None
    conflict = [evidence(.9, "SUPPORTS", "A"), evidence(.9, "CONTRADICTS", "B")]
    assert service.generate_verdict(conflict) == VerdictEnum.INCONCLUSIVA
    assert service.calculate_confidence(conflict) == 0
    dominant = [evidence(.95, "CONTRADICTS", "A"), evidence(.9, "CONTRADICTS", "B"), evidence(.2, "SUPPORTS", "C")]
    assert service.generate_verdict(dominant) == VerdictEnum.PROVAVELMENTE_FALSA


@pytest.mark.parametrize("statuses,code", [([401, 401], "GNEWS_AUTH_ERROR"), ([429, 429], "GNEWS_RATE_LIMIT"), ([500], "GNEWS_UNAVAILABLE"), ([403, 403], "GNEWS_QUOTA_EXCEEDED")])
def test_gnews_errors_reach_endpoint_structured(monkeypatch, statuses, code):
    monkeypatch.setenv("GNEWS_ENABLED", "true")
    responses = iter(statuses)
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(next(responses)))
    response = TestClient(app).post("/analysis/", json={"title": "Teste", "input_text": "PIB Brasil cresceu"})
    assert response.status_code == 503
    assert response.json()["error"]["code"] == code
    assert response.json()["error"]["message"]


def test_fallback_logs_only_attempt_and_status(monkeypatch, caplog):
    config = Config(_env_file=None, gnews_enabled=True, gnews_api_keys="dummy-one,dummy-two")
    calls = []
    def get(*args, **kwargs):
        calls.append(kwargs["params"]["apikey"])
        return httpx.Response(403 if len(calls) == 1 else 200, json={"articles": []})
    monkeypatch.setattr(httpx, "get", get)
    with caplog.at_level("INFO", logger="app.clients.gnews_client"):
        assert GNewsClient(config).search("private query") == []
    assert calls == ["dummy-one", "dummy-two"]
    assert [r.message for r in caplog.records if r.name == "app.clients.gnews_client"] == ["tentativa=1 status=403", "tentativa=2 status=200"]
    assert "dummy" not in caplog.text
    assert "private query" not in caplog.text


@pytest.mark.parametrize("payload", [{}, {"articles": None}, [], {"articles": "bad"}])
def test_invalid_json_shape_is_structured(monkeypatch, payload):
    monkeypatch.setattr(httpx, "get", lambda *a, **k: httpx.Response(200, json=payload))
    with pytest.raises(ExternalServiceException) as error:
        GNewsClient(Config(_env_file=None, gnews_enabled=True)).search("PIB")
    assert error.value.code == "GNEWS_INVALID_RESPONSE"
