export type User = { id: string; email: string; display_name: string; is_admin: boolean };
export type AdminUser = User & { is_active: boolean; created_at: string };
export type Project = { id: string; name: string; description: string; role: string; created_at: string };
export type DocumentRecord = { id: string; filename: string; status: string; page_count: number; structure_confirmed: boolean };
export type Unit = { id: string; parent_id?: string; level: string; number: string; title: string; content: string; start_page: number; end_page: number; sort_order: number; confidence: number };
export type ReferenceRecord = { id: string; citation_key: string; authors: string; title: string; year: string; doi: string; raw_reference: string; source_type: string; confidence: number };
export type ReferencePreviewEntry = { citation_key: string; authors: string; title: string; year: string; doi: string; raw_reference: string; source_type: string; parse_confidence: number };
export type Citation = { id: string; marker: string; context: string; status: string; page_number: number; unit: string; reference?: { id: string; citation_key: string; title: string } };
export type Draft = { id: string; unit_id?: string; title: string; current_version: number; content: string; summary: string };
export type DraftVersion = { id: string; version: number; content: string; summary: string; source: string; created_at: string };
export type Workspace = { id: string; name: string; main_document: string };
export type WorkspaceScaffold = { name: string; main_document: string; paper_size: string; font_size: string; line_spacing: string; margin_top_cm: number; margin_right_cm: number; margin_bottom_cm: number; margin_left_cm: number; font_family: string; chapter_style: string; include_cover: boolean; bibliography_style: string };
export type WorkspaceFile = { path: string; size: number; editable: boolean; kind: "file" | "folder" };
export type Job = { id: string; type: string; status: string; progress_percent: number; progress_message: string; error_message?: string | null; result: Record<string, unknown> };
export type BibExport = { filename: string; content: string; count: number };

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || "").replace(/\/$/, "");

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  if (options.body && !(options.body instanceof FormData)) headers.set("Content-Type", "application/json");
  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, { ...options, headers, credentials: "include" });
  } catch {
    throw new Error("Backend V2 tidak dapat dihubungi. Jalankan backend pada port 8001.");
  }
  if (!response.ok) {
    const payload = await response.json().catch(() => ({ detail: "Request gagal." }));
    throw new Error(payload.detail || "Request gagal.");
  }
  return response.json() as Promise<T>;
}

