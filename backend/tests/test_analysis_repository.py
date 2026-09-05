from app.core.database import SessionLocal
from app.models.analysis import Analysis, StatusEnum
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import AnalysisCreate


def test_create_analysis_repository():

    db = SessionLocal()

    repository = AnalysisRepository()

    data = AnalysisCreate(
        title="Análise pelo Repository",
        input_text="O Brasil ganhou o jogo.",
        input_url="https://exemplo.com/noticia"
    )

    analysis = repository.create(
        db=db,
        data=data
    )

    assert analysis is not None
    assert analysis.id is not None
    assert analysis.title == "Análise pelo Repository"
    assert analysis.input_text == "O Brasil ganhou o jogo."
    assert analysis.input_url == "https://exemplo.com/noticia"
    assert analysis.status == StatusEnum.PENDING
    assert analysis.created_at is not None

    db.close()


def test_create_analysis_without_url():

    db = SessionLocal()

    repository = AnalysisRepository()

    data = AnalysisCreate(
        title="Análise sem URL",
        input_text="Conteúdo da notícia."
    )

    analysis = repository.create(
        db=db,
        data=data
    )

    assert analysis is not None
    assert analysis.id is not None
    assert analysis.title == "Análise sem URL"
    assert analysis.input_url is None
    assert analysis.status == StatusEnum.PENDING

    db.close()
