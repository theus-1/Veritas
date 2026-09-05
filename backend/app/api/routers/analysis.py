from fastapi import APIRouter, Depends
from app.schemas.analysis import AnalysisCreate
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.analysis_service import AnalysisService
from app.schemas.analysis import AnalysisResponse

router = APIRouter()

@router.post("/analysis/", response_model=AnalysisResponse)
async def create_analysis(analysiscreate: AnalysisCreate, db: Session = Depends(get_db)):

    service = AnalysisService()
    new_analysis = service.create_analysis(
        db=db,
        data=analysiscreate
    )

    return new_analysis

