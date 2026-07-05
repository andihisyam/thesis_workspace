import sys
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse

from backend.app.core.config import PROJECT_ROOT, THESIS_ROOT
from backend.app.schemas.compare import CompareRequest, CompareResponse, FullDocumentBuildResponse
from backend.app.schemas.draft import DraftContentSaveRequest

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.compile_service import run_latex_compile  # noqa: E402
from app.services.full_document_build import prepare_full_document_build  # noqa: E402
from app.services.latex_fragment_preview import prepare_fragment_compare_build  # noqa: E402
from app.services.thesis_repository import ThesisRepository  # noqa: E402

router = APIRouter(tags=["compile"])
repository = ThesisRepository(THESIS_ROOT)
COMPILE_RUNS_ROOT = PROJECT_ROOT / "data" / "compile_runs"
FULL_DOCUMENT_RUNS_ROOT = PROJECT_ROOT / "data" / "full_document_runs"


def _resolve_compile_run_dir(run_id: str) -> Path:
    run_root = (COMPILE_RUNS_ROOT / run_id).resolve()
    base_root = COMPILE_RUNS_ROOT.resolve()
    if base_root != run_root.parent:
        raise HTTPException(status_code=400, detail="Run ID tidak valid.")
    if not run_root.exists():
        raise HTTPException(status_code=404, detail="Folder hasil compile tidak ditemukan.")
    return run_root


def _resolve_full_document_run_dir(run_id: str) -> Path:
    run_root = (FULL_DOCUMENT_RUNS_ROOT / run_id).resolve()
    base_root = FULL_DOCUMENT_RUNS_ROOT.resolve()
    if base_root != run_root.parent:
        raise HTTPException(status_code=400, detail="Run ID tidak valid.")
    if not run_root.exists():
        raise HTTPException(status_code=404, detail="Folder hasil full compile tidak ditemukan.")
    return run_root


def _build_pdf_preview_url(run_id: str, variant: str, pdf_path: str) -> str:
    if not pdf_path:
        return ""
    return f"/api/compile/runs/{run_id}/{variant}/preview"


def _build_pdf_download_url(run_id: str, variant: str, pdf_path: str) -> str:
    if not pdf_path:
        return ""
    return f"/api/compile/runs/{run_id}/{variant}/download"


def _build_compare_response(result: dict) -> CompareResponse:
    run_id = Path(result["run_root"]).name
    result["run_id"] = run_id
    result["original"]["pdf_preview_url"] = _build_pdf_preview_url(
        run_id,
        "original",
        result["original"].get("pdf_path", ""),
    )
    result["original"]["pdf_download_url"] = _build_pdf_download_url(
        run_id,
        "original",
        result["original"].get("pdf_path", ""),
    )
    result["revised"]["pdf_preview_url"] = _build_pdf_preview_url(
        run_id,
        "revised",
        result["revised"].get("pdf_path", ""),
    )
    result["revised"]["pdf_download_url"] = _build_pdf_download_url(
        run_id,
        "revised",
        result["revised"].get("pdf_path", ""),
    )
    return CompareResponse(**result)


def _build_full_document_response(result: dict) -> FullDocumentBuildResponse:
    run_id = Path(result["run_root"]).name
    compile_result = dict(result["compile_result"])
    compile_result["pdf_preview_url"] = f"/api/compile/full/runs/{run_id}/preview" if compile_result.get("pdf_path") else ""
    compile_result["pdf_download_url"] = f"/api/compile/full/runs/{run_id}/download" if compile_result.get("pdf_path") else ""
    return FullDocumentBuildResponse(
        run_id=run_id,
        run_root=result["run_root"],
        preview_mode="full",
        applied_draft_count=int(result.get("applied_draft_count", 0)),
        applied_draft_labels=list(result.get("applied_draft_labels", [])),
        compile_result=compile_result,
        pdf_preview_url=compile_result["pdf_preview_url"],
        pdf_download_url=compile_result["pdf_download_url"],
    )


def _inline_pdf_response(pdf_path: Path) -> FileResponse:
    response = FileResponse(pdf_path, media_type="application/pdf")
    response.headers["Content-Disposition"] = f'inline; filename="{pdf_path.name}"'
    return response


