from datetime import datetime
from uuid import UUID

import pytest
from pydantic import ValidationError

from app.models.analysis import StatusEnum, VerdictEnum
from app.schemas.analysis import AnalysisCreate, AnalysisResponse


def test_analysis_create_with_valid_data():

    data = AnalysisCreate(
        title="Notícia de teste",
        input_text="Conteúdo da notícia.",
        input_url="https://exemplo.com/noticia"
    )

    assert data.title == "Notícia de teste"
    assert data.input_text == "Conteúdo da notícia."
    assert data.input_url == "https://exemplo.com/noticia"


def test_analysis_create_without_url():

    data = AnalysisCreate(
        title="Notícia de teste",
        input_text="Conteúdo da notícia."
    )

    assert data.input_url is None


def test_analysis_response_with_valid_data():

    data = AnalysisResponse(
        id=UUID("cbe0d0d8-da2d-4eed-a360-88c677da4a61"),
        title="Notícia de teste",
        input_text="Conteúdo da notícia.",
        input_url=None,
        verdict=VerdictEnum.VERDADEIRA,
        confidence=0.95,
        explanation="As fontes encontradas confirmam a informação.",
        status=StatusEnum.COMPLETED,
        created_at=datetime(2026, 9, 3, 20, 0, 0)
    )

    assert data.id == UUID("cbe0d0d8-da2d-4eed-a360-88c677da4a61")
    assert data.verdict == VerdictEnum.VERDADEIRA
    assert data.confidence == 0.95
    assert data.status == StatusEnum.COMPLETED


def test_analysis_response_rejects_invalid_verdict():

    with pytest.raises(ValidationError):

        AnalysisResponse(
            id=UUID("cbe0d0d8-da2d-4eed-a360-88c677da4a61"),
            title="Notícia de teste",
            input_text="Conteúdo da notícia.",
            verdict="TALVEZ",
            confidence=0.5,
            explanation="Não foi possível determinar.",
            status=StatusEnum.COMPLETED,
            created_at=datetime(2026, 9, 3, 20, 0, 0)
        )


def test_analysis_create_requires_title():

    with pytest.raises(ValidationError):

        AnalysisCreate(
            input_text="Conteúdo da notícia."
        )


def test_analysis_create_requires_input_text():

    with pytest.raises(ValidationError):

        AnalysisCreate(
            title="Notícia de teste"
        )
