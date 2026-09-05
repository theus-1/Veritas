from sqlalchemy.orm import Session

from app.models.analysis import Analysis
from app.models.claim import Claim
from app.models.evidence import Evidence
from app.schemas.search import SearchResult


class EvidenceService:

    def create_evidences(
        self,
        db: Session,
        analysis: Analysis,
        claim: Claim,
        results: list[SearchResult]
    ):
        evidences = []

        for result in results:
            relevance = self.calculate_relevance(
                claim.text,
                result
            )

            evidence = Evidence(
                analysis_id=analysis.id,
                claim_id=claim.id,
                source_name=result.source_name,
                source_url=result.url,
                title=result.title,
                relevance=relevance,
                supports_claim=False
            )

            db.add(evidence)
            evidences.append(evidence)

        db.commit()

        for evidence in evidences:
            db.refresh(evidence)

        return evidences

    def calculate_relevance(
        self,
        claim_text: str,
        result: SearchResult
    ) -> float:

        claim_words = set(
            claim_text.lower().split()
        )

        evidence_text = (
            f"{result.title} {result.snippet}"
        ).lower()

        evidence_words = set(
            evidence_text.split()
        )

        if not claim_words:
            return 0.0

        common_words = (
            claim_words.intersection(evidence_words)
        )

        return len(common_words) / len(claim_words)
