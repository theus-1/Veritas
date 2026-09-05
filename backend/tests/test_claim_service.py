from app.core.database import SessionLocal
from app.models.analysis import StatusEnum, VerdictEnum
from app.schemas.analysis import AnalysisCreate
from app.services.analysis_service import AnalysisService
from app.services.claim_service import ClaimService


def test_extract_multiple_claims():

    service = ClaimService()

    text = "O Brasil ganhou o jogo. A partida terminou ontem."

    claims = service.extract_claims(text)

    assert claims == [
        "O Brasil ganhou o jogo",
        "A partida terminou ontem"
    ]


def test_extract_single_claim():

    service = ClaimService()

    text = "O Brasil ganhou o jogo."

    claims = service.extract_claims(text)

    assert claims == [
        "O Brasil ganhou o jogo"
    ]


def test_extract_claims_ignores_empty_sentences():

    service = ClaimService()

    text = "O Brasil ganhou o jogo... A partida terminou ontem."

    claims = service.extract_claims(text)

    assert claims == [
        "O Brasil ganhou o jogo",
        "A partida terminou ontem"
    ]


def test_extract_claims_with_whitespace():

    service = ClaimService()

    text = "  O Brasil ganhou o jogo.   A partida terminou ontem.  "

    claims = service.extract_claims(text)

    assert claims == [
        "O Brasil ganhou o jogo",
        "A partida terminou ontem"
    ]


def test_extract_claims_empty_text():

    service = ClaimService()

    claims = service.extract_claims("")

    assert claims == []


def test_create_analysis_persists_claims(monkeypatch):

    def fake_search(self, query):
        return []

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

    analysis = service.create_analysis(
        db,
        data
    )

    assert len(analysis.claims) == 2

    assert analysis.claims[0].analysis_id == analysis.id
    assert analysis.claims[1].analysis_id == analysis.id

    assert analysis.claims[0].text == "O Brasil ganhou o jogo"
    assert analysis.claims[1].text == "A partida terminou ontem"

    assert analysis.status == StatusEnum.COMPLETED

    db.close()


def test_calculate_confidence_without_evidence():

    service = ClaimService()

    confidence = service.calculate_confidence([])

    assert confidence is None


def test_calculate_confidence_with_one_evidence():

    service = ClaimService()

    class FakeEvidence:
        relevance = 0.8

    confidence = service.calculate_confidence(
        [FakeEvidence()]
    )

    assert confidence == 0.8


def test_calculate_confidence_with_multiple_evidences():

    service = ClaimService()

    class EvidenceOne:
        relevance = 0.8

    class EvidenceTwo:
        relevance = 0.6

    confidence = service.calculate_confidence(
        [
            EvidenceOne(),
            EvidenceTwo()
        ]
    )

    assert confidence == 0.7


def test_low_relevance_is_not_false():

    service = ClaimService()

    verdict = service.generate_verdict(0.10)

    assert verdict == VerdictEnum.INCONCLUSIVA


def test_weak_relevance_is_not_probably_false():

    service = ClaimService()

    verdict = service.generate_verdict(0.30)

    assert verdict == VerdictEnum.INCONCLUSIVA


def test_generate_verdict_inconclusive():

    service = ClaimService()

    verdict = service.generate_verdict(0.50)

    assert verdict == VerdictEnum.INCONCLUSIVA


def test_relevance_alone_is_not_probably_true():

    service = ClaimService()

    verdict = service.generate_verdict(0.80)

    assert verdict == VerdictEnum.INCONCLUSIVA


def test_relevance_alone_is_not_true():

    service = ClaimService()

    verdict = service.generate_verdict(0.95)

    assert verdict == VerdictEnum.INCONCLUSIVA

def test_build_search_texts_inherits_repeated_role_entity():
    service = ClaimService()

    claims = [
        "Presidente Lula morreu",
        "Presidente lula morreu de overdose",
        "Presidente morreu peladão",
        "Presidente lula está no momento em um caixão",
    ]

    values = (
        service.build_search_texts(
            claims
        )
    )

    assert (
        values[0]
        == "Presidente Lula morreu"
    )

    assert (
        values[1]
        == "Presidente lula morreu de overdose"
    )

    assert (
        values[2].lower()
        == "presidente lula morreu peladão"
    )

    assert (
        values[3]
        == "Presidente lula está no momento em um caixão"
    )

def test_build_search_texts_does_not_replace_existing_entity():
    service = ClaimService()

    claims = [
        "Presidente Lula discursou",
        "Presidente Lula viajou",
        "Presidente Bolsonaro morreu",
    ]

    values = (
        service.build_search_texts(
            claims
        )
    )

    assert (
        values[2]
        == "Presidente Bolsonaro morreu"
    )
