from collections import Counter
from types import SimpleNamespace
from unittest.mock import Mock

from fastapi.testclient import TestClient
from app.main import app
from app.core.rate_limit import RateLimiter
from app.models.evidence import EvidenceVerdictEnum as V
from app.schemas.search import SearchResult
from app.services.evidence_service import EvidenceService
from app.services.search_service import SearchService


def result(title, url=None):
    return SearchResult(title=title, url=url or "https://example.com/" + title, source_name="Test", snippet="")


def test_priority_relevance_deduplication_and_persistence(monkeypatch):
    service = EvidenceService()
    scores = {"neutral": (.99, V.NEUTRAL), "weak": (.3, V.SUPPORTS), "strong": (.9, V.CONTRADICTS), "duplicate": (.8, V.SUPPORTS), "n2": (.8, V.NEUTRAL), "n3": (.7, V.NEUTRAL), "n4": (.6, V.NEUTRAL)}
    monkeypatch.setattr(service, "calculate_relevance", lambda _, r: scores[r.title][0])
    monkeypatch.setattr(service, "determine_verdict", lambda _, r: scores[r.title][1])
    inputs = [result(name, "https://example.com/shared" if name in {"weak", "duplicate"} else None) for name in scores]
    db = Mock()
    evidences = service.create_evidences(db, SimpleNamespace(id=1), SimpleNamespace(id=2, text="claim"), inputs)
    assert [e.title for e in evidences] == ["strong", "duplicate", "neutral", "n2", "n3"]
    assert len({e.source_url for e in evidences}) == 5
    assert db.add.call_count == 5
    assert db.refresh.call_count == 5


def test_ten_claims_persist_at_most_fifty_evidences(monkeypatch):
    monkeypatch.setattr("app.api.routers.analysis.analysis_rate_limiter", RateLimiter())
    monkeypatch.setattr(SearchService, "search", lambda *args: [result(str(i)) for i in range(12)])
    response = TestClient(app).post("/analysis/", json={"title": "Test limits", "input_text": ". ".join(f"Empresa anunciou investimento {i}" for i in range(10))})
    assert response.status_code == 200
    data = response.json()
    assert len(data["claims"]) == 10
    assert len(data["evidences"]) == 50
    assert set(Counter(e["claim_id"] for e in data["evidences"]).values()) == {5}
    assert data["verdict"] == "INCONCLUSIVA"


def test_empty_evidence_does_not_persist():
    db = Mock()
    assert EvidenceService().create_evidences(db, SimpleNamespace(id=1), SimpleNamespace(id=2, text="claim"), []) == []
    db.add.assert_not_called()
