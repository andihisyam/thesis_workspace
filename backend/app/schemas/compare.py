from pydantic import BaseModel


class CompareRequest(BaseModel):
    draft_json_path: str


class CompileStepResponse(BaseModel):
    name: str
    command: str
    returncode: int
    stdout: str
    stderr: str


class CompileResultResponse(BaseModel):
    success: bool
    steps: list[CompileStepResponse]
    summary: str
    log_path: str
    pdf_path: str
    pdf_preview_url: str = ""
    pdf_download_url: str = ""


class CompareResponse(BaseModel):
    run_id: str
    run_root: str
    preview_mode: str = "fragment"
    fragment_label: str = ""
    fragment_scope: str = ""
    original: CompileResultResponse
    revised: CompileResultResponse
    original_text: str
    revised_text: str
    diff_html: str


class FullDocumentBuildResponse(BaseModel):
    run_id: str
    run_root: str
    preview_mode: str = "full"
    applied_draft_count: int
    applied_draft_labels: list[str]
    compile_result: CompileResultResponse
    pdf_preview_url: str = ""
    pdf_download_url: str = ""
