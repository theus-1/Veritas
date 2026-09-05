from app.core.database import SessionLocal
from app.schemas.analysis import AnalysisCreate
from app.services.analysis_service import AnalysisService
from app.models.analysis import VerdictEnum, StatusEnum


def test_create_analysis_complete_flow():
    db = SessionLocal()
    service = AnalysisService()

    data = AnalysisCreate(
        title="Notícia de teste",
        input_text="O Brasil ganhou o jogo. A partida terminou ontem."
    )

    analysis = service.create_analysis(db, data)

    assert analysis.confidence == 0.0
    assert analysis.verdict == VerdictEnum.FALSA
    assert analysis.status == StatusEnum.COMPLETED
    assert len(analysis.claims) == 2

    db.close()
