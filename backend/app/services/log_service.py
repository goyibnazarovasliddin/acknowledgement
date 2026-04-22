"""
Handles upsert logic for DocumentLog rows.

Rules:
  - UNIQUE(document_id, ad_username)
  - Anonymous users (ad_username IS NULL) always INSERT
  - Identified users: INSERT first time, UPDATE on repeat visits
  - Status transitions are monotonically forward only
"""
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models import DocumentLog, AckStatus

_STATUS_ORDER = [
    AckStatus.ANONYMOUS_OPENED,
    AckStatus.IDENTIFIED_NOT_CONFIRMED,
    AckStatus.CONFIRMED,
    AckStatus.ACKNOWLEDGED,
]


def _rank(status: AckStatus) -> int:
    return _STATUS_ORDER.index(status)


def get_log(db: Session, document_id: int, ad_username: str) -> Optional[DocumentLog]:
    return (
        db.query(DocumentLog)
        .filter(
            DocumentLog.document_id == document_id,
            DocumentLog.ad_username == ad_username,
        )
        .first()
    )


def record_open(
    db: Session,
    *,
    document_id: int,
    ad_username: Optional[str],
    full_name: Optional[str],
    department: Optional[str],
    email: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> DocumentLog:
    if ad_username:
        log = get_log(db, document_id, ad_username)
        if log:
            # User already opened — keep highest status reached
            log.ip_address = ip_address
            log.user_agent = user_agent
            db.commit()
            db.refresh(log)
            return log
        # First open for this identified user
        status = AckStatus.IDENTIFIED_NOT_CONFIRMED
    else:
        status = AckStatus.ANONYMOUS_OPENED

    log = DocumentLog(
        document_id=document_id,
        ad_username=ad_username,
        full_name=full_name,
        department=department,
        email=email,
        status=status,
        opened_at=datetime.utcnow(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def advance_to_confirmed(db: Session, log: DocumentLog) -> DocumentLog:
    if _rank(log.status) < _rank(AckStatus.CONFIRMED):
        log.status = AckStatus.CONFIRMED
        log.confirmed_at = datetime.utcnow()
        db.commit()
        db.refresh(log)
    return log


def advance_to_acknowledged(db: Session, log: DocumentLog) -> DocumentLog:
    if _rank(log.status) < _rank(AckStatus.ACKNOWLEDGED):
        log.status = AckStatus.ACKNOWLEDGED
        log.acknowledged_at = datetime.utcnow()
        db.commit()
        db.refresh(log)
    return log
