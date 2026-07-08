import asyncio
import json
import re
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath

from fastapi import BackgroundTasks, Cookie, Depends, FastAPI, File, Form, Header, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.services.latex_revision_sanitizer import sanitize_revision_latex
from app.services.llm_review_service import build_llm_suggestions, llm_review_available
from app.services.review_service import build_rule_based_suggestions, split_paragraphs
from app.services.revision_service import build_revision_draft
from backend_v2.config import settings
from backend_v2.database import get_db, initialize_database
from backend_v2.job_service import run_job, update_job
from backend_v2.llm_structure_service import detect_subchapters_for_chapter, replace_chapter_children_with_detected
from backend_v2.models import (
    Artifact,
    CitationOccurrence,
    DocumentPage,
    DocumentUnit,
    DraftVersion,
    Job,
    Project,
    ProjectMember,
    ReferenceRecord,
    RevisionDraft,
    ReviewRun,
    SourceDocument,
    User,
    UserSession,
    Workspace,
    WorkspaceVersion,
)
from backend_v2.pdf_ingestion import extract_pdf
from backend_v2.reference_service import export_references_bib, import_references, map_citations, preview_references
from backend_v2.schemas import (
    BootstrapRequest,
    CitationConfirmRequest,
    DraftCreate,
    DraftSave,
    InsertDraftRequest,
    InviteRequest,
    LoginRequest,
    MemberCreate,
    ProjectCreate,
    ReferencePasteRequest,
    ReferencePreviewRequest,
    ReferenceUpdateRequest,
    ReviewCreate,
    StructureUpdate,
    TocStructureRequest,
    WorkspaceCreate,
    WorkspaceFileCreate,
    WorkspaceFileSave,
    WorkspaceFolderCreate,
    WorkspaceMainDocument,
    WorkspaceRename,
    WorkspaceScaffoldRequest,
)
from backend_v2.security import create_session_token, hash_password, hash_session_token, verify_password
from backend_v2.storage import storage
from backend_v2.structure_builder import apply_toc_structure
from backend_v2.workspace_service import (
    build_workspace_snippet,
    compile_workspace,
    compile_workspace_file,
    create_blank_workspace,
    create_scaffold_workspace,
    import_zip,
    list_workspace_files,
    safe_relative_path,
)


app = FastAPI(title="Private AI Thesis Workspace API", version="2.0.0")


def set_session_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        settings.session_cookie_name,
        raw,
        httponly=True,
        samesite=settings.session_cookie_samesite,
        secure=settings.session_cookie_secure,
        domain=settings.session_cookie_domain,
        max_age=60 * 60 * 24 * settings.session_days,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(
        settings.session_cookie_name,
        domain=settings.session_cookie_domain,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    initialize_database()


def user_payload(user: User) -> dict:
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "is_admin": user.is_admin}


def project_payload(project: Project, role: str) -> dict:
    return {
        "id": project.id,
        "name": project.name,
        "description": project.description,
        "role": role,
        "created_at": project.created_at.isoformat(),
    }


def current_user(
    db: Session = Depends(get_db),
    thesis_session: str | None = Cookie(default=None),
    x_session_token: str | None = Header(default=None),
) -> User:
    raw = thesis_session or x_session_token
    if not raw:
        raise HTTPException(status_code=401, detail="Silakan login.")
    session = db.scalar(select(UserSession).where(UserSession.token_hash == hash_session_token(raw)))
    if not session:
        raise HTTPException(status_code=401, detail="Session tidak valid.")
    user = db.get(User, session.user_id)
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Akun tidak aktif.")
    return user


def membership(db: Session, project_id: str, user: User, write: bool = False) -> str:
    if user.is_admin:
        if not db.get(Project, project_id):
            raise HTTPException(status_code=404, detail="Project tidak ditemukan.")
        return "ADMIN"
    member = db.scalar(
        select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == user.id)
    )
    if not member:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan.")
    if write and member.role not in {"OWNER", "EDITOR"}:
        raise HTTPException(status_code=403, detail="Akses edit diperlukan.")
    return member.role


def require_project(db: Session, project_id: str, user: User, write: bool = False) -> Project:
    membership(db, project_id, user, write)
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project tidak ditemukan.")
    return project


async def read_upload(upload: UploadFile) -> bytes:
    content = await upload.read(settings.max_upload_bytes + 1)
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Ukuran file melebihi batas.")
    return content


@app.get("/api/v2/health")
def health() -> dict:
    available, _reason = llm_review_available()
    return {"status": "ok", "version": "2.0.0", "openrouter_ready": available}

@app.get("/api/v2/auth/setup-status")
def setup_status(db: Session = Depends(get_db)) -> dict:
    user_count = db.scalar(select(func.count(User.id))) or 0
    return {"requires_setup": user_count == 0, "user_count": user_count}



