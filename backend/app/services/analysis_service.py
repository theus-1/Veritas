from sqlalchemy.orm import Session
from app.schemas.analysis import AnalysisCreate
from app.repositories.analysis_repository import AnalysisRepository

class AnalysisService:
    def create_analysis(self, db: Session, data: AnalysisCreate):
        repository = AnalysisRepository()
        analysis = repository.create(db, data)
        return analysis

