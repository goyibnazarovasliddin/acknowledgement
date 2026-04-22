import os
import uuid
import mimetypes
from pathlib import Path
from typing import Optional

from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Document

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


def list_documents(db: Session) -> list[Document]:
    return db.query(Document).order_by(Document.uploaded_at.desc()).all()


def delete_document(db: Session, doc: Document):
    path = get_file_path(doc)
    if path.exists():
        path.unlink()
    db.delete(doc)
    db.commit()
