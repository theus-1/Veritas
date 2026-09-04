from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.analysis import VerdictEnum, StatusEnum
from uuid import UUID

class AnalysisCreate(BaseModel):

    title: str
    input_text: str
    input_url: Optional[str] = None

class AnalysisResponse(BaseModel):

    id: UUID
    title: str
    input_text: str
    input_url: Optional[str] = None
    verdict: Optional[VerdictEnum] = None
    confidence: Optional[float] = None
    explanation: Optional[str] = None
    status: StatusEnum
    created_at: datetime
