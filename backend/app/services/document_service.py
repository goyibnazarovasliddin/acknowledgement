import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DeepArchive

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024

# Allowed upload types → server-decided MIME (never trust the client's
# Content-Type). Anything else is rejected. PDFs render inline in the viewer;
# the others are downloaded.
_ALLOWED_TYPES = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


def _ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _safe_original_name(raw: Optional[str], ext: str) -> str:
    """Keep only the basename, strip control/quote/path chars — prevents
    Content-Disposition header injection when the file is served back."""
    base = Path(raw or "").name
    cleaned = "".join(c for c in base if c.isprintable() and c not in '"\\/\r\n')
    cleaned = cleaned.strip() or f"document{ext}"
    return cleaned[:255]


async def save_document(
    db: Session,
    file: UploadFile,
    title: str,
    uploaded_by: Optional[str],
) -> Document:
    _ensure_upload_dir()

    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_TYPES:
        raise HTTPException(
            415,
            f"Unsupported file type '{ext or '?'}'. Allowed: {', '.join(sorted(_ALLOWED_TYPES))}",
        )

    content = await file.read()
    if not content:
        raise HTTPException(400, "Empty file")
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"File too large (max {settings.MAX_FILE_SIZE_MB} MB)")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / stored_name
    dest.write_bytes(content)

    mime = _ALLOWED_TYPES[ext]  # server-decided, not the client-supplied header

    doc = Document(
        title=title,
        filename=stored_name,
        original_filename=_safe_original_name(file.filename, ext),
        mime_type=mime,
        file_size=len(content),
        uploaded_by=uploaded_by,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def get_by_token(db: Session, token: str) -> Optional[Document]:
    return db.query(Document).filter(Document.share_token == token).first()


def get_file_path(doc: Document) -> Path:
    return UPLOAD_DIR / doc.filename


def list_documents(db: Session, archived: bool = False) -> list[Document]:
    return (
        db.query(Document)
        .filter(Document.archived == archived)
        .order_by(Document.uploaded_at.desc())
        .all()
    )


def archive_document(db: Session, doc: Document):
    doc.archived = True
    doc.archived_at = datetime.utcnow()
    db.commit()


def unarchive_document(db: Session, doc: Document):
    doc.archived = False
    doc.archived_at = None
    db.commit()


def _fmt(dt) -> Optional[str]:
    return dt.isoformat() if dt else None


def delete_document(db: Session, doc: Document, deleted_by: Optional[str] = None):
    """
    Hard-delete from the UI, but snapshot everything into the hidden deep_archive
    table first. The physical file is intentionally KEPT on disk — nothing is
    truly lost at the storage level, even though the UI shows it as deleted.
    """
    snapshot = {
        "document": {
            "id": doc.id,
            "title": doc.title,
            "filename": doc.filename,
            "original_filename": doc.original_filename,
            "mime_type": doc.mime_type,
            "file_size": doc.file_size,
            "share_token": doc.share_token,
            "uploaded_at": _fmt(doc.uploaded_at),
            "uploaded_by": doc.uploaded_by,
            "archived": doc.archived,
            "archived_at": _fmt(doc.archived_at),
        },
        "logs": [
            {
                "id": l.id,
                "ad_username": l.ad_username,
                "full_name": l.full_name,
                "department": l.department,
                "position": l.position,
                "email": l.email,
                "status": l.status.value,
                "opened_at": _fmt(l.opened_at),
                "acknowledged_at": _fmt(l.acknowledged_at),
                "ip_address": l.ip_address,
                "user_agent": l.user_agent,
            }
            for l in doc.logs
        ],
    }

    db.add(DeepArchive(
        original_document_id=doc.id,
        title=doc.title,
        stored_filename=doc.filename,
        deleted_by=deleted_by,
        payload=json.dumps(snapshot, ensure_ascii=False),
    ))
    db.delete(doc)   # cascades logs; file kept on disk
    db.commit()
