"""
Admin panel — session-auth protected.

GET/POST /admin/login
GET      /admin/logout
GET      /admin/
GET/POST /admin/upload
GET      /admin/documents/{id}
GET      /admin/documents/{id}/logs.json
GET      /admin/documents/{id}/users/{username}
GET      /admin/documents/{id}/users/{username}/logs.json
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
from app.services import document_service, export_service, log_service
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


def _fmt(dt) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S") if dt else ""


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
        # distinct users who acknowledged
        ack_users = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id, DocumentLog.status == AckStatus.ACKNOWLEDGED)
            .distinct()
            .count()
        )
        total_users = (
            db.query(DocumentLog.ad_username)
            .filter(DocumentLog.document_id == doc.id)
            .distinct()
            .count()
        )
        doc_stats.append({"doc": doc, "ack_count": ack_users, "total_count": total_users})

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
# Document detail — grouped per user
# ---------------------------------------------------------------------------
def _apply_filters(rows, status, department):
    if status:
        rows = [r for r in rows if r["status"].value == status]
    if department:
        d = department.lower()
        rows = [r for r in rows if (r.get("department") or "").lower().find(d) >= 0]
    return rows


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

    rows = _apply_filters(log_service.list_user_rows(db, doc_id), status, department)
    departments = sorted({r["department"] for r in log_service.list_user_rows(db, doc_id) if r.get("department")})

    return templates.TemplateResponse(
        "admin/document_detail.html",
        {
            "request": request,
            "doc": doc,
            "rows": rows,
            "ack_statuses": list(AckStatus),
            "departments": departments,
            "filter_status": status,
            "filter_department": department,
            "admin_user": admin_user,
        },
    )


@router.get("/documents/{doc_id}/logs.json")
async def document_logs_json(
    doc_id: int,
    request: Request,
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    _require_admin(request)
    rows = _apply_filters(log_service.list_user_rows(db, doc_id), status, department)
    return {
        "rows": [
            {
                "username": r["username"],
                "full_name": r["full_name"] or "",
                "department": r["department"] or "",
                "position": r["position"] or "",
                "status": r["status"].value,
                "time": _fmt(r["time"]),
                "ip_address": r["ip_address"] or "",
                "attempts": r["attempts"],
            }
            for r in rows
        ]
    }


# ---------------------------------------------------------------------------
# User drill-down — all attempts of one user for this document
# ---------------------------------------------------------------------------
@router.get("/documents/{doc_id}/users/{username}", response_class=HTMLResponse)
async def user_attempts(doc_id: int, username: str, request: Request, db: Session = Depends(get_db)):
    admin_user = _require_admin(request)
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404)
    attempts = log_service.list_attempts(db, doc_id, username)
    return templates.TemplateResponse(
        "admin/user_attempts.html",
        {
            "request": request,
            "doc": doc,
            "username": username,
            "attempts": attempts,
            "admin_user": admin_user,
        },
    )


@router.get("/documents/{doc_id}/users/{username}/logs.json")
async def user_attempts_json(doc_id: int, username: str, request: Request, db: Session = Depends(get_db)):
    _require_admin(request)
    attempts = log_service.list_attempts(db, doc_id, username)
    return {
        "rows": [
            {
                "status": a.status.value,
                "opened_at": _fmt(a.opened_at),
                "acknowledged_at": _fmt(a.acknowledged_at),
                "time": _fmt(a.acknowledged_at or a.opened_at),
                "ip_address": a.ip_address or "",
            }
            for a in attempts
        ]
    }


# ---------------------------------------------------------------------------
# Exports — raw attempts
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
