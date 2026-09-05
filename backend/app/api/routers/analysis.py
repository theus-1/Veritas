from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.rate_limit import analysis_rate_limiter
from app.schemas.analysis import AnalysisCreate, AnalysisResponse
from app.services.analysis_service import AnalysisService


router = APIRouter()


@router.post("/", response_model=AnalysisResponse)
def create_analysis(
    request: Request,
    data: AnalysisCreate,
    db: Session = Depends(get_db),
):
    client_ip = (
        request.client.host
        if request.client
        else "unknown"
    )

    analysis_rate_limiter.check(client_ip)

    service = AnalysisService()

    return service.create_analysis(
        db=db,
        data=data,
    )
