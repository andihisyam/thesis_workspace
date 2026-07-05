import sys

from fastapi import APIRouter

from backend.app.core.config import PROJECT_ROOT, THESIS_ROOT
from backend.app.schemas.draft import RevisionDraftRequest
from backend.app.schemas.review import ReviewRequest, ReviewResponse

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.revision_service import build_revision_draft  # noqa: E402
from app.services.thesis_repository import ThesisRepository  # noqa: E402
from app.workflows.review_graph import run_review_workflow  # noqa: E402

router = APIRouter(tags=["review"])
repository = ThesisRepository(THESIS_ROOT)


@router.post("/review", response_model=ReviewResponse)
def review_document(payload: ReviewRequest) -> ReviewResponse:
    result = run_review_workflow(
        repository=repository,
        selected_file=payload.selected_file,
        user_goal=payload.user_goal,
        selected_scope=payload.selected_scope,
        selected_target_id=payload.selected_target_id
    )
    return ReviewResponse(
        selected_label=result["selected_label"],
        review_source=result["review_source"],
        summary=result["summary"],
        suggestions=result["suggestions"]
    )


@router.post("/revision-draft")
def create_revision_draft(payload: RevisionDraftRequest) -> dict[str, str]:
    revised_text, revision_summary = build_revision_draft(
        source_text=payload.source_text,
        suggestions=payload.suggestions,
        context_label=payload.context_label,
        user_goal=payload.user_goal
    )
    return {
      "revised_text": revised_text,
      "revision_summary": revision_summary
    }
