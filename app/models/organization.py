import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Organization(Base):
    """
    GitHub App installation (организация или пользователь).
    Одна установка = одна организация.
    """
    __tablename__ = "organizations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    installation_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        comment="GitHub App installation ID"
    )
    github_login: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="GitHub username or org name"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )

    # Связи
    repositories: Mapped[list["Repository"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )
    reviews: Mapped[list["Review"]] = relationship(
        back_populates="organization",
        cascade="all, delete-orphan"
    )