def _download_pdf_response(pdf_path: Path, download_name: str) -> FileResponse:
    response = FileResponse(pdf_path, media_type="application/pdf")
    response.headers["Content-Disposition"] = f'attachment; filename="{download_name}"'
    return response


@router.post("/compile/original")
def compile_original() -> dict:
    result = run_latex_compile(THESIS_ROOT, PROJECT_ROOT)
    return {
        **result,
        "pdf_preview_url": "/api/compile/thesis/original/preview" if result.get("pdf_path") else "",
        "pdf_download_url": "/api/compile/thesis/original/download" if result.get("pdf_path") else "",
    }


@router.post("/compile/compare", response_model=CompareResponse)
def compile_compare(payload: CompareRequest) -> CompareResponse:
    try:
        selected = repository.load_revision_draft(payload.draft_json_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        result = prepare_fragment_compare_build(
            project_root=PROJECT_ROOT,
            thesis_root=THESIS_ROOT,
            draft_metadata=selected,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _build_compare_response(result)


@router.post("/editor/compile-preview", response_model=CompareResponse)
def compile_editor_preview(payload: DraftContentSaveRequest) -> CompareResponse:
    try:
        selected = repository.load_revision_draft(payload.draft_json_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    try:
        result = prepare_fragment_compare_build(
            project_root=PROJECT_ROOT,
            thesis_root=THESIS_ROOT,
            draft_metadata=selected,
            revised_text_override=payload.content,
            include_original_compile=False,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _build_compare_response(result)


@router.post("/compile/full-document", response_model=FullDocumentBuildResponse)
def compile_full_document() -> FullDocumentBuildResponse:
    try:
        result = prepare_full_document_build(
            project_root=PROJECT_ROOT,
            thesis_root=THESIS_ROOT,
            active_drafts=repository.list_active_revision_drafts(),
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return _build_full_document_response(result)


@router.get("/compile/runs/{run_id}/{variant}/preview")
def get_compile_run_pdf_preview(run_id: str, variant: str) -> FileResponse:
    if variant not in {"original", "revised"}:
        raise HTTPException(status_code=400, detail="Variant PDF tidak valid.")

    run_root = _resolve_compile_run_dir(run_id)
    pdf_path = run_root / variant / "main.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF hasil compile belum tersedia.")

    return _inline_pdf_response(pdf_path)


@router.get("/compile/runs/{run_id}/{variant}/download")
def get_compile_run_pdf_download(run_id: str, variant: str) -> FileResponse:
    if variant not in {"original", "revised"}:
        raise HTTPException(status_code=400, detail="Variant PDF tidak valid.")

    run_root = _resolve_compile_run_dir(run_id)
    pdf_path = run_root / variant / "main.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF hasil compile belum tersedia.")

    return _download_pdf_response(pdf_path, f"{run_id}-{variant}.pdf")


@router.get("/compile/full/runs/{run_id}/preview")
def get_full_document_pdf_preview(run_id: str) -> FileResponse:
    run_root = _resolve_full_document_run_dir(run_id)
    pdf_path = run_root / "merged" / "main.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF full document belum tersedia.")

    return _inline_pdf_response(pdf_path)


@router.get("/compile/full/runs/{run_id}/download")
def get_full_document_pdf_download(run_id: str) -> FileResponse:
    run_root = _resolve_full_document_run_dir(run_id)
    pdf_path = run_root / "merged" / "main.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF full document belum tersedia.")

    return _download_pdf_response(pdf_path, f"{run_id}-full-document.pdf")


@router.get("/compile/thesis/original/preview")
def get_original_thesis_pdf_preview() -> FileResponse:
    pdf_path = THESIS_ROOT / "main.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF thesis asli belum tersedia.")
    return _inline_pdf_response(pdf_path)


@router.get("/compile/thesis/original/download")
def get_original_thesis_pdf_download() -> FileResponse:
    pdf_path = THESIS_ROOT / "main.pdf"
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="PDF thesis asli belum tersedia.")
    return _download_pdf_response(pdf_path, "main.pdf")
