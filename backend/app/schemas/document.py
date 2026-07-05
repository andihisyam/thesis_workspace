from pydantic import BaseModel


class DocumentListResponse(BaseModel):
    items: list[str]


class StructureItem(BaseModel):
    scope: str
    target_id: str
    label: str


class StructureResponse(BaseModel):
    chapter_title: str
    items: list[StructureItem]


class DocumentContentResponse(BaseModel):
    selected_label: str
    source_text: str
    start_line: int
    end_line: int
