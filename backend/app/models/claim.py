from datetime import datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID, uuid4

from sqlalchemy import (
    DateTime,
    Enum as SqlEnum,
    Float,
    ForeignKey,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.analysis import VerdictEnum

if TYPE_CHECKING:
    from app.models.analysis import Analysis
    from app.models.evidence import Evidence


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid4,
    )

    analysis_id: Mapped[UUID] = mapped_column(
        Uuid,
        ForeignKey("analyses.id"),
    )

    text: Mapped[str] = mapped_column(
        Text,
    )

    verdict: Mapped[Optional[VerdictEnum]] = mapped_column(
        SqlEnum(VerdictEnum),
        nullable=True,
    )

    confidence: Mapped[Optional[float]] = mapped_column(
        Float,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
    )

    analysis: Mapped["Analysis"] = relationship(
        back_populates="claims",
    )

    evidences: Mapped[list["Evidence"]] = relationship(
        back_populates="claim",
    )
