"""
Admin panel — session-auth protected.

GET/POST /admin/login
GET      /admin/logout
GET      /admin/
GET/POST /admin/upload
GET      /admin/documents/{id}
GET      /admin/documents/{id}/export/csv|excel
DELETE   /admin/documents/{id}
"""
import logging
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.session import clear_session, create_session, get_session_user
from app.config import settings
from app.database import get_db
from app.models import AckStatus, Document, DocumentLog
from app.services import document_service, export_service
from app.services.document_service import list_documents

logger = logging.getLogger(__name__)

_TEMPLATES_DIR = Path(__file__).resolve().parent.parent.parent.parent / "frontend" / "templates"

router = APIRouter(prefix="/admin")
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))


def _require_admin(request: Request) -> str:
    user = get_session_user(request)
    if not user:
        raise HTTPException(status_code=302, headers={"Location": "/admin/login"})
    return user


# ---------------------------------------------------------------------------
# Login / Logout
# ---------------------------------------------------------------------------
@router.get("/login", response_class=HTMLResponse)
async def login_form(request: Request):
    if get_session_user(request):
        return RedirectResponse("/admin/", status_code=302)
    return templates.TemplateResponse("admin/login.html", {"request": request, "error": None})


@router.post("/login", response_class=HTMLResponse)
async def login_post(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    if username == settings.ADMIN_USERNAME and password == settings.ADMIN_PASSWORD:
        response = RedirectResponse("/admin/", status_code=302)
        create_session(response, username)
        return response
    return templates.TemplateResponse(
        "admin/login.html",
        {"request": request, "error": "Login yoki parol noto'g'ri"},
        status_code=401,
    )


@router.get("/logout")
async def logout():
    response = RedirectResponse("/admin/login", status_code=302)
    clear_session(response)
    return response


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------
@router.get("/", response_class=HTMLResponse)
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request)
    docs = list_documents(db)
    doc_stats = []
    for doc in docs:
        ack_count = (
            db.query(DocumentLog)
            .filter(DocumentLog.document_id == doc.id, DocumentLog.status == AckStatus.ACKNOWLEDGED)
            .count()
        )
        total_count = (
            db.query(DocumentLog)
            .filter(DocumentLog.document_id == doc.id, DocumentLog.ad_username.isnot(None))
            .count()
        )
        doc_stats.append({"doc": doc, "ack_count": ack_count, "total_count": total_count})

    return templates.TemplateResponse(
        "admin/index.html",
        {"request": request, "doc_stats": doc_stats, "admin_user": admin_user},
    )


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------
@router.get("/upload", response_class=HTMLResponse)
async def upload_form(request: Request):
    admin_user = _require_admin(request)
    return templates.TemplateResponse("admin/upload.html", {"request": request, "admin_user": admin_user})


@router.post("/upload", response_class=HTMLResponse)
async def upload_document(
    request: Request,
    title: str = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    admin_user = _require_admin(request)
    doc = await document_service.save_document(db, file, title, uploaded_by=admin_user)
    return templates.TemplateResponse(
        "admin/upload_success.html",
        {"request": request, "doc": doc, "admin_user": admin_user},
    )


# ---------------------------------------------------------------------------
# Document detail
# ---------------------------------------------------------------------------
@router.get("/documents/{doc_id}", response_class=HTMLResponse)
async def document_detail(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    admin_user = _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)

    query = db.query(DocumentLog).filter(DocumentLog.document_id == doc_id)
    if status:
        try:
            query = query.filter(DocumentLog.status == AckStatus(status))
        except ValueError:
            pass
    if department:
        query = query.filter(DocumentLog.department.ilike(f"%{department}%"))

    logs = query.order_by(DocumentLog.opened_at.desc()).all()
    departments = (
        db.query(DocumentLog.department)
        .filter(DocumentLog.document_id == doc_id, DocumentLog.department.isnot(None))
        .distinct()
        .all()
    )

    return templates.TemplateResponse(
        "admin/document_detail.html",
        {
            "request": request,
            "doc": doc,
            "logs": logs,
            "ack_statuses": list(AckStatus),
            "departments": [d[0] for d in departments if d[0]],
            "filter_status": status,
            "filter_department": department,
            "admin_user": admin_user,
        },
    )


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------
@router.get("/documents/{doc_id}/export/csv")
async def export_csv(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    data = export_service.export_csv(_filtered_logs(db, doc_id, status, department))
    return Response(
        content=data,
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="ack_{doc_id}.csv"'},
    )


@router.get("/documents/{doc_id}/export/excel")
async def export_excel(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    data = export_service.export_excel(_filtered_logs(db, doc_id, status, department), doc.title)
    return Response(
        content=data,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="ack_{doc_id}.xlsx"'},
    )


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------
@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    document_service.delete_document(db, doc)
    return {"ok": True}


# ---------------------------------------------------------------------------
# Admin file view/download
# ---------------------------------------------------------------------------
@router.get("/documents/{doc_id}/file")
async def admin_serve_file(doc_id: int, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    file_path = document_service.get_file_path(doc)
    if not file_path.exists():
        raise HTTPException(404, "File not found on disk")
    return FileResponse(
        path=str(file_path),
        media_type=doc.mime_type,
        filename=doc.original_filename,
        headers={"Content-Disposition": f'inline; filename="{doc.original_filename}"'},
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _filtered_logs(db: Session, doc_id: int, status: str | None, department: str | None):
    query = db.query(DocumentLog).filter(DocumentLog.document_id == doc_id)
    if status:
        try:
            query = query.filter(DocumentLog.status == AckStatus(status))
        except ValueError:
            pass
    if department:
        query = query.filter(DocumentLog.department.ilike(f"%{department}%"))
    return query.order_by(DocumentLog.opened_at.desc()).all()
