export type StructureItem = {
  scope: string;
  target_id: string;
  label: string;
};

export type StructureResponse = {
  chapter_title: string;
  items: StructureItem[];
};

export type DocumentContentResponse = {
  selected_label: string;
  source_text: string;
  start_line: number;
  end_line: number;
};

export type ReviewSuggestion = {
  category: string;
  title: string;
  detail: string;
  paragraph_index: number;
  priority: string;
  suggested_revision?: string;
  source: string;
};

export type ReviewResponse = {
  selected_label: string;
  review_source: string;
  summary: string;
  suggestions: ReviewSuggestion[];
};

export type ReviewSnapshot = {
  schema_version: 1;
  review_source: string;
  user_goal: string;
  created_at: string;
  suggestions: ReviewSuggestion[];
};

export type RevisionDraftResponse = {
  revised_text: string;
  revision_summary: string;
};

export type RevisionDraftRecord = {
  selected_file?: string;
  selected_scope?: string;
  selected_target_id?: string;
  selected_label?: string;
  original_text?: string;
  revised_text?: string;
  revision_summary?: string;
  review_snapshot?: ReviewSnapshot;
  is_active_for_full_document?: boolean;
  created_at?: string;
  updated_at?: string;
  json_path: string;
  tex_path: string;
};

export type RevisionDraftDetail = {
  selected_file: string;
  selected_scope: string;
  selected_target_id: string;
  selected_label: string;
  original_text: string;
  revised_text: string;
  revision_summary: string;
  review_snapshot?: ReviewSnapshot;
  is_active_for_full_document: boolean;
  created_at: string;
  updated_at: string;
  json_path: string;
  tex_path: string;
};

export type CompileStep = {
  name: string;
  command: string;
  returncode: number;
  stdout: string;
  stderr: string;
};

export type CompileResult = {
  success: boolean;
  steps: CompileStep[];
  summary: string;
  log_path: string;
  pdf_path: string;
  pdf_preview_url: string;
  pdf_download_url: string;
};

export type CompareResponse = {
  run_id: string;
  run_root: string;
  preview_mode: "fragment";
  fragment_label: string;
  fragment_scope: string;
  original: CompileResult;
  revised: CompileResult;
  original_text: string;
  revised_text: string;
  diff_html: string;
};

export type FullDocumentBuildResponse = {
  run_id: string;
  run_root: string;
  preview_mode: "full";
  applied_draft_count: number;
  applied_draft_labels: string[];
  compile_result: CompileResult;
  pdf_preview_url: string;
  pdf_download_url: string;
};

const defaultHeaders = {
  "Content-Type": "application/json"
};

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const message = await response.text();
    throw new Error(message || "Request gagal diproses.");
  }

  return response.json() as Promise<T>;
}

export async function listDocuments(): Promise<string[]> {
  const response = await fetch("/api/documents");
  const payload = await readJson<{ items: string[] }>(response);
  return payload.items;
}

export async function getStructure(fileName: string): Promise<StructureResponse> {
  const response = await fetch(`/api/documents/${encodeURIComponent(fileName)}/structure`);
  return readJson<StructureResponse>(response);
}

export async function getDocumentContent(
  fileName: string,
  scope: string,
  targetId: string
): Promise<DocumentContentResponse> {
  const search = new URLSearchParams({
    scope,
    target_id: targetId
  });
  const response = await fetch(
    `/api/documents/${encodeURIComponent(fileName)}/content?${search.toString()}`
  );
  return readJson<DocumentContentResponse>(response);
}

export async function submitReview(payload: {
  selected_file: string;
  selected_scope: string;
  selected_target_id: string;
  user_goal: string;
}): Promise<ReviewResponse> {
  const response = await fetch("/api/review", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<ReviewResponse>(response);
}

export async function createRevisionDraft(payload: {
  source_text: string;
  suggestions: ReviewSuggestion[];
  context_label: string;
  user_goal: string;
}): Promise<RevisionDraftResponse> {
  const response = await fetch("/api/revision-draft", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<RevisionDraftResponse>(response);
}

export async function saveRevisionDraft(payload: {
  selected_file: string;
  selected_label: string;
  content: string;
  metadata: Record<string, unknown>;
}): Promise<{ path: string }> {
  const response = await fetch("/api/revision-drafts/save", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<{ path: string }>(response);
}

export async function listRevisionDrafts(): Promise<RevisionDraftRecord[]> {
  const response = await fetch("/api/revision-drafts");
  return readJson<RevisionDraftRecord[]>(response);
}

export async function loadRevisionDraft(payload: {
  draft_json_path: string;
}): Promise<RevisionDraftDetail> {
  const response = await fetch("/api/revision-drafts/load", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<RevisionDraftDetail>(response);
}

export async function saveRevisionDraftContent(payload: {
  draft_json_path: string;
  content: string;
}): Promise<RevisionDraftDetail> {
  const response = await fetch("/api/revision-drafts/save-content", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<RevisionDraftDetail>(response);
}

export async function setRevisionDraftFullDocumentActive(payload: {
  draft_json_path: string;
  is_active_for_full_document: boolean;
}): Promise<RevisionDraftDetail> {
  const response = await fetch("/api/revision-drafts/set-active", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<RevisionDraftDetail>(response);
}

export async function deleteRevisionDraft(payload: {
  draft_json_path: string;
}): Promise<{ json_path: string; tex_path: string }> {
  const response = await fetch("/api/revision-drafts/delete", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<{ json_path: string; tex_path: string }>(response);
}

export async function compileCompare(payload: {
  draft_json_path: string;
}): Promise<CompareResponse> {
  const response = await fetch("/api/compile/compare", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<CompareResponse>(response);
}

export async function compileEditorPreview(payload: {
  draft_json_path: string;
  content: string;
}): Promise<CompareResponse> {
  const response = await fetch("/api/editor/compile-preview", {
    method: "POST",
    headers: defaultHeaders,
    body: JSON.stringify(payload)
  });
  return readJson<CompareResponse>(response);
}

export async function compileFullDocument(): Promise<FullDocumentBuildResponse> {
  const response = await fetch("/api/compile/full-document", {
    method: "POST",
    headers: defaultHeaders
  });
  return readJson<FullDocumentBuildResponse>(response);
}
