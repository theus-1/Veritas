from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.models.evidence import EvidenceVerdictEnum


class EvidenceResponse(BaseModel):
    id: UUID
    claim_id: UUID

    source_name: str
    source_url: str
    title: str

    relevance: float
    verdict: EvidenceVerdictEnum

    reason: Optional[str] = None

    created_at: datetime

    model_config = ConfigDict(
        from_attributes=True
    )
