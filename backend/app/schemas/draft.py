from pydantic import BaseModel


class RevisionDraftRequest(BaseModel):
    source_text: str
    suggestions: list[dict]
    context_label: str
    user_goal: str


class SaveDraftRequest(BaseModel):
    selected_file: str
    selected_label: str
    content: str
    metadata: dict


class DraftLookupRequest(BaseModel):
    draft_json_path: str


class DraftContentSaveRequest(BaseModel):
    draft_json_path: str
    content: str


class DraftActiveStateRequest(BaseModel):
    draft_json_path: str
    is_active_for_full_document: bool


class RevisionDraftDetailResponse(BaseModel):
    selected_file: str = ""
    selected_scope: str = ""
    selected_target_id: str = ""
    selected_label: str = ""
    original_text: str = ""
    revised_text: str = ""
    revision_summary: str = ""
    review_snapshot: dict | None = None
    is_active_for_full_document: bool = False
    created_at: str = ""
    updated_at: str = ""
    json_path: str
    tex_path: str
