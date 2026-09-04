from app.core.database import SessionLocal
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import AnalysisCreate


def test_create_analysis():
    db = SessionLocal()
    repository = AnalysisRepository()

    data = AnalysisCreate(
        title="Notícia de teste",
        input_text="Conteúdo da notícia de teste.",
        input_url="https://exemplo.com/noticia"
    )

    analysis = repository.create(db, data)

    assert analysis is not None
    assert analysis.id is not None
    assert analysis.title == "Notícia de teste"
    assert analysis.input_text == "Conteúdo da notícia de teste."
    assert analysis.input_url == "https://exemplo.com/noticia"

    db.close()
