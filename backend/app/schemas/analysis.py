from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.analysis import StatusEnum, VerdictEnum
from app.schemas.evidence import EvidenceResponse


class AnalysisCreate(BaseModel):
    title: str = Field(min_length=3, max_length=300)
    input_text: str = Field(min_length=10, max_length=10000)
    input_url: Optional[str] = Field(default=None, max_length=2000)


class ClaimResponse(BaseModel):
    id: UUID
    text: str

    verdict: Optional[VerdictEnum] = None
    confidence: Optional[float] = None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )


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

    claims: list[ClaimResponse] = Field(default_factory=list)
    evidences: list[EvidenceResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)
