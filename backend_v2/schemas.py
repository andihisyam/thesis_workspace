from pydantic import BaseModel, Field


class BootstrapRequest(BaseModel):
    email: str
    display_name: str
    password: str = Field(min_length=8)


class LoginRequest(BaseModel):
    email: str
    password: str


class InviteRequest(BootstrapRequest):
    pass


class ProjectCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    description: str = ""


class MemberCreate(BaseModel):
    email: str
    role: str = "EDITOR"


class StructureUnitUpdate(BaseModel):
    id: str = ""
    parent_id: str | None = None
    level: str
    number: str = ""
    title: str
    start_page: int
    end_page: int
    sort_order: int


class StructureUpdate(BaseModel):
    units: list[StructureUnitUpdate]


class TocStructureRequest(BaseModel):
    content: str = Field(min_length=1)


class ReferencePasteRequest(BaseModel):
    content: str = Field(min_length=1)
    reference_format: str = "auto"


class ReferencePreviewRequest(BaseModel):
    content: str = Field(min_length=1)
    reference_format: str = "auto"


class ReferenceUpdateRequest(BaseModel):
    citation_key: str = Field(min_length=1, max_length=160)
    authors: str = ""
    title: str = ""
    year: str = ""
    doi: str = ""
    raw_reference: str = Field(min_length=1)


class CitationConfirmRequest(BaseModel):
    reference_id: str


class ReviewCreate(BaseModel):
    unit_id: str
    user_goal: str = "Periksa kualitas akademik, kejelasan argumen, dan kebutuhan sitasi."


class DraftCreate(BaseModel):
    unit_id: str
    title: str = ""
    content: str | None = None
    summary: str = ""


class DraftSave(BaseModel):
    content: str
    summary: str = ""


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    main_document: str = "main.tex"


class WorkspaceScaffoldRequest(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    main_document: str = "main.tex"
    paper_size: str = "a4paper"
    font_size: str = "12pt"
    line_spacing: str = "1.5"
    margin_top_cm: float = 4.0
    margin_right_cm: float = 3.0
    margin_bottom_cm: float = 3.0
    margin_left_cm: float = 4.0
    font_family: str = "times"
    chapter_style: str = "default"
    include_cover: bool = True
    bibliography_style: str = "numeric"


class WorkspaceFolderCreate(BaseModel):
    path: str


class WorkspaceFileCreate(BaseModel):
    path: str
    content: str = ""


class WorkspaceFileSave(BaseModel):
    path: str
    content: str


class WorkspaceRename(BaseModel):
    path: str
    new_name: str = Field(min_length=1, max_length=240)


class WorkspaceMainDocument(BaseModel):
    path: str


class InsertDraftRequest(BaseModel):
    draft_id: str
    target_path: str
    mode: str = "append"



