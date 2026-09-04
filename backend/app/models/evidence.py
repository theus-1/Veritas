from sqlalchemy import Uuid, String, Float, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from uuid import UUID, uuid4
from datetime import datetime
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.claim import Claim

class Evidence(Base):
    __tablename__="evidences"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    analysis_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("analyses.id"))
    claim_id: Mapped[UUID] = mapped_column(Uuid, ForeignKey("claims.id"))
    source_name: Mapped[str] = mapped_column(String)
    source_url: Mapped[str] = mapped_column(String)
    title: Mapped[str] = mapped_column(String)
    relevance: Mapped[float] = mapped_column(Float)
    supports_claim: Mapped[bool] = mapped_column(Boolean)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    claim: Mapped["Claim"] = relationship(back_populates="evidences")
    analysis: Mapped["Analysis"] = relationship(back_populates="evidences")
