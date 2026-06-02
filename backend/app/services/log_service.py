"""
DocumentLog access — one row per OPEN (urinish).

Rules:
  - Each viewer open creates a NEW row (status OPENED).
  - Acknowledge updates that specific row to ACKNOWLEDGED.
  - Admin report groups rows by user, with drill-down to all attempts.
"""
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.models import DocumentLog, AckStatus


def create_attempt(
    db: Session,
    *,
    document_id: int,
    ad_username: str,
    full_name: Optional[str],
    department: Optional[str],
    position: Optional[str],
    email: Optional[str],
    ip_address: Optional[str],
    user_agent: Optional[str],
) -> DocumentLog:
    log = DocumentLog(
        document_id=document_id,
        ad_username=ad_username,
        full_name=full_name,
        department=department,
        position=position,
        email=email,
        status=AckStatus.OPENED,
        opened_at=datetime.utcnow(),
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


def get_attempt(db: Session, attempt_id: int) -> Optional[DocumentLog]:
    return db.query(DocumentLog).filter(DocumentLog.id == attempt_id).first()


def latest_attempt(db: Session, document_id: int, ad_username: str) -> Optional[DocumentLog]:
    """Most recent attempt for a user+document (fallback when no id supplied)."""
    return (
        db.query(DocumentLog)
        .filter(
            DocumentLog.document_id == document_id,
            DocumentLog.ad_username == ad_username,
        )
        .order_by(DocumentLog.opened_at.desc())
        .first()
    )


def acknowledge_attempt(db: Session, attempt_id: int, ad_username: str) -> Optional[DocumentLog]:
    log = (
        db.query(DocumentLog)
        .filter(DocumentLog.id == attempt_id, DocumentLog.ad_username == ad_username)
        .first()
    )
    if not log:
        return None
    if log.status != AckStatus.ACKNOWLEDGED:
        log.status = AckStatus.ACKNOWLEDGED
        log.acknowledged_at = datetime.utcnow()
        db.commit()
        db.refresh(log)
    return log


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def list_attempts(db: Session, document_id: int, ad_username: str) -> List[DocumentLog]:
    return (
        db.query(DocumentLog)
        .filter(
            DocumentLog.document_id == document_id,
            DocumentLog.ad_username == ad_username,
        )
        .order_by(DocumentLog.opened_at.desc())
        .all()
    )


def list_user_rows(db: Session, document_id: int) -> List[dict]:
    """
    One row per user. Status = ACKNOWLEDGED if any attempt acknowledged,
    else OPENED. Time = latest acknowledge time if acknowledged, else latest
    open time. IP = that representative attempt's IP.
    """
    rows = (
        db.query(DocumentLog)
        .filter(DocumentLog.document_id == document_id)
        .order_by(DocumentLog.opened_at.asc())
        .all()
    )

    grouped: dict[str, dict] = {}
    for log in rows:
        u = log.ad_username
        g = grouped.get(u)
        if g is None:
            g = {
                "username": u,
                "full_name": log.full_name,
                "department": log.department,
                "position": log.position,
                "attempts": 0,
                "acknowledged": False,
                "status": AckStatus.OPENED,
                "time": log.opened_at,
                "ip_address": log.ip_address,
            }
            grouped[u] = g

        g["attempts"] += 1
        # keep latest identity fields
        g["full_name"] = log.full_name or g["full_name"]
        g["department"] = log.department or g["department"]
        g["position"] = log.position or g["position"]

        if log.status == AckStatus.ACKNOWLEDGED:
            ack_t = log.acknowledged_at or log.opened_at
            if not g["acknowledged"] or (g["time"] and ack_t and ack_t > g["time"]) or not g["time"]:
                g["acknowledged"] = True
                g["status"] = AckStatus.ACKNOWLEDGED
                g["time"] = ack_t
                g["ip_address"] = log.ip_address
        elif not g["acknowledged"]:
            # still only opened — track latest open
            if not g["time"] or (log.opened_at and log.opened_at > g["time"]):
                g["time"] = log.opened_at
                g["ip_address"] = log.ip_address

    # newest activity first
    return sorted(grouped.values(), key=lambda r: r["time"] or datetime.min, reverse=True)
