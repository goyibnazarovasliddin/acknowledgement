import os
import json
import uuid
import mimetypes
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document, DeepArchive

UPLOAD_DIR = Path(settings.UPLOAD_DIR)
MAX_BYTES = settings.MAX_FILE_SIZE_MB * 1024 * 1024


def _ensure_upload_dir():
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def save_document(
    db: Session,
    file: UploadFile,
    title: str,
    uploaded_by: Optional[str],
) -> Document:
    _ensure_upload_dir()

    content = await file.read()
    if len(content) > MAX_BYTES:
        raise HTTPException(413, f"File too large (max {settings.MAX_FILE_SIZE_MB} MB)")

    ext = Path(file.filename).suffix
    stored_name = f"{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / stored_name
    dest.write_bytes(content)

    mime = file.content_type or mimetypes.guess_type(file.filename)[0] or "application/octet-stream"

    doc = Document(
        title=title,
        filename=stored_name,
        original_filename=file.filename,
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