@app.post("/api/v2/auth/bootstrap")
def bootstrap(payload: BootstrapRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    if db.scalar(select(func.count(User.id))) > 0:
        raise HTTPException(status_code=409, detail="Bootstrap sudah pernah dilakukan.")
    try:
        encoded = hash_password(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user = User(email=payload.email.lower().strip(), display_name=payload.display_name.strip(), password_hash=encoded, is_admin=True)
    db.add(user)
    db.flush()
    raw, token_hash = create_session_token()
    db.add(UserSession(user_id=user.id, token_hash=token_hash, expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_days)))
    db.commit()
    set_session_cookie(response, raw)
    return user_payload(user)


@app.post("/api/v2/auth/login")
def login(payload: LoginRequest, response: Response, db: Session = Depends(get_db)) -> dict:
    user = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Email atau password salah.")
    raw, token_hash = create_session_token()
    db.add(UserSession(user_id=user.id, token_hash=token_hash, expires_at=datetime.now(timezone.utc) + timedelta(days=settings.session_days)))
    db.commit()
    set_session_cookie(response, raw)
    return user_payload(user)


@app.post("/api/v2/auth/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    thesis_session: str | None = Cookie(default=None),
) -> dict:
    if thesis_session:
        db.execute(delete(UserSession).where(UserSession.token_hash == hash_session_token(thesis_session)))
        db.commit()
    clear_session_cookie(response)
    return {"status": "logged_out"}


@app.get("/api/v2/auth/me")
def me(user: User = Depends(current_user)) -> dict:
    return user_payload(user)


@app.post("/api/v2/users/invite")
def invite(payload: InviteRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Hanya admin yang dapat membuat akun.")
    if db.scalar(select(User).where(User.email == payload.email.lower().strip())):
        raise HTTPException(status_code=409, detail="Email sudah terdaftar.")
    invited = User(
        email=payload.email.lower().strip(),
        display_name=payload.display_name.strip(),
        password_hash=hash_password(payload.password),
    )
    db.add(invited)
    db.commit()
    return user_payload(invited)


@app.get("/api/v2/users")
def list_users(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Hanya admin yang dapat melihat daftar akun.")
    users = db.scalars(select(User).order_by(User.created_at.desc()))
    return [user_payload(item) | {"is_active": item.is_active, "created_at": item.created_at.isoformat()} for item in users]


@app.get("/api/v2/projects")
def list_projects(db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    if user.is_admin:
        projects = db.scalars(select(Project).order_by(Project.updated_at.desc()))
        return [project_payload(project, "ADMIN") for project in projects]
    rows = db.execute(
        select(Project, ProjectMember.role)
        .join(ProjectMember, ProjectMember.project_id == Project.id)
        .where(ProjectMember.user_id == user.id)
        .order_by(Project.updated_at.desc())
    ).all()
    return [project_payload(project, role) for project, role in rows]


@app.post("/api/v2/projects")
def create_project(payload: ProjectCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    project = Project(name=payload.name.strip(), description=payload.description.strip(), created_by=user.id)
    db.add(project)
    db.flush()
    db.add(ProjectMember(project_id=project.id, user_id=user.id, role="OWNER"))
    db.commit()
    return project_payload(project, "OWNER")


@app.get("/api/v2/projects/{project_id}")
def get_project(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    role = membership(db, project_id, user)
    project = require_project(db, project_id, user)
    return project_payload(project, role)


@app.post("/api/v2/projects/{project_id}/members")
def add_member(project_id: str, payload: MemberCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    role = membership(db, project_id, user)
    if not user.is_admin and role != "OWNER":
        raise HTTPException(status_code=403, detail="Hanya owner yang dapat menambah anggota.")
    target = db.scalar(select(User).where(User.email == payload.email.lower().strip()))
    if not target:
        raise HTTPException(status_code=404, detail="Pengguna belum memiliki akun.")
    existing = db.scalar(select(ProjectMember).where(ProjectMember.project_id == project_id, ProjectMember.user_id == target.id))
    if existing:
        existing.role = payload.role.upper()
    else:
        existing = ProjectMember(project_id=project_id, user_id=target.id, role=payload.role.upper())
        db.add(existing)
    db.commit()
    return {"user": user_payload(target), "role": existing.role}


@app.get("/api/v2/projects/{project_id}/documents")
def list_documents(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    require_project(db, project_id, user)
    documents = db.scalars(select(SourceDocument).where(SourceDocument.project_id == project_id).order_by(SourceDocument.created_at.desc()))
    return [{"id": item.id, "filename": item.filename, "status": item.status, "page_count": item.page_count, "structure_confirmed": item.structure_confirmed} for item in documents]


@app.delete("/api/v2/projects/{project_id}/documents/{document_id}")
def delete_document(project_id: str, document_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    document = db.get(SourceDocument, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    unit_ids = list(db.scalars(select(DocumentUnit.id).where(DocumentUnit.document_id == document_id)))
    if unit_ids:
        draft_ids = list(db.scalars(select(RevisionDraft.id).where(RevisionDraft.unit_id.in_(unit_ids))))
        if draft_ids:
            db.execute(delete(DraftVersion).where(DraftVersion.draft_id.in_(draft_ids)))
            db.execute(delete(RevisionDraft).where(RevisionDraft.id.in_(draft_ids)))
        db.execute(delete(ReviewRun).where(ReviewRun.unit_id.in_(unit_ids)))
        db.execute(delete(CitationOccurrence).where(CitationOccurrence.unit_id.in_(unit_ids)))
        db.execute(delete(DocumentUnit).where(DocumentUnit.id.in_(unit_ids)))
    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document_id))
    storage_root_key = f"projects/{project_id}/sources/{document_id}"
    db.delete(document)
    db.commit()
    try:
        storage.delete_tree(storage_root_key)
    except Exception:
        pass
    return {"status": "deleted", "document_id": document_id}


@app.post("/api/v2/projects/{project_id}/documents")
async def upload_document(project_id: str, background: BackgroundTasks, file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=422, detail="File harus berformat PDF.")
    content = await read_upload(file)
    document = SourceDocument(project_id=project_id, filename=Path(file.filename).name, storage_key="", status="QUEUED")
    db.add(document)
    db.flush()
    document.storage_key = f"projects/{project_id}/sources/{document.id}/original.pdf"
    storage.write_bytes(document.storage_key, content)
    job = Job(project_id=project_id, job_type="PDF_INGESTION", created_by=user.id)
    db.add(job)
    db.commit()

    def handler(job_db: Session, running_job: Job) -> dict:
        source = job_db.get(SourceDocument, document.id)
        update_job(job_db, running_job, 25, "Mengekstrak teks PDF")
        units = extract_pdf(job_db, source, storage.resolve(source.storage_key))
        update_job(job_db, running_job, 85, "Menyusun struktur dokumen")
        return {"document_id": source.id, "unit_count": len(units), "status": source.status}

    background.add_task(run_job, job.id, handler)
    return {"document_id": document.id, "job_id": job.id, "status": "QUEUED"}


@app.get("/api/v2/projects/{project_id}/documents/{document_id}/structure")
def get_structure(project_id: str, document_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user)
    document = db.get(SourceDocument, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    units = db.scalars(select(DocumentUnit).where(DocumentUnit.document_id == document_id).order_by(DocumentUnit.sort_order))
    return {
        "document": {"id": document.id, "filename": document.filename, "status": document.status, "confirmed": document.structure_confirmed},
        "units": [
            {"id": unit.id, "parent_id": unit.parent_id, "level": unit.level, "number": unit.number, "title": unit.title, "content": unit.content, "start_page": unit.start_page, "end_page": unit.end_page, "sort_order": unit.sort_order, "confidence": unit.confidence}
            for unit in units
        ],
    }


@app.put("/api/v2/projects/{project_id}/documents/{document_id}/structure")
def update_structure(project_id: str, document_id: str, payload: StructureUpdate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    document = db.get(SourceDocument, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    pages = list(db.scalars(select(DocumentPage).where(DocumentPage.document_id == document_id).order_by(DocumentPage.page_number)))
    page_lookup = {page.page_number: page.text for page in pages}
    existing_ids = set(db.scalars(select(DocumentUnit.id).where(DocumentUnit.document_id == document_id)))
    incoming_existing_ids = {item.id for item in payload.units if item.id in existing_ids}
    removed_ids = sorted(existing_ids - incoming_existing_ids)
    if removed_ids:
        draft_ids = list(db.scalars(select(RevisionDraft.id).where(RevisionDraft.unit_id.in_(removed_ids))))
        if draft_ids:
            db.execute(delete(DraftVersion).where(DraftVersion.draft_id.in_(draft_ids)))
            db.execute(delete(RevisionDraft).where(RevisionDraft.id.in_(draft_ids)))
        db.execute(delete(ReviewRun).where(ReviewRun.unit_id.in_(removed_ids)))
        db.execute(delete(CitationOccurrence).where(CitationOccurrence.unit_id.in_(removed_ids)))
        db.execute(delete(DocumentUnit).where(DocumentUnit.id.in_(removed_ids)))
        db.flush()
    latest_chapter_id = None
    latest_subchapter_id = None
    for index, item in enumerate(sorted(payload.units, key=lambda unit: unit.sort_order)):
        unit = db.get(DocumentUnit, item.id) if item.id in existing_ids else None
        if unit and (unit.document_id != document_id or unit.project_id != project_id):
            raise HTTPException(status_code=404, detail=f"Unit tidak ditemukan: {item.id}")
        if not unit:
            unit = DocumentUnit(project_id=project_id, document_id=document_id, level="SUBCHAPTER", title="Bagian Baru", sort_order=index)
            db.add(unit)
            db.flush()
        level = item.level.upper()
        parent_id = None
        if level == "CHAPTER":
            latest_subchapter_id = None
        elif level == "SUBCHAPTER":
            parent_id = latest_chapter_id
        elif level == "SUBSUBCHAPTER":
            parent_id = latest_subchapter_id or latest_chapter_id
        start_page = max(1, item.start_page)
        end_page = max(start_page, item.end_page)
        unit.parent_id = parent_id
        unit.level = level
        unit.number = item.number.strip()
        unit.title = item.title.strip() or "Bagian Baru"
        unit.start_page = start_page
        unit.end_page = end_page
        unit.sort_order = index
        unit.content = "\n\n".join(page_lookup.get(page, "") for page in range(start_page, end_page + 1)).strip()
        unit.confidence = 1.0
        db.flush()
        if level == "CHAPTER":
            latest_chapter_id = unit.id
        elif level == "SUBCHAPTER":
            latest_subchapter_id = unit.id
    document.structure_confirmed = True
    document.status = "READY"
    db.commit()
    return {"status": "saved", "unit_count": len(payload.units)}


@app.post("/api/v2/projects/{project_id}/documents/{document_id}/structure/detect-subchapters/{chapter_id}")
def detect_subchapters(project_id: str, document_id: str, chapter_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    chapter = db.get(DocumentUnit, chapter_id)
    if not chapter or chapter.project_id != project_id or chapter.document_id != document_id or chapter.level != "CHAPTER":
        raise HTTPException(status_code=404, detail="BAB tidak ditemukan.")
    pages = list(db.scalars(select(DocumentPage).where(DocumentPage.document_id == document_id, DocumentPage.page_number >= chapter.start_page, DocumentPage.page_number <= chapter.end_page).order_by(DocumentPage.page_number)))
    items, source = detect_subchapters_for_chapter(chapter, pages)
    if not items:
        raise HTTPException(status_code=422, detail="Sub Bab belum berhasil terdeteksi dari BAB ini.")
    units = replace_chapter_children_with_detected(db, chapter, items, source)
    return {"status": "READY", "source": source, "unit_count": len(units)}

@app.post("/api/v2/projects/{project_id}/documents/{document_id}/structure/from-toc")
def build_structure_from_toc(project_id: str, document_id: str, payload: TocStructureRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    document = db.get(SourceDocument, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    try:
        units = apply_toc_structure(db, document, payload.content)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"status": "READY", "unit_count": len(units)}

@app.post("/api/v2/projects/{project_id}/documents/{document_id}/confirm-structure")
def confirm_structure(project_id: str, document_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    document = db.get(SourceDocument, document_id)
    if not document or document.project_id != project_id:
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan.")
    document.structure_confirmed = True
    document.status = "READY"
    db.commit()
    return {"status": "READY", "document_id": document.id}


@app.get("/api/v2/projects/{project_id}/references")
def list_references(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    require_project(db, project_id, user)
    items = db.scalars(select(ReferenceRecord).where(ReferenceRecord.project_id == project_id).order_by(ReferenceRecord.citation_key))
    return [{"id": ref.id, "citation_key": ref.citation_key, "authors": ref.authors, "title": ref.title, "year": ref.year, "doi": ref.doi, "raw_reference": ref.raw_reference, "source_type": ref.source_type, "confidence": ref.parse_confidence} for ref in items]


@app.post("/api/v2/projects/{project_id}/references/preview")
def preview_reference_entries(project_id: str, payload: ReferencePreviewRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    entries = preview_references(payload.content, "paste", payload.reference_format)
    return {"count": len(entries), "entries": entries}


@app.post("/api/v2/projects/{project_id}/references/import")
async def upload_references(project_id: str, reference_format: str = Form("auto"), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    if not file.filename or Path(file.filename).suffix.lower() not in {".bib", ".txt"}:
        raise HTTPException(status_code=422, detail="Referensi harus berupa .bib atau .txt.")
    content = (await read_upload(file)).decode("utf-8", errors="replace")
    source_type = "bib" if file.filename.lower().endswith(".bib") else "txt"
    created = import_references(db, project_id, content, source_type, reference_format)
    return {"imported": len(created)}


@app.post("/api/v2/projects/{project_id}/references/paste")
def paste_references(project_id: str, payload: ReferencePasteRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    created = import_references(db, project_id, payload.content, "paste", payload.reference_format)
    return {"imported": len(created)}


@app.post("/api/v2/projects/{project_id}/citations/map")
def create_citation_map(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    occurrences = map_citations(db, project_id)
    return {"mapped": len(occurrences)}


@app.put("/api/v2/projects/{project_id}/references/{reference_id}")
def update_reference(project_id: str, reference_id: str, payload: ReferenceUpdateRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    reference = db.get(ReferenceRecord, reference_id)
    if not reference or reference.project_id != project_id:
        raise HTTPException(status_code=404, detail="Referensi tidak ditemukan.")
    duplicate = db.scalar(select(ReferenceRecord).where(ReferenceRecord.project_id == project_id, ReferenceRecord.citation_key == payload.citation_key.strip(), ReferenceRecord.id != reference_id))
    if duplicate:
        raise HTTPException(status_code=409, detail="Citation key sudah dipakai referensi lain.")
    reference.citation_key = payload.citation_key.strip()
    reference.authors = payload.authors.strip()
    reference.title = payload.title.strip()
    reference.year = payload.year.strip()
    reference.doi = payload.doi.strip()
    reference.raw_reference = payload.raw_reference.strip()
    reference.source_type = "user_edited"
    reference.parse_confidence = 1.0
    db.commit()
    return {"status": "updated", "id": reference.id}


@app.delete("/api/v2/projects/{project_id}/references/{reference_id}")
def delete_reference(project_id: str, reference_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    reference = db.get(ReferenceRecord, reference_id)
    if not reference or reference.project_id != project_id:
        raise HTTPException(status_code=404, detail="Referensi tidak ditemukan.")
    db.execute(delete(CitationOccurrence).where(CitationOccurrence.project_id == project_id, CitationOccurrence.reference_id == reference.id))
    db.delete(reference)
    db.commit()
    return {"status": "deleted", "id": reference_id}


@app.get("/api/v2/projects/{project_id}/references/bib")
def get_references_bib(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user)
    content = export_references_bib(db, project_id)
    return {"filename": "references.bib", "content": content, "count": len(content.split("@")) - 1 if content else 0}


@app.get("/api/v2/projects/{project_id}/citations")
def list_citations(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    require_project(db, project_id, user)
    rows = db.execute(
        select(CitationOccurrence, DocumentUnit, ReferenceRecord)
        .join(DocumentUnit, DocumentUnit.id == CitationOccurrence.unit_id)
        .outerjoin(ReferenceRecord, ReferenceRecord.id == CitationOccurrence.reference_id)
        .where(CitationOccurrence.project_id == project_id)
        .order_by(DocumentUnit.sort_order)
    ).all()
    return [{"id": item.id, "marker": item.marker, "context": item.context, "status": item.status, "page_number": item.page_number, "unit": f"{unit.number} {unit.title}".strip(), "reference": {"id": ref.id, "citation_key": ref.citation_key, "title": ref.title} if ref else None} for item, unit, ref in rows]


@app.post("/api/v2/projects/{project_id}/citations/{citation_id}/confirm")
def confirm_citation(project_id: str, citation_id: str, payload: CitationConfirmRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    citation = db.get(CitationOccurrence, citation_id)
    reference = db.get(ReferenceRecord, payload.reference_id)
    if not citation or citation.project_id != project_id or not reference or reference.project_id != project_id:
        raise HTTPException(status_code=404, detail="Sitasi atau referensi tidak ditemukan.")
    citation.reference_id = reference.id
    citation.status = "USER_CONFIRMED"
    db.commit()
    return {"status": citation.status}


def create_review_payload(db: Session, project_id: str, unit: DocumentUnit, user_goal: str) -> dict:
    paragraphs = split_paragraphs(unit.content)
    source = "rule-based"
    try:
        suggestions, summary = build_llm_suggestions(paragraphs, user_goal, f"{unit.number} {unit.title}".strip())
        source = "openrouter"
    except Exception:
        suggestions = build_rule_based_suggestions(paragraphs, selected_label=unit.title, source_text=unit.content)
        summary = f"Review lokal selesai dengan {len(suggestions)} saran."
    review = ReviewRun(project_id=project_id, unit_id=unit.id, user_goal=user_goal, source=source, summary=summary, suggestions_json=json.dumps(suggestions, ensure_ascii=False))
    db.add(review)
    db.commit()
    return {"id": review.id, "unit_id": unit.id, "source": source, "summary": summary, "suggestions": suggestions}


def create_draft_payload(db: Session, project_id: str, user_id: str, unit: DocumentUnit, payload: DraftCreate) -> dict:
    content = payload.content
    summary = payload.summary
    source = "user"
    if content is None:
        latest_review = db.scalar(select(ReviewRun).where(ReviewRun.unit_id == unit.id).order_by(ReviewRun.created_at.desc()))
        suggestions = json.loads(latest_review.suggestions_json) if latest_review else []
        try:
            content, summary = build_revision_draft(unit.content, suggestions, f"{unit.number} {unit.title}".strip(), latest_review.user_goal if latest_review else "Rapikan tulisan akademik.")
            source = "openrouter"
        except Exception:
            content = unit.content
            summary = "Draft dibuat dari teks hasil ekstraksi dan siap diedit manual."
            source = "source-copy"
    content = sanitize_revision_latex(content)
    validate_citation_keys(db, project_id, content)
    draft = RevisionDraft(project_id=project_id, unit_id=unit.id, title=payload.title or f"Revisi {unit.number} {unit.title}".strip(), created_by=user_id)
    db.add(draft)
    db.flush()
    version = DraftVersion(draft_id=draft.id, version_number=1, content=content, summary=summary, source=source, created_by=user_id)
    db.add(version)
    db.commit()
    return {"id": draft.id, "version": 1, "content": content, "summary": summary, "title": draft.title}


@app.post("/api/v2/projects/{project_id}/reviews")
def create_review(project_id: str, payload: ReviewCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    unit = db.get(DocumentUnit, payload.unit_id)
    if not unit or unit.project_id != project_id:
        raise HTTPException(status_code=404, detail="Bagian dokumen tidak ditemukan.")
    return create_review_payload(db, project_id, unit, payload.user_goal)


@app.post("/api/v2/projects/{project_id}/reviews/jobs")
def create_review_job(project_id: str, payload: ReviewCreate, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    unit = db.get(DocumentUnit, payload.unit_id)
    if not unit or unit.project_id != project_id:
        raise HTTPException(status_code=404, detail="Bagian dokumen tidak ditemukan.")
    active = db.scalar(
        select(Job)
        .where(Job.project_id == project_id, Job.job_type == "REVIEW_UNIT", Job.status.in_(["QUEUED", "RUNNING"]))
        .order_by(Job.created_at.desc())
    )
    if active:
        raise HTTPException(status_code=409, detail="Masih ada review yang sedang berjalan. Tunggu sampai selesai ya.")
    job = Job(project_id=project_id, job_type="REVIEW_UNIT", created_by=user.id)
    db.add(job)
    db.commit()

    def handler(job_db: Session, running_job: Job) -> dict:
        current_unit = job_db.get(DocumentUnit, unit.id)
        update_job(job_db, running_job, 22, "Membaca isi bagian yang dipilih")
        update_job(job_db, running_job, 58, "Menganalisis koherensi, gaya akademik, dan sitasi")
        result = create_review_payload(job_db, project_id, current_unit, payload.user_goal)
        update_job(job_db, running_job, 92, "Menyiapkan hasil review")
        result["unit_id"] = current_unit.id
        result["title"] = f"{current_unit.number} {current_unit.title}".strip()
        return result

    background.add_task(run_job, job.id, handler)
    return {"job_id": job.id, "status": "QUEUED"}


def validate_citation_keys(db: Session, project_id: str, content: str) -> None:
    keys = set()
    for match in re.finditer(r"\\(?:cite|parencite|textcite)\w*\{([^}]+)\}", content):
        keys.update(key.strip() for key in match.group(1).split(",") if key.strip())
    if not keys:
        return
    known = set(db.scalars(select(ReferenceRecord.citation_key).where(ReferenceRecord.project_id == project_id)))
    unknown = sorted(keys - known)
    if unknown:
        raise HTTPException(status_code=422, detail=f"Citation key tidak tersedia di project: {', '.join(unknown)}")


@app.get("/api/v2/projects/{project_id}/drafts")
def list_drafts(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    require_project(db, project_id, user)
    drafts = db.scalars(select(RevisionDraft).where(RevisionDraft.project_id == project_id).order_by(RevisionDraft.updated_at.desc()))
    result = []
    for draft in drafts:
        version = db.scalar(select(DraftVersion).where(DraftVersion.draft_id == draft.id, DraftVersion.version_number == draft.current_version))
        result.append({"id": draft.id, "unit_id": draft.unit_id, "title": draft.title, "current_version": draft.current_version, "content": version.content if version else "", "summary": version.summary if version else ""})
    return result


@app.post("/api/v2/projects/{project_id}/drafts")
def create_draft(project_id: str, payload: DraftCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    unit = db.get(DocumentUnit, payload.unit_id)
    if not unit or unit.project_id != project_id:
        raise HTTPException(status_code=404, detail="Bagian dokumen tidak ditemukan.")
    return create_draft_payload(db, project_id, user.id, unit, payload)


@app.post("/api/v2/projects/{project_id}/drafts/jobs")
def create_draft_job(project_id: str, payload: DraftCreate, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    unit = db.get(DocumentUnit, payload.unit_id)
    if not unit or unit.project_id != project_id:
        raise HTTPException(status_code=404, detail="Bagian dokumen tidak ditemukan.")
    active = db.scalar(
        select(Job)
        .where(Job.project_id == project_id, Job.job_type == "DRAFT_BUILD", Job.status.in_(["QUEUED", "RUNNING"]))
        .order_by(Job.created_at.desc())
    )
    if active:
        raise HTTPException(status_code=409, detail="Masih ada pembuatan draft yang sedang berjalan.")
    job = Job(project_id=project_id, job_type="DRAFT_BUILD", created_by=user.id)
    db.add(job)
    db.commit()

    def handler(job_db: Session, running_job: Job) -> dict:
        current_unit = job_db.get(DocumentUnit, unit.id)
        update_job(job_db, running_job, 18, "Mengambil hasil review terbaru")
        update_job(job_db, running_job, 52, "Menyusun draft .tex")
        result = create_draft_payload(job_db, project_id, user.id, current_unit, payload)
        update_job(job_db, running_job, 90, "Menyimpan draft ke Draft Manager")
        result["unit_id"] = current_unit.id
        result["next_step"] = "Buka Draft Manager untuk mengecek hasil draft .tex."
        return result

    background.add_task(run_job, job.id, handler)
    return {"job_id": job.id, "status": "QUEUED"}


@app.delete("/api/v2/projects/{project_id}/drafts/{draft_id}")
def delete_draft(project_id: str, draft_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    draft = db.get(RevisionDraft, draft_id)
    if not draft or draft.project_id != project_id:
        raise HTTPException(status_code=404, detail="Draft tidak ditemukan.")
    db.execute(delete(DraftVersion).where(DraftVersion.draft_id == draft.id))
    db.delete(draft)
    db.commit()
    return {"status": "deleted", "draft_id": draft_id}


@app.post("/api/v2/projects/{project_id}/drafts/{draft_id}/versions")
def save_draft_version(project_id: str, draft_id: str, payload: DraftSave, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    draft = db.get(RevisionDraft, draft_id)
    if not draft or draft.project_id != project_id:
        raise HTTPException(status_code=404, detail="Draft tidak ditemukan.")
    sanitized_content = sanitize_revision_latex(payload.content)
    validate_citation_keys(db, project_id, sanitized_content)
    draft.current_version += 1
    db.add(DraftVersion(draft_id=draft.id, version_number=draft.current_version, content=sanitized_content, summary=payload.summary, source="user", created_by=user.id))
    db.commit()
    return {"draft_id": draft.id, "version": draft.current_version}


@app.get("/api/v2/projects/{project_id}/drafts/{draft_id}/versions")
def draft_versions(project_id: str, draft_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    require_project(db, project_id, user)
    draft = db.get(RevisionDraft, draft_id)
    if not draft or draft.project_id != project_id:
        raise HTTPException(status_code=404, detail="Draft tidak ditemukan.")
    versions = db.scalars(select(DraftVersion).where(DraftVersion.draft_id == draft_id).order_by(DraftVersion.version_number.desc()))
    return [{"id": item.id, "version": item.version_number, "content": item.content, "summary": item.summary, "source": item.source, "created_at": item.created_at.isoformat()} for item in versions]


@app.post("/api/v2/projects/{project_id}/drafts/{draft_id}/versions/{version_id}/restore")
def restore_draft(project_id: str, draft_id: str, version_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    draft = db.get(RevisionDraft, draft_id)
    old = db.get(DraftVersion, version_id)
    if not draft or draft.project_id != project_id or not old or old.draft_id != draft.id:
        raise HTTPException(status_code=404, detail="Versi tidak ditemukan.")
    draft.current_version += 1
    db.add(DraftVersion(draft_id=draft.id, version_number=draft.current_version, content=old.content, summary=f"Dipulihkan dari versi {old.version_number}", source="restore", created_by=user.id))
    db.commit()
    return {"draft_id": draft.id, "version": draft.current_version}


@app.get("/api/v2/projects/{project_id}/workspaces")
def list_workspaces(project_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> list[dict]:
    require_project(db, project_id, user)
    items = db.scalars(select(Workspace).where(Workspace.project_id == project_id).order_by(Workspace.updated_at.desc()))
    return [{"id": item.id, "name": item.name, "main_document": item.main_document} for item in items]


@app.post("/api/v2/projects/{project_id}/workspaces")
def create_workspace(project_id: str, payload: WorkspaceCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = Workspace(project_id=project_id, name=payload.name, storage_prefix="", main_document=safe_relative_path(payload.main_document), created_by=user.id)
    db.add(workspace)
    db.flush()
    workspace.storage_prefix = f"projects/{project_id}/workspaces/{workspace.id}/current"
    create_blank_workspace(storage, workspace.storage_prefix)
    db.commit()
    return {"id": workspace.id, "name": workspace.name, "main_document": workspace.main_document}


@app.post("/api/v2/projects/{project_id}/workspaces/auto")
def create_auto_workspace(project_id: str, payload: WorkspaceScaffoldRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = Workspace(project_id=project_id, name=payload.name, storage_prefix="", main_document=safe_relative_path(payload.main_document), created_by=user.id)
    db.add(workspace)
    db.flush()
    workspace.storage_prefix = f"projects/{project_id}/workspaces/{workspace.id}/current"
    create_scaffold_workspace(storage, workspace.storage_prefix, payload.model_dump())
    db.commit()
    return {"id": workspace.id, "name": workspace.name, "main_document": workspace.main_document, "mode": "auto"}


@app.post("/api/v2/projects/{project_id}/workspaces/snippet")
def workspace_snippet(project_id: str, payload: WorkspaceScaffoldRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user)
    snippets = build_workspace_snippet(payload.model_dump())
    return {"mode": "snippet", "files": snippets}


@app.post("/api/v2/projects/{project_id}/workspaces/import")
async def import_workspace(project_id: str, name: str = Form(...), main_document: str = Form("main.tex"), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    if not file.filename or not file.filename.lower().endswith(".zip"):
        raise HTTPException(status_code=422, detail="Workspace harus berupa ZIP.")
    content = await read_upload(file)
    workspace = Workspace(project_id=project_id, name=name, storage_prefix="", main_document=safe_relative_path(main_document), created_by=user.id)
    db.add(workspace)
    db.flush()
    workspace.storage_prefix = f"projects/{project_id}/workspaces/{workspace.id}/current"
    try:
        import_zip(storage, workspace.storage_prefix, content)
    except (ValueError, OSError) as exc:
        db.rollback()
        storage.delete_tree(f"projects/{project_id}/workspaces/{workspace.id}")
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    db.commit()
    return {"id": workspace.id, "name": workspace.name, "main_document": workspace.main_document}


def require_workspace(db: Session, project_id: str, workspace_id: str) -> Workspace:
    workspace = db.get(Workspace, workspace_id)
    if not workspace or workspace.project_id != project_id:
        raise HTTPException(status_code=404, detail="Workspace tidak ditemukan.")
    return workspace


def draft_workspace_path(draft: RevisionDraft) -> str:
    title = re.sub(r"[^a-z0-9]+", "-", (draft.title or "draft").strip().lower()).strip("-") or "draft"
    return f"drafts/{title}-{draft.id[:8]}.tex"


def draft_input_statement(relative_path: str) -> str:
    pure = Path(relative_path.replace("\\", "/"))
    without_suffix = pure.with_suffix("").as_posix() if pure.suffix.lower() == ".tex" else pure.as_posix()
    return f"\\input{{{without_suffix}}}"


def insert_tex_snippet(base: str, snippet: str) -> tuple[str, str]:
    bibliography_marker = "\\printbibliography"
    end_document_marker = "\\end{document}"
    separator = "\n\n" if base else ""

    if snippet in base:
        return base, "already_present"
    if bibliography_marker in base:
        return base.replace(bibliography_marker, f"{separator}{snippet}\n\n{bibliography_marker}", 1), "before_bibliography"
    if end_document_marker in base:
        return base.replace(end_document_marker, f"{separator}{snippet}\n\n{end_document_marker}", 1), "before_end_document"
    return f"{base}{separator}{snippet}\n", "append"


def validate_workspace_name(name: str) -> str:
    cleaned = name.strip()
    if not cleaned or cleaned in {".", ".."} or "/" in cleaned or "\\" in cleaned:
        raise HTTPException(status_code=422, detail="Nama baru tidak valid.")
    return cleaned


def rename_relative_path(relative_path: str, new_name: str) -> str:
    current = PurePosixPath(relative_path)
    renamed = current.parent / validate_workspace_name(new_name)
    return safe_relative_path(renamed.as_posix())


def remove_tex_reference(base: str, relative_path: str) -> str:
    variants = [
        f"\\input{{{relative_path}}}",
        f"\\include{{{relative_path}}}",
        draft_input_statement(relative_path),
        f"\\include{{{Path(relative_path).with_suffix('').as_posix()}}}",
    ]
    lines = [line for line in base.splitlines() if line.strip() not in variants]
    cleaned = "\n".join(lines)
    return re.sub(r"\n{3,}", "\n\n", cleaned).rstrip() + ("\n" if cleaned.strip() else "")


@app.get("/api/v2/projects/{project_id}/workspaces/{workspace_id}/files")
def workspace_files(project_id: str, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user)
    workspace = require_workspace(db, project_id, workspace_id)
    return {"main_document": workspace.main_document, "files": list_workspace_files(storage.resolve(workspace.storage_prefix))}


@app.get("/api/v2/projects/{project_id}/workspaces/{workspace_id}/files/content")
def read_workspace_file(project_id: str, workspace_id: str, path: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user)
    workspace = require_workspace(db, project_id, workspace_id)
    relative = safe_relative_path(path)
    target = storage.resolve(f"{workspace.storage_prefix}/{relative}")
    if not target.exists() or not target.is_file():
        raise HTTPException(status_code=404, detail="File tidak ditemukan.")
    return {"path": relative, "content": target.read_text(encoding="utf-8")}


@app.post("/api/v2/projects/{project_id}/workspaces/{workspace_id}/folders")
def create_workspace_folder(project_id: str, workspace_id: str, payload: WorkspaceFolderCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    relative = safe_relative_path(payload.path)
    target = storage.resolve(f"{workspace.storage_prefix}/{relative}")
    if target.exists():
        raise HTTPException(status_code=409, detail="Folder sudah ada di workspace.")
    target.mkdir(parents=True, exist_ok=False)
    return {"path": relative, "kind": "folder"}


@app.post("/api/v2/projects/{project_id}/workspaces/{workspace_id}/files/upload")
async def upload_workspace_file(project_id: str, workspace_id: str, path: str = Form(...), file: UploadFile = File(...), db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    if not file.filename:
        raise HTTPException(status_code=422, detail="File upload tidak valid.")
    relative = safe_relative_path(path)
    target = storage.resolve(f"{workspace.storage_prefix}/{relative}")
    if target.exists():
        raise HTTPException(status_code=409, detail="File sudah ada di workspace.")
    content = await read_upload(file)
    storage.write_bytes(f"{workspace.storage_prefix}/{relative}", content)
    return {"path": relative, "kind": "file"}


@app.post("/api/v2/projects/{project_id}/workspaces/{workspace_id}/files")
def create_workspace_file(project_id: str, workspace_id: str, payload: WorkspaceFileCreate, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    relative = safe_relative_path(payload.path)
    target = storage.resolve(f"{workspace.storage_prefix}/{relative}")
    if target.exists():
        raise HTTPException(status_code=409, detail="File sudah ada di workspace.")
    storage.write_text(f"{workspace.storage_prefix}/{relative}", payload.content)
    return {"path": relative}


@app.put("/api/v2/projects/{project_id}/workspaces/{workspace_id}/files/rename")
def rename_workspace_entry(project_id: str, workspace_id: str, payload: WorkspaceRename, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    relative = safe_relative_path(payload.path)
    renamed_relative = rename_relative_path(relative, payload.new_name)
    if relative == renamed_relative:
        return {"old_path": relative, "path": renamed_relative, "kind": "folder" if storage.resolve(f"{workspace.storage_prefix}/{relative}").is_dir() else "file", "main_document": workspace.main_document}

    source = storage.resolve(f"{workspace.storage_prefix}/{relative}")
    if not source.exists():
        raise HTTPException(status_code=404, detail="Path tidak ditemukan.")

    destination = storage.resolve(f"{workspace.storage_prefix}/{renamed_relative}")
    workspace_root = storage.resolve(workspace.storage_prefix)
    if not destination.parent.resolve().is_relative_to(workspace_root.resolve()):
        raise HTTPException(status_code=422, detail="Nama baru tidak valid.")
    if destination.exists():
        raise HTTPException(status_code=409, detail="Nama tujuan sudah ada di workspace.")

    destination.parent.mkdir(parents=True, exist_ok=True)
    source.rename(destination)

    kind = "folder" if destination.is_dir() else "file"
    if workspace.main_document == relative:
        workspace.main_document = renamed_relative
    elif kind == "folder" and workspace.main_document.startswith(f"{relative}/"):
        workspace.main_document = f"{renamed_relative}/{workspace.main_document[len(relative) + 1:]}"
    db.commit()

    old_parent = source.parent
    while old_parent != workspace_root and old_parent.exists() and not any(old_parent.iterdir()):
        old_parent.rmdir()
        old_parent = old_parent.parent

    return {"old_path": relative, "path": renamed_relative, "kind": kind, "main_document": workspace.main_document}


@app.delete("/api/v2/projects/{project_id}/workspaces/{workspace_id}/files")
def delete_workspace_file(project_id: str, workspace_id: str, path: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    relative = safe_relative_path(path)
    if relative == workspace.main_document:
        raise HTTPException(status_code=422, detail="Main document tidak boleh dihapus.")
    target = storage.resolve(f"{workspace.storage_prefix}/{relative}")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Path tidak ditemukan.")

    main_target = storage.resolve(f"{workspace.storage_prefix}/{workspace.main_document}")
    referenced_tex_paths: list[str] = []
    if target.is_dir():
        referenced_tex_paths = [item.relative_to(storage.resolve(workspace.storage_prefix)).as_posix() for item in target.rglob("*.tex")]
        storage.delete_tree(f"{workspace.storage_prefix}/{relative}")
    else:
        if target.is_file() and target.suffix.lower() == ".tex":
            referenced_tex_paths = [relative]
        storage.delete_file(f"{workspace.storage_prefix}/{relative}")

    if main_target.exists() and main_target.is_file() and main_target != target and referenced_tex_paths:
        main_content = main_target.read_text(encoding="utf-8")
        cleaned = main_content
        for tex_path in referenced_tex_paths:
            cleaned = remove_tex_reference(cleaned, tex_path)
        if cleaned != main_content:
            main_target.write_text(cleaned, encoding="utf-8")

    workspace_root = storage.resolve(workspace.storage_prefix)
    parent = target.parent
    while parent != workspace_root and parent.exists() and not any(parent.iterdir()):
        parent.rmdir()
        parent = parent.parent
    return {"status": "deleted", "path": relative}


@app.put("/api/v2/projects/{project_id}/workspaces/{workspace_id}/files/content")
def save_workspace_file(project_id: str, workspace_id: str, payload: WorkspaceFileSave, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    relative = safe_relative_path(payload.path)
    count = db.scalar(select(func.count(WorkspaceVersion.id)).where(WorkspaceVersion.workspace_id == workspace.id, WorkspaceVersion.relative_path == relative)) or 0
    db.add(WorkspaceVersion(workspace_id=workspace.id, relative_path=relative, version_number=count + 1, content=payload.content, created_by=user.id))
    storage.write_text(f"{workspace.storage_prefix}/{relative}", payload.content)
    db.commit()
    return {"path": relative, "version": count + 1}


@app.put("/api/v2/projects/{project_id}/workspaces/{workspace_id}/main-document")
def set_main_document(project_id: str, workspace_id: str, payload: WorkspaceMainDocument, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    relative = safe_relative_path(payload.path)
    if not storage.resolve(f"{workspace.storage_prefix}/{relative}").exists():
        raise HTTPException(status_code=404, detail="Main document tidak ditemukan.")
    workspace.main_document = relative
    db.commit()
    return {"main_document": relative}


@app.post("/api/v2/projects/{project_id}/workspaces/{workspace_id}/references-bib")
def insert_references_bib(project_id: str, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    content = export_references_bib(db, project_id)
    storage.write_text(f"{workspace.storage_prefix}/references.bib", content)
    return {"path": "references.bib", "count": len(content.split("@")) - 1 if content else 0}


@app.post("/api/v2/projects/{project_id}/workspaces/{workspace_id}/insert-draft")
def insert_draft(project_id: str, workspace_id: str, payload: InsertDraftRequest, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    draft = db.get(RevisionDraft, payload.draft_id)
    if not draft or draft.project_id != project_id:
        raise HTTPException(status_code=404, detail="Draft tidak ditemukan.")
    version = db.scalar(select(DraftVersion).where(DraftVersion.draft_id == draft.id, DraftVersion.version_number == draft.current_version))
    relative = safe_relative_path(payload.target_path)
    if not relative.lower().endswith(".tex"):
        raise HTTPException(status_code=422, detail="Draft hanya bisa dikirim ke file .tex penggabung.")

    draft_relative = draft_workspace_path(draft)
    draft_target = storage.resolve(f"{workspace.storage_prefix}/{draft_relative}")
    draft_target.parent.mkdir(parents=True, exist_ok=True)
    draft_target.write_text(sanitize_revision_latex(version.content).strip() + "\n", encoding="utf-8")

    input_line = draft_input_statement(draft_relative)
    target = storage.resolve(f"{workspace.storage_prefix}/{relative}")
    if not target.exists():
        raise HTTPException(status_code=404, detail="Target workspace tidak ditemukan.")

    return {
        "path": relative,
        "mode": payload.mode,
        "inserted_at": "compile_bundle",
        "draft_file": draft_relative,
        "input_command": input_line,
    }



@app.post("/api/v2/projects/{project_id}/workspaces/{workspace_id}/compile")
def start_compile(project_id: str, workspace_id: str, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    active = db.scalar(select(Job).where(Job.project_id == project_id, Job.job_type.in_(["LATEX_COMPILE", "LATEX_FILE_COMPILE"]), Job.status.in_(["QUEUED", "RUNNING"])))
    if active:
        raise HTTPException(status_code=409, detail="Masih ada compile yang berjalan.")
    job = Job(project_id=project_id, job_type="LATEX_COMPILE", created_by=user.id)
    db.add(job)
    db.commit()

    def handler(job_db: Session, running_job: Job) -> dict:
        current_workspace = job_db.get(Workspace, workspace.id)
        update_job(job_db, running_job, 20, "Menyiapkan workspace")
        output_key = f"projects/{project_id}/artifacts/{running_job.id}/build"
        result = compile_workspace(storage.resolve(current_workspace.storage_prefix), current_workspace.main_document, storage.resolve(output_key))
        update_job(job_db, running_job, 90, "Menyiapkan preview")
        if result["success"]:
            pdf_path = Path(result["pdf_path"])
            artifact = Artifact(project_id=project_id, job_id=running_job.id, artifact_type="PDF", filename=pdf_path.name, storage_key=pdf_path.relative_to(storage.root).as_posix())
            job_db.add(artifact)
            job_db.commit()
            return {"success": True, "artifact_id": artifact.id, "preview_url": f"/api/v2/artifacts/{artifact.id}", "download_url": f"/api/v2/artifacts/{artifact.id}/download"}
        return {"success": False, "error_summary": result.get("error_summary", "Compile gagal."), "error_line": result.get("error_line"), "error_context": result.get("error_context", "")}

    background.add_task(run_job, job.id, handler)
    return {"job_id": job.id, "status": "QUEUED"}


@app.post("/api/v2/projects/{project_id}/workspaces/{workspace_id}/compile-file")
def start_compile_file(project_id: str, workspace_id: str, path: str, background: BackgroundTasks, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    require_project(db, project_id, user, write=True)
    workspace = require_workspace(db, project_id, workspace_id)
    target_path = safe_relative_path(path)
    active = db.scalar(select(Job).where(Job.project_id == project_id, Job.job_type.in_(["LATEX_COMPILE", "LATEX_FILE_COMPILE"]), Job.status.in_(["QUEUED", "RUNNING"])))
    if active:
        raise HTTPException(status_code=409, detail="Masih ada compile yang berjalan.")
    job = Job(project_id=project_id, job_type="LATEX_FILE_COMPILE", created_by=user.id)
    db.add(job)
    db.commit()

    def handler(job_db: Session, running_job: Job) -> dict:
        current_workspace = job_db.get(Workspace, workspace.id)
        update_job(job_db, running_job, 20, f"Menyiapkan {target_path}")
        output_key = f"projects/{project_id}/artifacts/{running_job.id}/build"
        result = compile_workspace_file(storage.resolve(current_workspace.storage_prefix), target_path, storage.resolve(output_key))
        update_job(job_db, running_job, 90, "Menyiapkan preview")
        if result["success"]:
            pdf_path = Path(result["pdf_path"])
            artifact = Artifact(project_id=project_id, job_id=running_job.id, artifact_type="PDF", filename=pdf_path.name, storage_key=pdf_path.relative_to(storage.root).as_posix())
            job_db.add(artifact)
            job_db.commit()
            return {"success": True, "artifact_id": artifact.id, "preview_url": f"/api/v2/artifacts/{artifact.id}", "download_url": f"/api/v2/artifacts/{artifact.id}/download", "compiled_path": target_path}
        return {"success": False, "compiled_path": target_path, "error_summary": result.get("error_summary", "Compile gagal."), "error_line": result.get("error_line"), "error_context": result.get("error_context", "")}

    background.add_task(run_job, job.id, handler)
    return {"job_id": job.id, "status": "QUEUED"}


@app.get("/api/v2/jobs/{job_id}")
def get_job(job_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> dict:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
    membership(db, job.project_id, user)
    return {"id": job.id, "type": job.job_type, "status": job.status, "progress_percent": job.progress_percent, "progress_message": job.progress_message, "result": json.loads(job.result_json or "{}")}


@app.get("/api/v2/jobs/{job_id}/events")
def job_events(job_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> StreamingResponse:
    job = db.get(Job, job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job tidak ditemukan.")
    membership(db, job.project_id, user)

    async def stream():
        last = None
        while True:
            from backend_v2.database import SessionLocal

            event_db = SessionLocal()
            current = event_db.get(Job, job_id)
            payload = {"id": current.id, "status": current.status, "progress_percent": current.progress_percent, "progress_message": current.progress_message, "result": json.loads(current.result_json or "{}")}
            event_db.close()
            serialized = json.dumps(payload, ensure_ascii=False)
            if serialized != last:
                yield f"data: {serialized}\n\n"
                last = serialized
            if current.status in {"SUCCEEDED", "FAILED", "CANCELLED"}:
                break
            await asyncio.sleep(0.75)

    return StreamingResponse(stream(), media_type="text/event-stream")


@app.get("/api/v2/artifacts/{artifact_id}")
def get_artifact(artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> FileResponse:
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact tidak ditemukan.")
    membership(db, artifact.project_id, user)
    return FileResponse(storage.resolve(artifact.storage_key), media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=\"{artifact.filename}\""})


@app.get("/api/v2/artifacts/{artifact_id}/download")
def download_artifact(artifact_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> FileResponse:
    artifact = db.get(Artifact, artifact_id)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact tidak ditemukan.")
    membership(db, artifact.project_id, user)
    return FileResponse(storage.resolve(artifact.storage_key), filename=artifact.filename, media_type="application/pdf")


@app.get("/api/v2/projects/{project_id}/workspaces/{workspace_id}/export")
def export_workspace(project_id: str, workspace_id: str, db: Session = Depends(get_db), user: User = Depends(current_user)) -> FileResponse:
    require_project(db, project_id, user)
    workspace = require_workspace(db, project_id, workspace_id)
    export_base = storage.resolve(f"projects/{project_id}/exports/{workspace.id}")
    export_base.parent.mkdir(parents=True, exist_ok=True)
    archive = shutil.make_archive(str(export_base), "zip", storage.resolve(workspace.storage_prefix))
    return FileResponse(archive, filename=f"{workspace.name}.zip", media_type="application/zip")











