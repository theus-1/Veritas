from sqlalchemy.orm import Session

from app.models.analysis import StatusEnum
from app.repositories.analysis_repository import AnalysisRepository
from app.schemas.analysis import AnalysisCreate
from app.services.claim_service import ClaimService
from app.services.evidence_service import EvidenceService
from app.services.search_service import SearchService


class AnalysisService:

    def create_analysis(self, db: Session, data: AnalysisCreate):
        repository = AnalysisRepository()

        analysis = repository.create(db, data)

        claim_service = ClaimService()
        evidence_service = EvidenceService()
        search_service = SearchService()

        claims_text = claim_service.extract_claims(data.input_text)

        claims = claim_service.create_claims(
            db=db,
            analysis=analysis,
            claims=claims_text
        )

        all_evidences = []

        for claim in claims:
            results = search_service.search(claim.text)

            evidences = evidence_service.create_evidences(
                db=db,
                analysis=analysis,
                claim=claim,
                results=results
            )

            all_evidences.extend(evidences)

        confidence = claim_service.calculate_confidence(
            all_evidences
        )

        analysis.confidence = confidence
        analysis.verdict = claim_service.generate_verdict(confidence)
        analysis.status = StatusEnum.COMPLETED

        db.commit()
        db.refresh(analysis)

        return analysis