export const api = {
  me: () => request<User>("/api/v2/auth/me"),
  setupStatus: () => request<{ requires_setup: boolean; user_count: number }>("/api/v2/auth/setup-status"),
  bootstrap: (body: { email: string; display_name: string; password: string }) => request<User>("/api/v2/auth/bootstrap", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) => request<User>("/api/v2/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request("/api/v2/auth/logout", { method: "POST" }),
  users: () => request<AdminUser[]>("/api/v2/users"),
  inviteUser: (body: { email: string; display_name: string; password: string }) => request<User>("/api/v2/users/invite", { method: "POST", body: JSON.stringify(body) }),
  projects: () => request<Project[]>("/api/v2/projects"),
  createProject: (body: { name: string; description: string }) => request<Project>("/api/v2/projects", { method: "POST", body: JSON.stringify(body) }),
  documents: (projectId: string) => request<DocumentRecord[]>(`/api/v2/projects/${projectId}/documents`),
  uploadDocument: (projectId: string, file: File) => {
    const form = new FormData();
    form.append("file", file);
    return request<{ document_id: string; job_id: string }>(`/api/v2/projects/${projectId}/documents`, { method: "POST", body: form });
  },
  deleteDocument: (projectId: string, documentId: string) => request(`/api/v2/projects/${projectId}/documents/${documentId}`, { method: "DELETE" }),
  structure: (projectId: string, documentId: string) => request<{ document: Record<string, unknown>; units: Unit[] }>(`/api/v2/projects/${projectId}/documents/${documentId}/structure`),
  buildStructureFromToc: (projectId: string, documentId: string, content: string) => request<{ status: string; unit_count: number }>(`/api/v2/projects/${projectId}/documents/${documentId}/structure/from-toc`, { method: "POST", body: JSON.stringify({ content }) }),
  detectSubchapters: (projectId: string, documentId: string, chapterId: string) => request<{ status: string; source: string; unit_count: number }>(`/api/v2/projects/${projectId}/documents/${documentId}/structure/detect-subchapters/${chapterId}`, { method: "POST" }),
  saveStructure: (projectId: string, documentId: string, units: Unit[]) => request<{ status: string; unit_count: number }>(`/api/v2/projects/${projectId}/documents/${documentId}/structure`, { method: "PUT", body: JSON.stringify({ units }) }),
  confirmStructure: (projectId: string, documentId: string) => request(`/api/v2/projects/${projectId}/documents/${documentId}/confirm-structure`, { method: "POST" }),
  references: (projectId: string) => request<ReferenceRecord[]>(`/api/v2/projects/${projectId}/references`),
  previewReferences: (projectId: string, content: string, referenceFormat: string) => request<{ count: number; entries: ReferencePreviewEntry[] }>(`/api/v2/projects/${projectId}/references/preview`, { method: "POST", body: JSON.stringify({ content, reference_format: referenceFormat }) }),
  pasteReferences: (projectId: string, content: string, referenceFormat: string) => request<{ imported: number }>(`/api/v2/projects/${projectId}/references/paste`, { method: "POST", body: JSON.stringify({ content, reference_format: referenceFormat }) }),
  uploadReferences: (projectId: string, file: File, referenceFormat: string) => {
    const form = new FormData();
    form.append("file", file);
    form.append("reference_format", referenceFormat);
    return request<{ imported: number }>(`/api/v2/projects/${projectId}/references/import`, { method: "POST", body: form });
  },
  updateReference: (projectId: string, referenceId: string, body: { citation_key: string; authors: string; title: string; year: string; doi: string; raw_reference: string }) => request(`/api/v2/projects/${projectId}/references/${referenceId}`, { method: "PUT", body: JSON.stringify(body) }),
  deleteReference: (projectId: string, referenceId: string) => request(`/api/v2/projects/${projectId}/references/${referenceId}`, { method: "DELETE" }),
  exportReferencesBib: (projectId: string) => request<BibExport>(`/api/v2/projects/${projectId}/references/bib`),
  insertReferencesBib: (projectId: string, workspaceId: string) => request<{ path: string; count: number }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/references-bib`, { method: "POST" }),
  mapCitations: (projectId: string) => request<{ mapped: number }>(`/api/v2/projects/${projectId}/citations/map`, { method: "POST" }),
  citations: (projectId: string) => request<Citation[]>(`/api/v2/projects/${projectId}/citations`),
  review: (projectId: string, unitId: string, userGoal: string) => request<{ id: string; source: string; summary: string; suggestions: Array<Record<string, unknown>> }>(`/api/v2/projects/${projectId}/reviews`, { method: "POST", body: JSON.stringify({ unit_id: unitId, user_goal: userGoal }) }),
  startReviewJob: (projectId: string, unitId: string, userGoal: string) => request<{ job_id: string; status: string }>(`/api/v2/projects/${projectId}/reviews/jobs`, { method: "POST", body: JSON.stringify({ unit_id: unitId, user_goal: userGoal }) }),
  drafts: (projectId: string) => request<Draft[]>(`/api/v2/projects/${projectId}/drafts`),
  createDraft: (projectId: string, unitId: string) => request<Draft>(`/api/v2/projects/${projectId}/drafts`, { method: "POST", body: JSON.stringify({ unit_id: unitId }) }),
  startDraftJob: (projectId: string, unitId: string) => request<{ job_id: string; status: string }>(`/api/v2/projects/${projectId}/drafts/jobs`, { method: "POST", body: JSON.stringify({ unit_id: unitId }) }),
  deleteDraft: (projectId: string, draftId: string) => request(`/api/v2/projects/${projectId}/drafts/${draftId}`, { method: "DELETE" }),
  saveDraft: (projectId: string, draftId: string, content: string, summary = "") => request(`/api/v2/projects/${projectId}/drafts/${draftId}/versions`, { method: "POST", body: JSON.stringify({ content, summary }) }),
  draftVersions: (projectId: string, draftId: string) => request<DraftVersion[]>(`/api/v2/projects/${projectId}/drafts/${draftId}/versions`),
  restoreDraftVersion: (projectId: string, draftId: string, versionId: string) => request(`/api/v2/projects/${projectId}/drafts/${draftId}/versions/${versionId}/restore`, { method: "POST" }),
  workspaces: (projectId: string) => request<Workspace[]>(`/api/v2/projects/${projectId}/workspaces`),
  createWorkspace: (projectId: string, name: string) => request<Workspace>(`/api/v2/projects/${projectId}/workspaces`, { method: "POST", body: JSON.stringify({ name, main_document: "main.tex" }) }),
  createAutoWorkspace: (projectId: string, body: WorkspaceScaffold) => request<Workspace>(`/api/v2/projects/${projectId}/workspaces/auto`, { method: "POST", body: JSON.stringify(body) }),
  workspaceSnippet: (projectId: string, body: WorkspaceScaffold) => request<{ mode: string; files: Record<string, string> }>(`/api/v2/projects/${projectId}/workspaces/snippet`, { method: "POST", body: JSON.stringify(body) }),
  workspaceFiles: (projectId: string, workspaceId: string) => request<{ main_document: string; files: WorkspaceFile[] }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/files`),
  readFile: (projectId: string, workspaceId: string, path: string) => request<{ path: string; content: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/files/content?path=${encodeURIComponent(path)}`),
  createFolder: (projectId: string, workspaceId: string, path: string) => request<{ path: string; kind: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/folders`, { method: "POST", body: JSON.stringify({ path }) }),
  createFile: (projectId: string, workspaceId: string, path: string, content = "") => request<{ path: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/files`, { method: "POST", body: JSON.stringify({ path, content }) }),
  uploadWorkspaceFile: (projectId: string, workspaceId: string, path: string, file: File) => {
    const form = new FormData();
    form.append("path", path);
    form.append("file", file);
    return request<{ path: string; kind: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/files/upload`, { method: "POST", body: form });
  },
  deleteFile: (projectId: string, workspaceId: string, path: string) => request<{ status: string; path: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/files?path=${encodeURIComponent(path)}`, { method: "DELETE" }),
  renameFile: (projectId: string, workspaceId: string, path: string, newName: string) => request<{ old_path: string; path: string; kind: "file" | "folder"; main_document: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/files/rename`, { method: "PUT", body: JSON.stringify({ path, new_name: newName }) }),
  saveFile: (projectId: string, workspaceId: string, path: string, content: string) => request(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/files/content`, { method: "PUT", body: JSON.stringify({ path, content }) }),
  compile: (projectId: string, workspaceId: string) => request<{ job_id: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/compile`, { method: "POST" }),
  compileFile: (projectId: string, workspaceId: string, path: string) => request<{ job_id: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/compile-file?path=${encodeURIComponent(path)}`, { method: "POST" }),
  job: (jobId: string) => request<Job>(`/api/v2/jobs/${jobId}`),
  insertDraft: (projectId: string, workspaceId: string, draftId: string, targetPath: string) => request<{ path: string; mode: string; inserted_at: string; draft_file: string; input_command: string }>(`/api/v2/projects/${projectId}/workspaces/${workspaceId}/insert-draft`, { method: "POST", body: JSON.stringify({ draft_id: draftId, target_path: targetPath, mode: "append" }) })
};
