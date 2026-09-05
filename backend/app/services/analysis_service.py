from sqlalchemy.orm import Session
from app.schemas.analysis import AnalysisCreate
from app.repositories.analysis_repository import AnalysisRepository
from app.services.claim_service import ClaimService
from app.models.analysis import StatusEnum

class AnalysisService:
    def create_analysis(self, db: Session, data: AnalysisCreate):
        evidences =[]
        repository = AnalysisRepository()
        analysis = repository.create(db, data)
        claim_service = ClaimService()
        claims = claim_service.extract_claims(data.input_text)
        claim_service.create_claims(db, analysis, claims)
        confidence = claim_service.calculate_confidence(evidences)
        analysis.confidence = confidence
        verdict = claim_service.generate_verdict(confidence)
        analysis.verdict = verdict
        analysis.status = StatusEnum.COMPLETED
        return analysis

