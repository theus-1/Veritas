from app.core.database import SessionLocal
from app.models.analysis import StatusEnum, VerdictEnum
from app.schemas.analysis import AnalysisCreate
from app.schemas.search import SearchResult
from app.services.analysis_service import AnalysisService


def test_complete_analysis_flow(monkeypatch):

    def fake_search(self, query):
        return [
            SearchResult(
                title="Brasil vence partida",
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
        title="Brasil vence partida",
        input_text="O Brasil ganhou o jogo."
    )

    analysis = service.create_analysis(
        db=db,
        data=data
    )

    assert analysis is not None

    # Análise
    assert analysis.title == "Brasil vence partida"
    assert analysis.input_text == "O Brasil ganhou o jogo."
    assert analysis.status == StatusEnum.COMPLETED

    # Claims
    assert len(analysis.claims) == 1
    assert analysis.claims[0].text == "O Brasil ganhou o jogo"

    # Evidências
    assert len(analysis.evidences) == 1

    evidence = analysis.evidences[0]

    assert evidence.analysis_id == analysis.id
    assert evidence.claim_id == analysis.claims[0].id
    assert evidence.source_name == "Fonte de teste"
    assert evidence.source_url == "https://exemplo.com/brasil"
    assert evidence.title == "Brasil vence partida"

    # Relevância
    assert evidence.relevance >= 0.0
    assert evidence.relevance <= 1.0

    # Resultado da análise
    assert analysis.confidence >= 0.0
    assert analysis.confidence <= 1.0

    assert analysis.verdict in [
        VerdictEnum.FALSA,
        VerdictEnum.PROVAVELMENTE_FALSA,
        VerdictEnum.INCONCLUSIVA,
        VerdictEnum.PROVAVELMENTE_VERDADEIRA,
        VerdictEnum.VERDADEIRA,
    ]

    db.close()
