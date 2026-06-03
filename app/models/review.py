import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Review(Base):
    """
    Результат анализа Pull Request.
    Одна запись = одно ревью одного PR.
    """
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"),
        index=True
    )
    repo_full_name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        comment="owner/repo"
    )
    pr_number: Mapped[int] = mapped_column(
        Integer,
        comment="Pull Request number"
    )
    commit_sha: Mapped[str] = mapped_column(
        String(40),
        comment="SHA of the commit being reviewed"
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="pending",
        comment="pending, completed, failed"
    )
    problems_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        comment="Number of problems found"
    )
    problems_data: Mapped[dict | None] = mapped_column(
        JSON,
        nullable=True,
        comment="Full list of problems from Ruff"
    )
    processing_time_ms: Mapped[int | None] = mapped_column(
        Integer,
        comment="Time taken to process PR in milliseconds"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )

    # Связи
    organization: Mapped["Organization"] = relationship(
        back_populates="reviews"
    )