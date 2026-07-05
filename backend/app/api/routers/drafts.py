import sys

from fastapi import APIRouter, HTTPException

from backend.app.core.config import PROJECT_ROOT, THESIS_ROOT
from backend.app.schemas.draft import (
    DraftActiveStateRequest,
    DraftContentSaveRequest,
    DraftLookupRequest,
    RevisionDraftDetailResponse,
    SaveDraftRequest,
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.thesis_repository import ThesisRepository  # noqa: E402

router = APIRouter(tags=["drafts"])
repository = ThesisRepository(THESIS_ROOT)


@router.get("/revision-drafts")
def list_drafts() -> list[dict]:
    return repository.list_revision_drafts()


@router.post("/revision-drafts/load", response_model=RevisionDraftDetailResponse)
def load_draft(payload: DraftLookupRequest) -> RevisionDraftDetailResponse:
    try:
        draft = repository.load_revision_draft(payload.draft_json_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RevisionDraftDetailResponse(**draft)


@router.post("/revision-drafts/save")
def save_draft(payload: SaveDraftRequest) -> dict[str, str]:
    output_path = repository.save_revision_draft(
        filename=payload.selected_file,
        selected_label=payload.selected_label,
        content=payload.content,
        metadata=payload.metadata,
    )
    return {"path": str(output_path)}


@router.post("/revision-drafts/save-content", response_model=RevisionDraftDetailResponse)
def save_draft_content(payload: DraftContentSaveRequest) -> RevisionDraftDetailResponse:
    try:
        draft = repository.update_revision_draft_content(payload.draft_json_path, payload.content)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return RevisionDraftDetailResponse(**draft)


@router.post("/revision-drafts/set-active", response_model=RevisionDraftDetailResponse)
def set_draft_active_state(payload: DraftActiveStateRequest) -> RevisionDraftDetailResponse:
    try:
        draft = repository.set_full_document_active(
            payload.draft_json_path,
            payload.is_active_for_full_document,
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return RevisionDraftDetailResponse(**draft)


@router.post("/revision-drafts/delete")
def delete_draft(payload: DraftLookupRequest) -> dict[str, str]:
    try:
        deleted = repository.delete_revision_draft(payload.draft_json_path)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return deleted
