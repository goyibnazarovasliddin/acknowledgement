import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, DateTime, Enum as SAEnum,
    ForeignKey, UniqueConstraint, Text, BigInteger,
)
from sqlalchemy.orm import relationship

from app.database import Base


class AckStatus(str, enum.Enum):
    ANONYMOUS_OPENED = "ANONYMOUS_OPENED"
    IDENTIFIED_NOT_CONFIRMED = "IDENTIFIED_NOT_CONFIRMED"
    CONFIRMED = "CONFIRMED"
    ACKNOWLEDGED = "ACKNOWLEDGED"


def _token() -> str:
    return uuid.uuid4().hex


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    filename = Column(String(255), nullable=False)          # stored name on disk
    original_filename = Column(String(255), nullable=False)  # original upload name
    mime_type = Column(String(128), nullable=False)
    file_size = Column(BigInteger, nullable=True)
    share_token = Column(String(64), unique=True, nullable=False, default=_token)
    uploaded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    uploaded_by = Column(String(255), nullable=True)

    logs = relationship("DocumentLog", back_populates="document", cascade="all, delete-orphan")


class DocumentLog(Base):
    __tablename__ = "document_logs"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)

    ad_username = Column(String(255), nullable=True)
    full_name = Column(String(255), nullable=True)
    department = Column(String(255), nullable=True)
    email = Column(String(255), nullable=True)

    status = Column(SAEnum(AckStatus), nullable=False, default=AckStatus.ANONYMOUS_OPENED)

    opened_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    confirmed_at = Column(DateTime, nullable=True)
    acknowledged_at = Column(DateTime, nullable=True)

    ip_address = Column(String(64), nullable=True)
    user_agent = Column(Text, nullable=True)

    __table_args__ = (
        UniqueConstraint("document_id", "ad_username", name="uq_document_user"),
    )

    document = relationship("Document", back_populates="logs")
