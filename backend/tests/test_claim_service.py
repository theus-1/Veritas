from app.core.database import SessionLocal
from app.models.analysis import Analysis, StatusEnum
from app.services.claim_service import ClaimService
from app.models.evidence import Evidence
import pytest

def test_create_claims():
    db = SessionLocal()
    service = ClaimService()

    analysis = Analysis(
        title="Notícia de teste",
        input_text="O Brasil ganhou. A partida terminou ontem.",
        status=StatusEnum.PENDING
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    claims = [
        "O Brasil ganhou",
        "A partida terminou ontem"
    ]

    created_claims = service.create_claims(
        db=db,
        analysis=analysis,
        claims=claims
    )

    assert len(created_claims) == 2
    assert created_claims[0].text == "O Brasil ganhou"
    assert created_claims[1].text == "A partida terminou ontem"

    assert created_claims[0].analysis_id == analysis.id
    assert created_claims[1].analysis_id == analysis.id

    db.close()

def test_calculate_confidence():
    service = ClaimService()

    evidences = [
        Evidence(relevance=0.9),
        Evidence(relevance=0.8),
        Evidence(relevance=0.7)
    ]

    confidence = service.calculate_confidence(evidences)

    assert confidence == pytest.approx(0.8)

def test_calculate_confidence_with_one_evidence():
    service = ClaimService()

    evidences = [
        Evidence(relevance=0.9)
    ]

    confidence = service.calculate_confidence(evidences)

    assert confidence == 0.9


def test_calculate_confidence_without_evidences():
    service = ClaimService()

    confidence = service.calculate_confidence([])

    assert confidence == 0.0
