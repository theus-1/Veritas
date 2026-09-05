from app.core.database import SessionLocal
from app.models.analysis import Analysis, StatusEnum
from app.models.claim import Claim
from app.models.evidence import EvidenceVerdictEnum
from app.schemas.search import SearchResult
from app.services.evidence_service import EvidenceService


def test_create_evidences():

    db = SessionLocal()

    analysis = Analysis(
        title="Análise de teste",
        input_text="O Brasil ganhou o jogo.",
        status=StatusEnum.PENDING
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    claim = Claim(
        analysis_id=analysis.id,
        text="O Brasil ganhou o jogo."
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    results = [
        SearchResult(
            title="Brasil vence partida",
            url="https://exemplo.com/brasil",
            source_name="Fonte de teste",
            snippet="O Brasil venceu a partida."
        ),
        SearchResult(
            title="Resultado da partida",
            url="https://exemplo.com/resultado",
            source_name="Outra fonte",
            snippet="A partida terminou com vitória do Brasil."
        )
    ]

    service = EvidenceService()

    evidences = service.create_evidences(
        db=db,
        analysis=analysis,
        claim=claim,
        results=results
    )

    assert len(evidences) == 2

    assert evidences[0].analysis_id == analysis.id
    assert evidences[0].claim_id == claim.id

    assert evidences[0].source_name == "Fonte de teste"
    assert evidences[0].source_url == "https://exemplo.com/brasil"
    assert evidences[0].title == "Brasil vence partida"
    assert evidences[0].relevance > 0.0
    assert evidences[0].relevance <= 1.0

    db.close()


def test_evidence_is_related_to_claim():

    db = SessionLocal()

    analysis = Analysis(
        title="Análise de teste",
        input_text="O Brasil ganhou o jogo.",
        status=StatusEnum.PENDING
    )

    db.add(analysis)
    db.commit()
    db.refresh(analysis)

    claim = Claim(
        analysis_id=analysis.id,
        text="O Brasil ganhou o jogo."
    )

    db.add(claim)
    db.commit()
    db.refresh(claim)

    result = SearchResult(
        title="Brasil vence partida",
        url="https://exemplo.com/brasil",
        source_name="Fonte de teste",
        snippet="O Brasil venceu."
    )

    service = EvidenceService()

    evidences = service.create_evidences(
        db=db,
        analysis=analysis,
        claim=claim,
        results=[result]
    )

    db.refresh(claim)

    assert len(claim.evidences) == 1
    assert claim.evidences[0].id == evidences[0].id
    assert claim.evidences[0].claim_id == claim.id

    db.close()


def test_calculate_relevance():

    service = EvidenceService()

    result = SearchResult(
        title="Brasil ganhou o jogo",
        url="https://exemplo.com",
        source_name="Fonte de teste",
        snippet="O Brasil venceu a partida."
    )

    relevance = service.calculate_relevance(
        "Brasil ganhou o jogo",
        result
    )

    assert relevance > 0.0
    assert relevance <= 1.0


def test_calculate_relevance_without_matching_words():

    service = EvidenceService()

    result = SearchResult(
        title="Economia mundial cresce",
        url="https://exemplo.com",
        source_name="Fonte de teste",
        snippet="Mercados internacionais apresentam crescimento."
    )

    relevance = service.calculate_relevance(
        "Brasil ganhou o jogo",
        result
    )

    assert relevance == 0.0


def test_determine_verdict_supports():

    service = EvidenceService()

    result = SearchResult(
        title="Brasil derrota Argentina",
        url="https://exemplo.com/brasil-argentina",
        source_name="Fonte de teste",
        snippet="O Brasil venceu a Argentina por 2 a 0."
    )

    verdict = service.determine_verdict(
        "Brasil venceu a Argentina.",
        result
    )

    assert verdict == EvidenceVerdictEnum.SUPPORTS


def test_determine_verdict_contradicts():

    service = EvidenceService()

    result = SearchResult(
        title="Argentina derrota Brasil",
        url="https://exemplo.com/argentina-brasil",
        source_name="Fonte de teste",
        snippet="A Argentina venceu o Brasil por 2 a 0."
    )

    verdict = service.determine_verdict(
        "Brasil venceu a Argentina.",
        result
    )

    assert verdict == EvidenceVerdictEnum.CONTRADICTS


def test_determine_verdict_neutral():

    service = EvidenceService()

    result = SearchResult(
        title="Vasco derrota Vitória",
        url="https://exemplo.com/vasco-vitoria",
        source_name="Fonte de teste",
        snippet="O Vasco venceu o Vitória pela Copa do Brasil."
    )

    verdict = service.determine_verdict(
        "Brasil venceu a Argentina.",
        result
    )

    assert verdict == EvidenceVerdictEnum.NEUTRAL


def test_determine_verdict_contradicts_with_negation():

    service = EvidenceService()

    result = SearchResult(
        title="Brasil não venceu a Argentina",
        url="https://exemplo.com/brasil-argentina",
        source_name="Fonte de teste",
        snippet="O Brasil não venceu a Argentina na partida."
    )

    verdict = service.determine_verdict(
        "Brasil venceu a Argentina.",
        result
    )

    assert verdict == EvidenceVerdictEnum.CONTRADICTS
