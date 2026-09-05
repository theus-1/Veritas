from datetime import datetime
from enum import Enum
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class EvidenceVerdictEnum(Enum):
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    NEUTRAL = "NEUTRAL"


class Evidence(Base):
    __tablename__ = "evidences"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    analysis_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("analyses.id"),
        nullable=False,
    )

    claim_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("claims.id"),
        nullable=False,
    )

    source_name: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    title: Mapped[str] = mapped_column(
        String,
        nullable=False,
    )

    relevance: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    verdict: Mapped[EvidenceVerdictEnum] = mapped_column(
        String,
        nullable=False,
        default=EvidenceVerdictEnum.NEUTRAL.value,
    )

    reason: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )

    claim: Mapped["Claim"] = relationship(
        back_populates="evidences",
    )

    analysis: Mapped["Analysis"] = relationship(
        back_populates="evidences",
    )
