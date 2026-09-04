from sqlalchemy.orm import Session
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate
from app.models.analysis import Analysis, StatusEnum

class AnalysisRepository:
    def create(self, db: Session, data: AnalysisCreate):
        analysis = Analysis(
            title = data.title,
            input_text = data.input_text,
            input_url = data.input_url,
            status = StatusEnum.PENDING
        )
        db.add(analysis)
        db.commit()
        db.refresh(analysis)

        return analysis
