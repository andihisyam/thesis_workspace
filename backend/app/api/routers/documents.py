import sys

from fastapi import APIRouter

from backend.app.core.config import PROJECT_ROOT, THESIS_ROOT
from backend.app.schemas.document import (
    DocumentContentResponse,
    DocumentListResponse,
    StructureItem,
    StructureResponse,
)

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.latex_structure_service import (  # noqa: E402
    build_review_menu,
    parse_latex_structure,
    resolve_review_unit,
)
from app.services.thesis_repository import ThesisRepository  # noqa: E402

router = APIRouter(tags=["documents"])
repository = ThesisRepository(THESIS_ROOT)


@router.get("/documents", response_model=DocumentListResponse)
def list_documents() -> DocumentListResponse:
    return DocumentListResponse(items=repository.list_tex_files())


@router.get("/documents/{file_name}/structure", response_model=StructureResponse)
def get_structure(file_name: str) -> StructureResponse:
    content = repository.read_tex(file_name)
    structure = parse_latex_structure(file_name, content)
    items = [
        StructureItem(
            scope=item["scope"],
            target_id=item["target_id"],
            label=item["label"],
        )
        for item in build_review_menu(structure)
    ]
    return StructureResponse(
        chapter_title=structure["chapter"]["chapter_title"],
        items=items,
    )


@router.get("/documents/{file_name}/content", response_model=DocumentContentResponse)
def get_content(
    file_name: str,
    scope: str = "chapter",
    target_id: str = "chapter:full",
) -> DocumentContentResponse:
    content = repository.read_tex(file_name)
    structure = parse_latex_structure(file_name, content)
    unit = resolve_review_unit(structure, scope, target_id)
    return DocumentContentResponse(
        selected_label=unit["path"],
        source_text=unit["raw_latex"],
        start_line=unit["start_line"],
        end_line=unit["end_line"],
    )
