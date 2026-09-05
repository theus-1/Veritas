from app.core.database import SessionLocal
from app.models.analysis import StatusEnum, VerdictEnum
from app.schemas.analysis import AnalysisCreate
from app.schemas.search import SearchResult
from app.services.analysis_service import AnalysisService


def test_create_analysis_complete_flow(monkeypatch):

    def fake_search(self, query):
        return [
            SearchResult(
                title="Brasil ganhou o jogo",
                url="https://exemplo.com/brasil",
                source_name="Fonte de teste",
                snippet="O Brasil ganhou o jogo."
            )
        ]

    monkeypatch.setattr(
        "app.clients.gnews_client.GNewsClient.search",
        fake_search
    )

    db = SessionLocal()
    service = AnalysisService()

    data = AnalysisCreate(
        title="Notícia de teste",
        input_text="O Brasil ganhou o jogo. A partida terminou ontem."
    )

    analysis = service.create_analysis(db, data)

    assert analysis is not None
    assert analysis.id is not None
    assert analysis.title == "Notícia de teste"

    assert len(analysis.claims) == 2
    assert len(analysis.evidences) == 2

    # Uma única fonte não permite certeza definitiva.
    assert 0 < analysis.confidence < 0.8

    assert analysis.verdict == VerdictEnum.PROVAVELMENTE_VERDADEIRA
    assert analysis.status == StatusEnum.COMPLETED

    db.close()
