import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base


class Repository(Base):
    """
    GitHub репозиторий, в котором установлен бот.
    """
    __tablename__ = "repositories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    org_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("organizations.id"),
        index=True
    )
    github_id: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        comment="GitHub repository ID"
    )
    full_name: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        comment="owner/repo"
    )
    is_private: Mapped[bool] = mapped_column(
        Boolean,
        default=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )

    # Связи
    organization: Mapped["Organization"] = relationship(
        back_populates="repositories"
    )