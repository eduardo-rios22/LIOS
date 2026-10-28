from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Participant(Base):
    __tablename__ = "participants"
    __table_args__ = (Index("ix_participants_condition", "condition"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), unique=True, nullable=False)
    condition: Mapped[str] = mapped_column(String(2), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)
    country: Mapped[str] = mapped_column(String(120), nullable=False)
    experience: Mapped[str] = mapped_column(String(8), nullable=False)
    consent: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="in_progress")
    iu1: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iu2: Mapped[int | None] = mapped_column(Integer, nullable=True)
    iu3: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_error: Mapped[int | None] = mapped_column(Integer, nullable=True)
    check_explanation: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    rounds: Mapped[list["RoundLog"]] = relationship(
        back_populates="participant",
        cascade="all, delete-orphan",
    )


class RoundLog(Base):
    __tablename__ = "round_logs"
    __table_args__ = (
        UniqueConstraint("participant_id", "round_number", name="uq_round_per_participant"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    participant_id: Mapped[int] = mapped_column(ForeignKey("participants.id"), nullable=False, index=True)
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    chosen: Mapped[str] = mapped_column(String(1), nullable=False)
    recommended: Mapped[str] = mapped_column(String(1), nullable=False)
    consistent: Mapped[str] = mapped_column(String(1), nullable=False)
    is_error: Mapped[bool] = mapped_column(Boolean, nullable=False)
    accepted: Mapped[bool] = mapped_column(Boolean, nullable=False)
    duration_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    participant: Mapped[Participant] = relationship(back_populates="rounds")
