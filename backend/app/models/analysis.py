from sqlalchemy import String, Uuid, Text, Enum as enum, Float, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base
from uuid import UUID, uuid4
from typing import Optional
from enum import Enum
from datetime import datetime


class VerdictEnum(Enum):

    VERDADEIRA = "VERDADEIRA"
    PROVAVELMENTE_VERDADEIRA = "PROVAVELMENTE_VERDADEIRA"
    INCONCLUSIVA = "INCONCLUSIVA"
    PROVAVELMENTE_FALSA = "PROVAVELMENTE_FALSA"
    FALSA = "FALSA"

class StatusEnum(Enum):

    PENDING = "Pendente"
    PROCESSING = "Processando"
    COMPLETED = "Completa"
    FAILED = "Falhou"

class Analysis(Base):
    __tablename__="analyses"

    id: Mapped[UUID] = mapped_column(Uuid, primary_key=True, default=uuid4)
    title: Mapped[str] = mapped_column(String)
    input_text: Mapped[str] = mapped_column(Text)
    input_url: Mapped[Optional[str]] = mapped_column(String)
    verdict: Mapped[VerdictEnum] = mapped_column(enum(VerdictEnum))
    confidence: Mapped[float] = mapped_column(Float)
    explanation: Mapped[str] = mapped_column(Text)
    status: Mapped[StatusEnum] = mapped_column(enum(StatusEnum))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    claims: Mapped[list["Claim"]] = relationship(back_populates="analysis")
    evidences: Mapped[list["Evidence"]] = relationship(back_populates="analysis")


