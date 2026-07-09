import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Navigate, Route, Routes, useNavigate, useParams } from "react-router-dom";
import CollaborativeEditor from "./CollaborativeEditor";
import { api, type AdminUser, type Draft, type DraftVersion, type ReferencePreviewEntry, type ReferenceRecord, type Unit, type User, type Workspace, type WorkspaceScaffold } from "./api";

export default function App() {
  const me = useQuery({ queryKey: ["me"], queryFn: api.me, retry: false });
  if (me.isLoading) return <Splash text="Menyiapkan workspace..." />;
  const homePath = me.data?.is_admin ? "/admin" : "/projects";
  return (
    <Routes>
      <Route path="/login" element={me.data ? <Navigate to={homePath} /> : <AuthPage />} />
      <Route path="/admin" element={me.data ? me.data.is_admin ? <AdminDashboard user={me.data} /> : <Navigate to="/projects" /> : <Navigate to="/login" />} />
      <Route path="/projects" element={me.data ? me.data.is_admin ? <Navigate to="/admin" /> : <ProjectsPage user={me.data} /> : <Navigate to="/login" />} />
      <Route path="/projects/:projectId/*" element={me.data ? <ProjectShell user={me.data} /> : <Navigate to="/login" />} />
      <Route path="*" element={<Navigate to={me.data ? homePath : "/login"} />} />
    </Routes>
  );
}

function Splash({ text }: { text: string }) {
  return <div className="splash"><div className="loader" /><p>{text}</p></div>;
}

function AuthPage() {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [bootstrap, setBootstrap] = useState(false);
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const setup = useQuery({ queryKey: ["setup-status"], queryFn: api.setupStatus, retry: false });
  useEffect(() => {
    if (setup.data?.requires_setup) setBootstrap(true);
  }, [setup.data]);
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const formError = !emailValid
    ? "Masukkan email yang valid."
    : password.length < 8
      ? "Password minimal 8 karakter."
      : bootstrap && name.trim().length < 2
        ? "Nama minimal 2 karakter."
        : "";
  const mutation = useMutation({
    mutationFn: () => bootstrap ? api.bootstrap({ email, display_name: name, password }) : api.login({ email, password }),
    onSuccess: (user) => { queryClient.setQueryData(["me"], user); navigate(user.is_admin ? "/admin" : "/projects"); }
  });
  return (
    <main className="auth-page">
      <section className="auth-story"><span className="eyebrow">PRIVATE WRITING ROOM</span><h1>Thesis Atelier</h1><p>Satu ruang tenang untuk membaca PDF, menjaga referensi, merancang revisi, dan menulis LaTeX bersama.</p><div className="orb orb-one" /><div className="orb orb-two" /></section>
      <section className="auth-card">
        <div><span className="eyebrow">{bootstrap ? "FIRST SETUP" : "WELCOME BACK"}</span><h2>{bootstrap ? "Buat admin pertama" : "Masuk ke workspace"}</h2></div>
        {setup.isLoading && <p className="notice">Memeriksa status backend...</p>}
        {setup.error && <p className="error">{(setup.error as Error).message}</p>}
        {bootstrap && <Field label="Nama" value={name} onChange={setName} />}
        <Field label="Email" value={email} onChange={setEmail} type="email" />
        <Field label="Password" value={password} onChange={setPassword} type="password" />
        {mutation.error && <p className="error">{(mutation.error as Error).message}</p>}
        <button className="primary" onClick={() => mutation.mutate()} disabled={mutation.isPending || Boolean(formError) || setup.isLoading}>{mutation.isPending ? "Memproses..." : bootstrap ? "Buat Admin" : "Masuk"}</button>
        {formError && (email || password || name) && <small className="form-hint">{formError}</small>}
        {!setup.data?.requires_setup && <button className="text-button" onClick={() => setBootstrap(!bootstrap)}>{bootstrap ? "Sudah punya akun? Masuk" : "Setup pertama kali"}</button>}
      </section>
    </main>
  );
}

function Field({ label, value, onChange, type = "text" }: { label: string; value: string; onChange: (v: string) => void; type?: string }) {
  return <label className="field"><span>{label}</span><input type={type} value={value} onChange={(event) => onChange(event.target.value)} /></label>;
}

function ProjectsPage({ user }: { user: User }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [name, setName] = useState("");
  const create = useMutation({ mutationFn: () => api.createProject({ name, description: "" }), onSuccess: (project) => { queryClient.invalidateQueries({ queryKey: ["projects"] }); navigate(`/projects/${project.id}`); } });
  return (
    <main className="projects-page">
      <header className="topbar"><div><span className="logo-mark">TA</span><strong>Thesis Atelier</strong></div><span>{user.display_name}</span></header>
      <section className="projects-hero"><span className="eyebrow">YOUR WORKSPACES</span><h1>Setiap skripsi punya ruangnya sendiri.</h1><p>Dokumen, referensi, draft, dan file LaTeX tetap terpisah per project.</p></section>
      <section className="project-grid">
        <article className="new-project-card"><h2>Project baru</h2><Field label="Nama project" value={name} onChange={setName} /><button className="primary" onClick={() => create.mutate()} disabled={!name.trim()}>Buat Workspace</button></article>
        {projects.data?.map((project) => <button className="project-card" key={project.id} onClick={() => navigate(`/projects/${project.id}`)}><span className="project-index">{project.role}</span><h2>{project.name}</h2><p>{project.description || "PDF review dan LaTeX workspace"}</p><span className="open-label">Buka project -&gt;</span></button>)}
      </section>
    </main>
  );
}

function AdminDashboard({ user }: { user: User }) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const [name, setName] = useState("");
  const create = useMutation({ mutationFn: () => api.createProject({ name, description: "" }), onSuccess: (project) => { queryClient.invalidateQueries({ queryKey: ["projects"] }); navigate(`/projects/${project.id}`); } });
  return <main className="projects-page admin-dashboard"><header className="topbar"><div><span className="logo-mark">TA</span><strong>Admin Dashboard</strong></div><span>{user.display_name} - Admin</span></header><section className="projects-hero"><span className="eyebrow">ADMIN DASHBOARD</span><h1>Kelola user dan semua project dari satu tempat.</h1><p>Admin bisa membuat user baru, melihat semua workspace, dan masuk ke project mana pun untuk membantu revisi atau debugging.</p></section><AdminPanel /><section className="project-grid"><article className="new-project-card"><h2>Project admin baru</h2><Field label="Nama project" value={name} onChange={setName} /><button className="primary" onClick={() => create.mutate()} disabled={!name.trim()}>Buat Workspace</button></article>{projects.data?.map((project) => <button className="project-card" key={project.id} onClick={() => navigate(`/projects/${project.id}`)}><span className="project-index">{project.role}</span><h2>{project.name}</h2><p>{project.description || "PDF review dan LaTeX workspace"}</p><span className="open-label">Buka project -&gt;</span></button>)}</section></main>;
}

function AdminPanel() {
  const queryClient = useQueryClient();
  const users = useQuery({ queryKey: ["admin-users"], queryFn: api.users });
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const emailValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  const canInvite = name.trim().length >= 2 && emailValid && password.length >= 8;
  const invite = useMutation({
    mutationFn: () => api.inviteUser({ email, display_name: name, password }),
    onSuccess: () => {
      setName("");
      setEmail("");
      setPassword("");
      queryClient.invalidateQueries({ queryKey: ["admin-users"] });
    }
  });
  return <section className="admin-panel"><div className="admin-copy"><span className="eyebrow">ADMIN CONTROL</span><h2>Kelola akses user</h2><p>User baru hanya bisa dibuat dari sini. Setelah login, mereka tetap boleh membuat project sendiri; admin otomatis bisa membuka semua project.</p></div><div className="admin-form"><Field label="Nama user" value={name} onChange={setName} /><Field label="Email user" value={email} onChange={setEmail} type="email" /><Field label="Password sementara" value={password} onChange={setPassword} type="password" /><button className="primary" disabled={!canInvite || invite.isPending} onClick={() => invite.mutate()}>{invite.isPending ? "Membuat akun..." : "Buat User"}</button>{invite.error && <p className="error">{(invite.error as Error).message}</p>}{invite.isSuccess && <p className="notice">User berhasil dibuat. Berikan email dan password sementara ini ke user.</p>}</div><div className="admin-users"><strong>Daftar akun</strong>{users.data?.map((item: AdminUser) => <article key={item.id}><span>{item.display_name}</span><small>{item.email}</small><code>{item.is_admin ? "ADMIN" : item.is_active ? "USER" : "INACTIVE"}</code></article>)}</div></section>;
}
const tabs = [
  ["", "Overview"], ["pdf", "PDF Review"], ["references", "References"], ["drafts", "Draft Manager"], ["workspace", "LaTeX Workspace"]
] as const;

const reviewJobKey = (projectId: string) => `thesis-review-job:${projectId}`;
const draftJobKey = (projectId: string) => `thesis-draft-job:${projectId}`;
const draftNoticeKey = (projectId: string) => `thesis-draft-notice:${projectId}`;
const compileJobKey = (projectId: string, workspaceId: string) => `thesis-compile-job:${projectId}:${workspaceId}`;
const workspaceDraftKey = (projectId: string, workspaceId: string, path: string) => `thesis-workspace-draft:${projectId}:${workspaceId}:${path}`;

function ProjectShell({ user }: { user: User }) {
  const { projectId = "" } = useParams();
  const projects = useQuery({ queryKey: ["projects"], queryFn: api.projects });
  const project = projects.data?.find((item) => item.id === projectId);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  return (
    <div className={`app-shell ${sidebarCollapsed ? "app-shell-collapsed" : ""}`}>
      <aside className={`sidebar ${sidebarCollapsed ? "sidebar-collapsed" : ""}`}><div className="sidebar-top"><Link to={user.is_admin ? "/admin" : "/projects"} className="brand"><span className="logo-mark">TA</span>{!sidebarCollapsed && <div><strong>Thesis Atelier</strong><small>{project?.name || "Project"}</small></div>}</Link><button className="sidebar-toggle" onClick={() => setSidebarCollapsed((current) => !current)}>{sidebarCollapsed ? ">" : "<"}</button></div><nav>{tabs.map(([path, label]) => <Link key={path} to={`/projects/${projectId}${path ? `/${path}` : ""}`}>{sidebarCollapsed ? label[0] : label}</Link>)}</nav>{!sidebarCollapsed && <div className="sidebar-user"><span>{user.display_name}</span><small>{user.email}</small></div>}</aside>
      <main className="content"><Routes><Route index element={<Overview projectId={projectId} />} /><Route path="pdf" element={<PdfReview projectId={projectId} />} /><Route path="references" element={<References projectId={projectId} />} /><Route path="drafts" element={<Drafts projectId={projectId} />} /><Route path="workspace" element={<WorkspacePage projectId={projectId} user={user} />} /></Routes></main>
    </div>
  );
}

function Overview({ projectId }: { projectId: string }) {
  const docs = useQuery({ queryKey: ["documents", projectId], queryFn: () => api.documents(projectId) });
  const refs = useQuery({ queryKey: ["references", projectId], queryFn: () => api.references(projectId) });
  const drafts = useQuery({ queryKey: ["drafts", projectId], queryFn: () => api.drafts(projectId) });
  const spaces = useQuery({ queryKey: ["workspaces", projectId], queryFn: () => api.workspaces(projectId) });
  return <Page title="Project Overview" kicker="PRIVATE PROJECT"><div className="metrics"><Metric value={docs.data?.length || 0} label="PDF" /><Metric value={refs.data?.length || 0} label="Referensi" /><Metric value={drafts.data?.length || 0} label="Draft" /><Metric value={spaces.data?.length || 0} label="Workspace" /></div><section className="panel"><h2>Alur kerja</h2><div className="flow"><span>01 Upload PDF</span><span>02 Structure Builder</span><span>03 Petakan sitasi</span><span>04 Review & draft</span><span>05 Tulis bersama</span></div></section></Page>;
}

function Metric({ value, label }: { value: number; label: string }) { return <div className="metric"><strong>{String(value).padStart(2, "0")}</strong><span>{label}</span></div>; }
function Page({ title, kicker, children, hideHeading = false, className = "" }: { title: string; kicker: string; children: React.ReactNode; hideHeading?: boolean; className?: string }) { return <div className={`page ${className}`.trim()}>{!hideHeading && <header className="page-heading"><span className="eyebrow">{kicker}</span><h1>{title}</h1></header>}{children}</div>; }

function PdfReview({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const [documentId, setDocumentId] = useState("");
  const [uploadJobId, setUploadJobId] = useState("");
  const [unitId, setUnitId] = useState("");
  const [selectedChapterId, setSelectedChapterId] = useState("");
  const [goal, setGoal] = useState("Periksa kualitas akademik, koherensi argumen, dan kebutuhan sitasi.");
  const [editableUnits, setEditableUnits] = useState<Unit[]>([]);
  const [structureSaved, setStructureSaved] = useState(false);
  const [draftNotice, setDraftNotice] = useState(localStorage.getItem(draftNoticeKey(projectId)) || "");
  const [reviewJobId, setReviewJobId] = useState(localStorage.getItem(reviewJobKey(projectId)) || "");
  const [draftJobId, setDraftJobId] = useState(localStorage.getItem(draftJobKey(projectId)) || "");

  const uploadJob = useQuery({ queryKey: ["job", uploadJobId], queryFn: () => api.job(uploadJobId), enabled: Boolean(uploadJobId), refetchInterval: (query) => ["SUCCEEDED", "FAILED"].includes(query.state.data?.status || "") ? false : 1500 });
  const uploadPollingActive = Boolean(uploadJobId) && !["SUCCEEDED", "FAILED"].includes(uploadJob.data?.status || "");
  const docs = useQuery({ queryKey: ["documents", projectId], queryFn: () => api.documents(projectId), refetchInterval: uploadPollingActive ? 2000 : false });
  const reviewJob = useQuery({ queryKey: ["job", reviewJobId], queryFn: () => api.job(reviewJobId), enabled: Boolean(reviewJobId), refetchInterval: (query) => ["SUCCEEDED", "FAILED"].includes(query.state.data?.status || "") ? false : 1500 });
  const draftJob = useQuery({ queryKey: ["job", draftJobId], queryFn: () => api.job(draftJobId), enabled: Boolean(draftJobId), refetchInterval: (query) => ["SUCCEEDED", "FAILED"].includes(query.state.data?.status || "") ? false : 1500 });
  const structure = useQuery({ queryKey: ["structure", projectId, documentId], queryFn: () => api.structure(projectId, documentId), enabled: Boolean(documentId), refetchInterval: (query) => query.state.data?.units.length ? false : 2000 });

  const upload = useMutation({
    mutationFn: (file: File) => api.uploadDocument(projectId, file),
    onSuccess: (data) => {
      setDocumentId(data.document_id);
      setUnitId("");
      setSelectedChapterId("");
      setUploadJobId(data.job_id);
      setStructureSaved(false);
      queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
    }
  });
  const detectSubchapters = useMutation({
    mutationFn: () => api.detectSubchapters(projectId, documentId, selectedChapterId),
    onSuccess: () => {
      setUnitId("");
      setStructureSaved(false);
      queryClient.invalidateQueries({ queryKey: ["structure", projectId, documentId] });
      queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
    }
  });
  const saveStructure = useMutation({
    mutationFn: () => api.saveStructure(projectId, documentId, editableUnits),
    onSuccess: () => {
      setStructureSaved(true);
      queryClient.invalidateQueries({ queryKey: ["structure", projectId, documentId] });
      const firstReviewable = editableUnits.find((unit) => unit.level !== "CHAPTER" && unit.level !== "FRONTMATTER");
      if (firstReviewable) setUnitId(firstReviewable.id);
    }
  });
  const startReview = useMutation({
    mutationFn: () => api.startReviewJob(projectId, unitId, goal),
    onSuccess: (data) => {
      setReviewJobId(data.job_id);
      localStorage.setItem(reviewJobKey(projectId), data.job_id);
    }
  });
  const startDraft = useMutation({
    mutationFn: () => api.startDraftJob(projectId, unitId),
    onSuccess: (data) => {
      setDraftJobId(data.job_id);
      localStorage.setItem(draftJobKey(projectId), data.job_id);
      setDraftNotice("");
      localStorage.removeItem(draftNoticeKey(projectId));
    }
  });
  const removeDocument = useMutation({
    mutationFn: (targetDocumentId: string) => api.deleteDocument(projectId, targetDocumentId),
    onSuccess: (_data, targetDocumentId) => {
      if (documentId === targetDocumentId) {
        setDocumentId("");
        setUnitId("");
        setSelectedChapterId("");
        setEditableUnits([]);
        setStructureSaved(false);
      }
      queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
      queryClient.invalidateQueries({ queryKey: ["structure", projectId, targetDocumentId] });
      queryClient.invalidateQueries({ queryKey: ["drafts", projectId] });
      queryClient.invalidateQueries({ queryKey: ["citations", projectId] });
    }
  });

  useEffect(() => {
    if (uploadJob.data?.status === "SUCCEEDED") {
      setStructureSaved(false);
      setUploadJobId("");
      queryClient.invalidateQueries({ queryKey: ["documents", projectId] });
      queryClient.invalidateQueries({ queryKey: ["structure", projectId, documentId] });
    }
    if (uploadJob.data?.status === "FAILED") {
      setUploadJobId("");
    }
  }, [documentId, projectId, queryClient, uploadJob.data?.status]);

  useEffect(() => {
    if (!documentId && docs.data?.length) setDocumentId(docs.data[0].id);
  }, [docs.data, documentId]);

  useEffect(() => {
    if (structure.data?.units) setEditableUnits(structure.data.units);
  }, [structure.data?.units]);

  useEffect(() => {
    const chaptersFromEditable = editableUnits.filter((unit) => unit.level === "CHAPTER");
    if (!chaptersFromEditable.length) {
      if (selectedChapterId) setSelectedChapterId("");
      return;
    }
    const stillExists = chaptersFromEditable.some((unit) => unit.id === selectedChapterId);
    if (!selectedChapterId || !stillExists) setSelectedChapterId(chaptersFromEditable[0].id);
  }, [editableUnits, selectedChapterId]);

  useEffect(() => {
    if (reviewJob.data?.status === "FAILED") localStorage.removeItem(reviewJobKey(projectId));
    if (draftJob.data?.status === "FAILED") localStorage.removeItem(draftJobKey(projectId));
    if (draftJob.data?.status === "SUCCEEDED") {
      localStorage.removeItem(draftJobKey(projectId));
      queryClient.invalidateQueries({ queryKey: ["drafts", projectId] });
      const message = typeof draftJob.data.result.next_step === "string" ? draftJob.data.result.next_step : "Draft .tex selesai dibuat. Silakan cek Draft Manager.";
      setDraftNotice(message);
      localStorage.setItem(draftNoticeKey(projectId), message);
    }
  }, [draftJob.data, projectId, queryClient, reviewJob.data?.status]);

  const selectedDoc = docs.data?.find((doc) => doc.id === documentId);
  const isProcessing = upload.isPending || ["QUEUED", "RUNNING"].includes(uploadJob.data?.status || "") || selectedDoc?.status === "QUEUED";
  const chapters = editableUnits.filter((unit) => unit.level === "CHAPTER");
  const selected = editableUnits.find((unit) => unit.id === unitId) || structure.data?.units.find((unit) => unit.id === unitId);
  const reviewResult = reviewJob.data?.status === "SUCCEEDED" && reviewJob.data.result.unit_id === unitId ? reviewJob.data.result : null;

  const updateUnit = (id: string, patch: Partial<Unit>) => {
    setStructureSaved(false);
    setEditableUnits((items) => items.map((item) => item.id === id ? { ...item, ...patch } : item));
  };
  const addUnit = (level: string) => {
    setStructureSaved(false);
    setEditableUnits((items) => {
      const last = items[items.length - 1];
      const nextPage = last?.end_page || 1;
      const unit: Unit = { id: `temp-${Date.now()}-${Math.random()}`, parent_id: undefined, level, number: "", title: "Bagian Baru", content: "", start_page: nextPage, end_page: nextPage, sort_order: items.length, confidence: 1 };
      setUnitId(unit.id);
      return [...items, unit].map((item, index) => ({ ...item, sort_order: index }));
    });
  };
  const deleteUnit = (id: string) => {
    setStructureSaved(false);
    if (unitId === id) setUnitId("");
    if (selectedChapterId === id) setSelectedChapterId("");
    setEditableUnits((items) => items.filter((item) => item.id !== id).map((item, index) => ({ ...item, sort_order: index })));
  };

  return <Page title="PDF Review" kicker="STRUCTURE BUILDER"><section className="panel upload-guide"><div><span className="eyebrow">LANGKAH PERTAMA</span><h2>Silakan upload dokumen skripsi dalam bentuk PDF.</h2><p>Upload PDF lalu lanjutkan edit struktur di bawah.</p></div><label className="upload-box"><input type="file" accept="application/pdf" onChange={(event) => event.target.files?.[0] && upload.mutate(event.target.files[0])} /><strong>Pilih file PDF skripsi</strong><small>Format: .pdf</small></label></section>{(isProcessing || structure.isLoading) && <section className="panel processing-panel"><div className="loader" /><div><h2>{uploadJob.data?.progress_message || "Memproses dokumen skripsi..."}</h2><p>{uploadJob.data ? `${uploadJob.data.progress_percent}% selesai` : "Mohon tunggu sebentar, daftar BAB akan muncul otomatis setelah ekstraksi selesai."}</p></div></section>}<div className="split"><section className="panel"><h2>Dokumen skripsi</h2><div className="list">{docs.data?.map((doc) => <div className={`document-row ${documentId === doc.id ? "active-row" : ""}`} key={doc.id}><button className="document-select" onClick={() => { setDocumentId(doc.id); setUnitId(""); setSelectedChapterId(""); setStructureSaved(false); }}><span>{doc.filename}</span><small>{doc.status}</small></button><button className="danger-button compact-danger" disabled={removeDocument.isPending} onClick={() => removeDocument.mutate(doc.id)}>Hapus</button></div>)}</div>{removeDocument.error && <p className="error">{(removeDocument.error as Error).message}</p>}{!docs.data?.length && <p className="notice">Belum ada dokumen. Upload PDF skripsi terlebih dahulu.</p>}</section><section className="panel structure-builder"><h2>Deteksi Sub Bab</h2><select value={selectedChapterId} onChange={(event) => setSelectedChapterId(event.target.value)}><option value="">Pilih BAB...</option>{chapters.map((chapter) => <option value={chapter.id} key={chapter.id}>{chapter.number} {chapter.title}</option>)}</select><button className="primary" disabled={!documentId || !selectedChapterId || detectSubchapters.isPending} onClick={() => detectSubchapters.mutate()}>{detectSubchapters.isPending ? "Mendeteksi sub bab..." : "Deteksi Sub Bab"}</button>{detectSubchapters.error && <p className="error">{(detectSubchapters.error as Error).message}</p>}{detectSubchapters.data && <p className="notice">Struktur diperbarui dari {detectSubchapters.data.source} dengan {detectSubchapters.data.unit_count} bagian baru.</p>}</section></div>{documentId && <section className="panel"><div className="panel-title"><div><h2>Struktur dokumen</h2><p>Edit struktur di sini sebelum review.</p></div><div className="structure-actions"><button className="secondary" onClick={() => addUnit("CHAPTER")}>Tambah Bab</button><button className="secondary" onClick={() => addUnit("SUBCHAPTER")}>Tambah Sub Bab</button><button className="secondary" onClick={() => addUnit("SUBSUBCHAPTER")}>Tambah Sub Sub Bab</button></div></div>{editableUnits.length ? <><div className="structure-editor">{editableUnits.map((unit) => <article className={`structure-edit-row level-${unit.level.toLowerCase()}`} key={unit.id}><select value={unit.level} onChange={(event) => updateUnit(unit.id, { level: event.target.value })}><option value="CHAPTER">Bab</option><option value="SUBCHAPTER">Sub Bab</option><option value="SUBSUBCHAPTER">Sub Sub Bab</option><option value="FRONTMATTER">Bagian Awal</option></select><input value={unit.number} onChange={(event) => updateUnit(unit.id, { number: event.target.value })} placeholder="Nomor" /><input value={unit.title} onChange={(event) => updateUnit(unit.id, { title: event.target.value })} placeholder="Judul" /><input type="number" value={unit.start_page} onChange={(event) => updateUnit(unit.id, { start_page: Number(event.target.value) })} /><input type="number" value={unit.end_page} onChange={(event) => updateUnit(unit.id, { end_page: Number(event.target.value) })} /><button className={unitId === unit.id ? "active-row" : ""} onClick={() => setUnitId(unit.id)}>Review</button><button className="danger-button" onClick={() => deleteUnit(unit.id)}>Hapus</button></article>)}</div><div className="structure-save-bar"><div><strong>Simpan kalau sudah sesuai.</strong></div><button className="primary" disabled={!editableUnits.length || saveStructure.isPending} onClick={() => saveStructure.mutate()}>{saveStructure.isPending ? "Menyimpan..." : "Simpan Struktur"}</button></div>{structureSaved && <p className="notice">Struktur tersimpan.</p>}</> : !isProcessing ? <p className="notice">Struktur belum tersedia. Upload PDF agar sistem mendeteksi BAB otomatis.</p> : null}</section>}{selected && <section className="panel review-panel"><div><h2>{selected.number} {selected.title}</h2><div className="unit-meta"><span>Halaman {selected.start_page} - {selected.end_page}</span><span>{selected.level === "CHAPTER" ? "Bab" : selected.level === "SUBCHAPTER" ? "Sub Bab" : selected.level === "SUBSUBCHAPTER" ? "Sub Sub Bab" : "Bagian Awal"}</span></div>{selected.content ? <p className="source-preview">{selected.content}</p> : <div className="notice"><strong>Preview teks belum tersedia.</strong><p>Simpan struktur terlebih dahulu agar sistem membangun preview dari halaman {selected.start_page} sampai {selected.end_page}. Setelah itu kamu bisa review dan membuat draft revisi dari bagian ini.</p></div>}</div><div><label className="field"><span>Fokus review</span><textarea value={goal} onChange={(e) => setGoal(e.target.value)} /></label><button className="primary" onClick={() => startReview.mutate()} disabled={!selected.content || startReview.isPending || reviewJob.data?.status === "RUNNING"}>{startReview.isPending ? "Menjalankan review..." : reviewJob.data?.status === "RUNNING" ? `Menjalankan review ${reviewJob.data.progress_percent}%` : "Jalankan Review"}</button>{reviewJob.data && ["QUEUED", "RUNNING"].includes(reviewJob.data.status) && <div className="review-progress-card"><div className="review-progress-head"><strong>{reviewJob.data.progress_percent}%</strong><span>{reviewJob.data.progress_message}</span></div><div className="review-progress-bar"><div className="review-progress-fill" style={{ width: `${reviewJob.data.progress_percent}%` }} /></div></div>}{startReview.error && <p className="error">{(startReview.error as Error).message}</p>}{reviewJob.data?.status === "FAILED" && <p className="error">Review gagal. Silakan coba lagi.</p>}{reviewResult && <><p className="notice">{String(reviewResult.summary || "Review selesai.")}</p>{Array.isArray(reviewResult.suggestions) && reviewResult.suggestions.map((item, index) => <div className="suggestion" key={index}><strong>{String((item as Record<string, unknown>).issue || `Saran ${index + 1}`)}</strong><p>{String((item as Record<string, unknown>).suggestion || "Tidak ada detail tambahan.")}</p></div>)}<button className="secondary" onClick={() => startDraft.mutate()} disabled={startDraft.isPending || draftJob.data?.status === "RUNNING"}>{startDraft.isPending ? "Menyiapkan draft..." : draftJob.data?.status === "RUNNING" ? `Membuat draft ${draftJob.data.progress_percent}%` : "Buat Draft .tex"}</button></>}{draftJob.data && ["QUEUED", "RUNNING"].includes(draftJob.data.status) && <div className="draft-progress-card"><div className="review-progress-head"><strong>{draftJob.data.progress_percent}%</strong><span>{draftJob.data.progress_message}</span></div><div className="review-progress-bar"><div className="review-progress-fill" style={{ width: `${draftJob.data.progress_percent}%` }} /></div></div>}{draftNotice && <p className="notice">{draftNotice}</p>}{startDraft.error && <p className="error">{(startDraft.error as Error).message}</p>}{!selected.content && <p className="notice">Bagian baru yang belum disimpan belum bisa direview.</p>}</div></section>}</Page>;
}

function References({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const refs = useQuery({ queryKey: ["references", projectId], queryFn: () => api.references(projectId) });
  const citations = useQuery({ queryKey: ["citations", projectId], queryFn: () => api.citations(projectId) });
  const workspaces = useQuery({ queryKey: ["workspaces", projectId], queryFn: () => api.workspaces(projectId) });
  const [pasted, setPasted] = useState("");
  const [referenceFormat, setReferenceFormat] = useState("ieee");
  const [previewEntries, setPreviewEntries] = useState<ReferencePreviewEntry[]>([]);
  const [previewCount, setPreviewCount] = useState(0);
  const [editingReference, setEditingReference] = useState<ReferenceRecord | null>(null);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState("");
  const [bibContent, setBibContent] = useState("");
  const [referenceForm, setReferenceForm] = useState({ citation_key: "", authors: "", title: "", year: "", doi: "", raw_reference: "" });

  useEffect(() => {
    if (!selectedWorkspaceId && workspaces.data?.length) setSelectedWorkspaceId(workspaces.data[0].id);
  }, [selectedWorkspaceId, workspaces.data]);

  const preview = useMutation({ mutationFn: () => api.previewReferences(projectId, pasted, referenceFormat), onSuccess: (data) => { setPreviewEntries(data.entries); setPreviewCount(data.count); } });
  const paste = useMutation({ mutationFn: () => api.pasteReferences(projectId, pasted, referenceFormat), onSuccess: () => { setPasted(""); setPreviewEntries([]); setPreviewCount(0); queryClient.invalidateQueries({ queryKey: ["references", projectId] }); } });
  const upload = useMutation({ mutationFn: (file: File) => api.uploadReferences(projectId, file, referenceFormat), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["references", projectId] }) });
  const updateReference = useMutation({ mutationFn: () => api.updateReference(projectId, editingReference!.id, referenceForm), onSuccess: () => { setEditingReference(null); queryClient.invalidateQueries({ queryKey: ["references", projectId] }); queryClient.invalidateQueries({ queryKey: ["citations", projectId] }); } });
  const removeReference = useMutation({ mutationFn: (referenceId: string) => api.deleteReference(projectId, referenceId), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["references", projectId] }); queryClient.invalidateQueries({ queryKey: ["citations", projectId] }); } });
  const map = useMutation({ mutationFn: () => api.mapCitations(projectId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["citations", projectId] }) });
  const buildBib = useMutation({ mutationFn: () => api.exportReferencesBib(projectId), onSuccess: (data) => setBibContent(data.content) });
  const insertBib = useMutation({ mutationFn: () => api.insertReferencesBib(projectId, selectedWorkspaceId), onSuccess: () => queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, selectedWorkspaceId] }) });

  const clearPreview = () => { setPreviewEntries([]); setPreviewCount(0); };
  const openEditReference = (reference: ReferenceRecord) => {
    setEditingReference(reference);
    setReferenceForm({ citation_key: reference.citation_key, authors: reference.authors, title: reference.title, year: reference.year, doi: reference.doi || "", raw_reference: reference.raw_reference });
  };

  return <Page title="References & Citation Map" kicker="EVIDENCE LIBRARY"><div className="split"><section className="panel"><h2>Masukkan daftar pustaka</h2><p className="section-copy">Pilih dulu format referensi. Untuk IEEE, sistem akan memecah daftar pustaka berdasarkan marker seperti [1], [2], [3], lalu menampilkan preview jumlah sitasi yang terdeteksi.</p><label className="field"><span>Format referensi</span><select value={referenceFormat} onChange={(event) => setReferenceFormat(event.target.value)}><option value="ieee">IEEE</option><option value="bibtex">BibTeX</option><option value="auto">Teks biasa / auto</option></select></label><input type="file" accept=".bib,.txt" onChange={(e) => e.target.files?.[0] && upload.mutate(e.target.files[0])} /><textarea className="large-input" placeholder="Paste daftar pustaka di sini..." value={pasted} onChange={(e) => setPasted(e.target.value)} /><div className="reference-actions"><button className="secondary" disabled={!pasted.trim() || preview.isPending} onClick={() => preview.mutate()}>{preview.isPending ? "Membaca sitasi..." : "Preview Sitasi"}</button><button className="primary" disabled={!pasted.trim() || paste.isPending} onClick={() => paste.mutate()}>{paste.isPending ? "Menyimpan..." : "Import Paste"}</button></div>{preview.error && <p className="error">{(preview.error as Error).message}</p>}{paste.error && <p className="error">{(paste.error as Error).message}</p>}{upload.error && <p className="error">{(upload.error as Error).message}</p>}{previewEntries.length > 0 && <div className="reference-preview-panel"><div className="panel-title"><div><h2>Preview hasil split</h2><p>Terdeteksi {previewCount} sitasi. Cek dulu apakah jumlahnya sudah masuk akal sebelum import.</p></div><button className="secondary" onClick={clearPreview}>Batalkan Preview</button></div><div className="reference-preview-list">{previewEntries.map((entry, index) => <article key={`${entry.citation_key}-${index}`}><code>{entry.raw_reference.match(/^\[\d+\]/)?.[0] || entry.citation_key}</code><strong>{entry.authors || "Penulis belum terbaca"}</strong><p>{entry.title}</p><small>{entry.year || "Tahun belum terbaca"}{entry.doi ? ` | DOI ${entry.doi}` : ""}</small></article>)}</div></div>}</section><section className="panel"><div className="panel-title"><h2>{refs.data?.length || 0} referensi</h2><button className="secondary" onClick={() => map.mutate()}>{map.isPending ? "Memetakan..." : "Petakan Sitasi"}</button></div><div className="reference-actions"><button className="secondary" onClick={() => buildBib.mutate()} disabled={buildBib.isPending || !refs.data?.length}>{buildBib.isPending ? "Membuat references.bib..." : "Buat references.bib"}</button><select value={selectedWorkspaceId} onChange={(event) => setSelectedWorkspaceId(event.target.value)}><option value="">Pilih workspace...</option>{workspaces.data?.map((workspace) => <option key={workspace.id} value={workspace.id}>{workspace.name}</option>)}</select><button className="primary" onClick={() => insertBib.mutate()} disabled={!selectedWorkspaceId || insertBib.isPending || !refs.data?.length}>{insertBib.isPending ? "Mengirim ke workspace..." : "Masukkan ke Workspace"}</button></div>{buildBib.error && <p className="error">{(buildBib.error as Error).message}</p>}{insertBib.error && <p className="error">{(insertBib.error as Error).message}</p>}{insertBib.isSuccess && <p className="notice">references.bib sudah masuk ke workspace. Langkah berikutnya: buka LaTeX Workspace untuk mengecek atau compile.</p>}{bibContent && <textarea className="code-input" value={bibContent} readOnly />}<div className="reference-list">{refs.data?.map((ref) => <article key={ref.id}><div className="reference-row-top"><div><code>{ref.raw_reference.match(/^\[\d+\]/)?.[0] || ref.citation_key}</code><strong>{ref.authors} {ref.year && `(${ref.year})`}</strong><p>{ref.title}</p>{ref.doi && <small>DOI: {ref.doi}</small>}</div><div className="reference-inline-actions"><button className="secondary" onClick={() => openEditReference(ref)}>Edit</button><button className="danger-button" disabled={removeReference.isPending} onClick={() => removeReference.mutate(ref.id)}>{removeReference.isPending ? "Menghapus..." : "Hapus"}</button></div></div></article>)}</div></section></div><section className="panel"><h2>Citation Map</h2><div className="citation-table">{citations.data?.map((item) => <article key={item.id}><span className={`status status-${item.status.toLowerCase()}`}>{item.status}</span><strong>{item.marker}</strong><span>{item.unit} ? halaman {item.page_number}</span><p>{item.reference?.citation_key || "Belum memiliki pasangan referensi"}</p></article>)}</div></section>{editingReference && <div className="modal"><div className="modal-card reference-modal"><h2>Edit Referensi</h2><label className="field"><span>Citation key</span><input value={referenceForm.citation_key} onChange={(e) => setReferenceForm((current) => ({ ...current, citation_key: e.target.value }))} /></label><label className="field"><span>Penulis</span><input value={referenceForm.authors} onChange={(e) => setReferenceForm((current) => ({ ...current, authors: e.target.value }))} /></label><label className="field"><span>Judul</span><input value={referenceForm.title} onChange={(e) => setReferenceForm((current) => ({ ...current, title: e.target.value }))} /></label><div className="reference-modal-grid"><label className="field"><span>Tahun</span><input value={referenceForm.year} onChange={(e) => setReferenceForm((current) => ({ ...current, year: e.target.value }))} /></label><label className="field"><span>DOI</span><input value={referenceForm.doi} onChange={(e) => setReferenceForm((current) => ({ ...current, doi: e.target.value }))} /></label></div><label className="field"><span>Raw reference</span><textarea className="reference-raw-input" value={referenceForm.raw_reference} onChange={(e) => setReferenceForm((current) => ({ ...current, raw_reference: e.target.value }))} /></label>{updateReference.error && <p className="error">{(updateReference.error as Error).message}</p>}<div><button className="secondary" onClick={() => setEditingReference(null)}>Batal</button><button className="primary" disabled={updateReference.isPending || !referenceForm.citation_key.trim() || !referenceForm.raw_reference.trim()} onClick={() => updateReference.mutate()}>{updateReference.isPending ? "Menyimpan..." : "Simpan Perubahan"}</button></div></div></div>}</Page>;
}

function Drafts({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();
  const statusStorageKey = `draft-status:${projectId}`;
  const drafts = useQuery({ queryKey: ["drafts", projectId], queryFn: () => api.drafts(projectId) });
  const workspaces = useQuery({ queryKey: ["workspaces", projectId], queryFn: () => api.workspaces(projectId) });
  const [activeDraftId, setActiveDraftId] = useState("");
  const [editing, setEditing] = useState<Draft | null>(null);
  const [content, setContent] = useState("");
  const [summary, setSummary] = useState("");
  const [workspaceByDraft, setWorkspaceByDraft] = useState<Record<string, string>>({});
  const [selectedDraftIds, setSelectedDraftIds] = useState<string[]>([]);
  const [bulkWorkspaceId, setBulkWorkspaceId] = useState("");
  const [sentMessage, setSentMessage] = useState("");
  const [draftStatuses, setDraftStatuses] = useState<Record<string, "draft" | "ready" | "sent">>(() => {
    try {
      return JSON.parse(localStorage.getItem(statusStorageKey) || "{}");
    } catch {
      return {};
    }
  });

  useEffect(() => {
    if (!activeDraftId && drafts.data?.length) setActiveDraftId(drafts.data[0].id);
  }, [activeDraftId, drafts.data]);

  useEffect(() => {
    if (!workspaces.data?.length) return;
    setBulkWorkspaceId((current) => current || workspaces.data[0].id);
    setWorkspaceByDraft((current) => {
      const next = { ...current };
      for (const draft of drafts.data || []) {
        if (!next[draft.id]) next[draft.id] = workspaces.data[0].id;
      }
      return next;
    });
  }, [drafts.data, workspaces.data]);

  useEffect(() => {
    localStorage.setItem(statusStorageKey, JSON.stringify(draftStatuses));
  }, [draftStatuses, statusStorageKey]);

  useEffect(() => {
    const existingIds = new Set((drafts.data || []).map((draft) => draft.id));
    setSelectedDraftIds((current) => current.filter((id) => existingIds.has(id)));
  }, [drafts.data]);

  const activeDraft = drafts.data?.find((draft) => draft.id === activeDraftId) || drafts.data?.[0] || null;
  const versions = useQuery({ queryKey: ["draft-versions", projectId, activeDraftId], queryFn: () => api.draftVersions(projectId, activeDraftId), enabled: Boolean(activeDraftId) });
  const readyCount = (drafts.data || []).filter((draft) => draftStatuses[draft.id] === "ready").length;
  const sentCount = (drafts.data || []).filter((draft) => draftStatuses[draft.id] === "sent").length;

  const save = useMutation({
    mutationFn: () => api.saveDraft(projectId, editing!.id, content, summary),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["drafts", projectId] });
      queryClient.invalidateQueries({ queryKey: ["draft-versions", projectId, editing?.id] });
      if (editing) setDraftStatus(editing.id, "ready");
      setEditing(null);
    }
  });
  const restore = useMutation({ mutationFn: ({ draftId, versionId }: { draftId: string; versionId: string }) => api.restoreDraftVersion(projectId, draftId, versionId), onSuccess: () => { queryClient.invalidateQueries({ queryKey: ["drafts", projectId] }); queryClient.invalidateQueries({ queryKey: ["draft-versions", projectId, activeDraftId] }); } });
  const insert = useMutation({
    mutationFn: ({ draftId, workspaceId }: { draftId: string; workspaceId: string }) => {
      const targetWorkspace = workspaces.data?.find((item) => item.id === workspaceId);
      if (!targetWorkspace) throw new Error("Workspace tujuan belum dipilih.");
      return api.insertDraft(projectId, workspaceId, draftId, targetWorkspace.main_document);
    },
    onSuccess: (data, variables) => {
      setDraftStatus(variables.draftId, "sent");
      setSentMessage(`Draft disimpan sebagai file ${data.draft_file}. Jika ingin muncul di PDF, panggil manual dari ${data.path} dengan \\input{...}.`);
      queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, variables.workspaceId] });
    }
  });
  const bulkInsert = useMutation({
    mutationFn: async () => {
      const targetWorkspace = workspaces.data?.find((item) => item.id === bulkWorkspaceId);
      if (!targetWorkspace) throw new Error("Workspace tujuan belum dipilih.");
      for (const draftId of selectedDraftIds) {
        await api.insertDraft(projectId, bulkWorkspaceId, draftId, targetWorkspace.main_document);
      }
      return { count: selectedDraftIds.length, workspaceId: bulkWorkspaceId };
    },
    onSuccess: (result) => {
      setDraftStatuses((current) => {
        const next = { ...current };
        for (const id of selectedDraftIds) next[id] = "sent";
        return next;
      });
      setSentMessage(`${result.count} draft berhasil disimpan ke folder drafts. Silakan buka LaTeX Workspace lalu panggil file yang diperlukan dengan \\input{...}.`);
      setSelectedDraftIds([]);
      queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, result.workspaceId] });
    }
  });
  const removeDraft = useMutation({ mutationFn: (draftId: string) => api.deleteDraft(projectId, draftId), onSuccess: (_data, removedId) => { queryClient.invalidateQueries({ queryKey: ["drafts", projectId] }); if (activeDraftId === removedId) setActiveDraftId(""); setSelectedDraftIds((current) => current.filter((id) => id !== removedId)); } });

  function setDraftStatus(draftId: string, status: "draft" | "ready" | "sent") {
    setDraftStatuses((current) => ({ ...current, [draftId]: status }));
  }

  function toggleSelected(draftId: string) {
    setSelectedDraftIds((current) => current.includes(draftId) ? current.filter((id) => id !== draftId) : [...current, draftId]);
  }

  function selectReadyDrafts() {
    setSelectedDraftIds((drafts.data || []).filter((draft) => draftStatuses[draft.id] === "ready").map((draft) => draft.id));
  }

  function selectAllDrafts() {
    setSelectedDraftIds((drafts.data || []).map((draft) => draft.id));
  }

  const selectedCount = selectedDraftIds.length;

  return <Page title="Draft Manager" kicker="CONTROLLED REVISIONS"><section className="panel draft-intro"><div><h2>Draft hasil review terkumpul di sini</h2><p>Edit draft sampai rapi, tandai siap kirim, pilih beberapa draft, lalu kirim massal ke workspace LaTeX.</p></div><div className="draft-intro-badges"><span>{drafts.data?.length || 0} draft</span><span>{readyCount} siap kirim</span><span>{sentCount} terkirim</span></div></section>{!drafts.data?.length ? <section className="panel empty-state-panel"><h2>Belum ada draft revisi</h2><p>Kembali ke halaman PDF Review, pilih bagian dokumen, jalankan review, lalu klik Buat Draft .tex. Setelah itu hasilnya akan muncul di sini.</p></section> : <><section className="panel draft-bulk-panel"><div><strong>{selectedCount} draft dipilih</strong><p>Pilih draft yang sudah final, lalu kirim sekaligus ke workspace tujuan.</p></div><div className="draft-bulk-controls"><button className="secondary" onClick={selectReadyDrafts} disabled={!readyCount}>Pilih Siap Kirim</button><button className="secondary" onClick={selectAllDrafts}>Pilih Semua</button><button className="secondary" onClick={() => setSelectedDraftIds([])} disabled={!selectedCount}>Kosongkan</button><select value={bulkWorkspaceId} onChange={(event) => setBulkWorkspaceId(event.target.value)}><option value="">Pilih workspace...</option>{workspaces.data?.map((space) => <option key={space.id} value={space.id}>{space.name}</option>)}</select><button className="primary" disabled={!selectedCount || !bulkWorkspaceId || bulkInsert.isPending} onClick={() => bulkInsert.mutate()}>{bulkInsert.isPending ? "Mengirim draft..." : `Kirim ${selectedCount} Draft`}</button></div>{sentMessage && <p className="notice">{sentMessage}</p>}{bulkInsert.error && <p className="error">{(bulkInsert.error as Error).message}</p>}</section><div className="draft-manager-layout"><section className="panel draft-list-panel"><div className="panel-title"><div><h2>Daftar draft</h2><p>Pilih draft, ubah status, atau buka detailnya.</p></div></div><div className="draft-stack">{drafts.data?.map((draft, index) => { const status = draftStatuses[draft.id] || "draft"; return <article className={`draft-list-card ${activeDraftId === draft.id ? "draft-list-card-active" : ""} ${selectedDraftIds.includes(draft.id) ? "draft-list-card-selected" : ""}`} key={draft.id}><div className="draft-card-head"><label className="draft-check"><input type="checkbox" checked={selectedDraftIds.includes(draft.id)} onChange={() => toggleSelected(draft.id)} /><span>Pilih</span></label><span className={`draft-status draft-status-${status}`}>{status === "ready" ? "Siap kirim" : status === "sent" ? "Terkirim" : "Draft"}</span></div><button className="draft-select" onClick={() => setActiveDraftId(draft.id)}><div><span className="eyebrow">DRAFT {String(index + 1).padStart(2, "0")}</span><h3>{draft.title}</h3><p>{draft.summary || "Belum ada ringkasan. Draft ini siap kamu rapikan manual."}</p></div><div className="draft-list-meta"><span>Versi {draft.current_version}</span><small>{draft.content.length} karakter</small></div></button><div className="draft-inline-actions"><button className="secondary" onClick={() => navigator.clipboard.writeText(draft.content)}>Copy .tex</button><button className="secondary" onClick={() => setDraftStatus(draft.id, status === "ready" ? "draft" : "ready")}>{status === "ready" ? "Batal Siap" : "Siap Kirim"}</button><button className="primary" onClick={() => { setEditing(draft); setContent(draft.content); setSummary(draft.summary || ""); }}>Edit</button><button className="danger-button" disabled={removeDraft.isPending} onClick={() => removeDraft.mutate(draft.id)}>{removeDraft.isPending ? "Menghapus..." : "Hapus"}</button></div></article>; })}</div>{removeDraft.error && <p className="error">{(removeDraft.error as Error).message}</p>}</section><section className="panel draft-detail-panel">{activeDraft ? <><div className="panel-title"><div><span className="eyebrow">VERSI TERBARU</span><h2>{activeDraft.title}</h2><p>{activeDraft.summary || "Belum ada ringkasan untuk draft ini."}</p></div><div className="draft-detail-actions"><button className="secondary" onClick={() => toggleSelected(activeDraft.id)}>{selectedDraftIds.includes(activeDraft.id) ? "Batal Pilih" : "Pilih Draft"}</button><button className="secondary" onClick={() => setDraftStatus(activeDraft.id, "ready")}>Tandai Siap</button><button className="primary" onClick={() => { setEditing(activeDraft); setContent(activeDraft.content); setSummary(activeDraft.summary || ""); }}>Edit versi terbaru</button></div></div><div className="draft-workspace-handoff"><div><strong>Kirim draft ini saja</strong><p>Untuk banyak draft, gunakan panel pilihan massal di atas.</p></div><div className="draft-handoff-controls"><select value={workspaceByDraft[activeDraft.id] || ""} onChange={(event) => setWorkspaceByDraft((current) => ({ ...current, [activeDraft.id]: event.target.value }))}><option value="">Pilih workspace...</option>{workspaces.data?.map((space) => <option key={space.id} value={space.id}>{space.name}</option>)}</select><button className="primary" disabled={!workspaceByDraft[activeDraft.id] || insert.isPending} onClick={() => insert.mutate({ draftId: activeDraft.id, workspaceId: workspaceByDraft[activeDraft.id] })}>{insert.isPending ? "Mengirim..." : "Kirim ke Workspace"}</button></div></div>{insert.isSuccess && <p className="notice">Draft tidak ditempel mentah ke main.tex. Sistem membuat file .tex terpisah lalu menautkannya ke file penggabung.</p>}{insert.error && <p className="error">{(insert.error as Error).message}</p>}<pre className="draft-preview-full">{activeDraft.content}</pre><section className="draft-versions-panel"><div className="panel-title"><div><h2>Riwayat versi</h2><p>Kalau versi terbaru kurang pas, kamu bisa lihat versi sebelumnya lalu pulihkan.</p></div></div>{versions.isLoading && <p className="notice">Memuat riwayat versi...</p>}{versions.data?.map((version: DraftVersion) => <article className="draft-version-row" key={version.id}><div><strong>Versi {version.version}</strong><small>{version.source} | {new Date(version.created_at).toLocaleString("id-ID")}</small><p>{version.summary || "Tidak ada ringkasan versi."}</p></div><div className="draft-version-actions"><button className="secondary" onClick={() => navigator.clipboard.writeText(version.content)}>Copy</button><button className="secondary" disabled={restore.isPending || version.version === activeDraft.current_version} onClick={() => restore.mutate({ draftId: activeDraft.id, versionId: version.id })}>{version.version === activeDraft.current_version ? "Versi aktif" : restore.isPending ? "Memulihkan..." : "Pulihkan"}</button></div></article>)}</section></> : <p className="notice">Pilih salah satu draft untuk melihat detailnya.</p>}</section></div></>}{editing && <div className="modal"><div className="modal-card"><h2>{editing.title}</h2><label className="field"><span>Ringkasan revisi</span><input value={summary} onChange={(e) => setSummary(e.target.value)} placeholder="Contoh: Sudah dirapikan dan sitasi diperjelas." /></label><textarea className="code-input" value={content} onChange={(e) => setContent(e.target.value)} /><div><button className="secondary" onClick={() => setEditing(null)}>Batal</button><button className="primary" onClick={() => save.mutate()}>{save.isPending ? "Menyimpan..." : "Simpan versi baru & siap kirim"}</button></div></div></div>}</Page>;
}

function WorkspacePage({ projectId, user }: { projectId: string; user: User }) {
  const queryClient = useQueryClient();
  const workspaces = useQuery({ queryKey: ["workspaces", projectId], queryFn: () => api.workspaces(projectId) });
  const [workspaceId, setWorkspaceId] = useState("");
  const [newName, setNewName] = useState("");
  const [showBuilder, setShowBuilder] = useState(true);
  const [snippetPreview, setSnippetPreview] = useState<Record<string, string> | null>(null);
  const [scaffold, setScaffold] = useState<WorkspaceScaffold>({
    name: "Workspace Skripsi",
    main_document: "main.tex",
    paper_size: "a4paper",
    font_size: "12pt",
    line_spacing: "1.5",
    margin_top_cm: 4,
    margin_right_cm: 3,
    margin_bottom_cm: 3,
    margin_left_cm: 4,
    font_family: "times",
    chapter_style: "default",
    include_cover: true,
    bibliography_style: "numeric",
  });

  useEffect(() => {
    if (!workspaceId && workspaces.data?.length) setWorkspaceId(workspaces.data[0].id);
  }, [workspaceId, workspaces.data]);

  useEffect(() => {
    if ((workspaces.data?.length || 0) > 0) setShowBuilder(false);
  }, [workspaces.data]);

  const create = useMutation({ mutationFn: () => api.createWorkspace(projectId, newName), onSuccess: (space) => { queryClient.invalidateQueries({ queryKey: ["workspaces", projectId] }); setWorkspaceId(space.id); setNewName(""); setShowBuilder(false); } });
  const createAuto = useMutation({ mutationFn: () => api.createAutoWorkspace(projectId, scaffold), onSuccess: (space) => { queryClient.invalidateQueries({ queryKey: ["workspaces", projectId] }); setWorkspaceId(space.id); setScaffold((current) => ({ ...current, name: space.name })); setShowBuilder(false); } });
  const makeSnippet = useMutation({ mutationFn: () => api.workspaceSnippet(projectId, scaffold), onSuccess: (data) => setSnippetPreview(data.files) });
  const selected = workspaces.data?.find((item) => item.id === workspaceId);

  const setField = <K extends keyof WorkspaceScaffold>(key: K, value: WorkspaceScaffold[K]) => {
    setScaffold((current) => ({ ...current, [key]: value }));
  };

  return <Page title="LaTeX Workspace" kicker="WRITE TOGETHER" hideHeading className="workspace-page">{showBuilder && <section className="panel workspace-builder-panel"><div className="panel-title"><div><h2>Bangun workspace sesuai layout yang kamu mau</h2><p>Pilih cara membuat workspace.</p></div></div><div className="workspace-builder-grid"><label className="field"><span>Nama workspace</span><input value={scaffold.name} onChange={(e) => setField("name", e.target.value)} /></label><label className="field"><span>Main document</span><input value={scaffold.main_document} onChange={(e) => setField("main_document", e.target.value)} /></label><label className="field"><span>Kertas</span><select value={scaffold.paper_size} onChange={(e) => setField("paper_size", e.target.value)}><option value="a4paper">A4</option><option value="letterpaper">Letter</option></select></label><label className="field"><span>Ukuran font</span><select value={scaffold.font_size} onChange={(e) => setField("font_size", e.target.value)}><option value="12pt">12 pt</option><option value="11pt">11 pt</option><option value="10pt">10 pt</option></select></label><label className="field"><span>Spasi</span><select value={scaffold.line_spacing} onChange={(e) => setField("line_spacing", e.target.value)}><option value="2">2.0</option><option value="1.5">1.5</option><option value="1.15">1.15</option><option value="1">1.0</option></select></label><label className="field"><span>Font family</span><select value={scaffold.font_family} onChange={(e) => setField("font_family", e.target.value)}><option value="times">Times</option><option value="palatino">Palatino</option><option value="helvetica">Helvetica</option></select></label><label className="field"><span>Style bab</span><select value={scaffold.chapter_style} onChange={(e) => setField("chapter_style", e.target.value)}><option value="default">Default</option><option value="simple">Simple</option><option value="centered">Centered</option></select></label><label className="field"><span>Bibliography</span><select value={scaffold.bibliography_style} onChange={(e) => setField("bibliography_style", e.target.value)}><option value="numeric">Numeric</option><option value="ieee">IEEE</option></select></label><label className="field"><span>Margin atas (cm)</span><input type="number" step="0.1" value={scaffold.margin_top_cm} onChange={(e) => setField("margin_top_cm", Number(e.target.value))} /></label><label className="field"><span>Margin kanan (cm)</span><input type="number" step="0.1" value={scaffold.margin_right_cm} onChange={(e) => setField("margin_right_cm", Number(e.target.value))} /></label><label className="field"><span>Margin bawah (cm)</span><input type="number" step="0.1" value={scaffold.margin_bottom_cm} onChange={(e) => setField("margin_bottom_cm", Number(e.target.value))} /></label><label className="field"><span>Margin kiri (cm)</span><input type="number" step="0.1" value={scaffold.margin_left_cm} onChange={(e) => setField("margin_left_cm", Number(e.target.value))} /></label><label className="field workspace-checkbox"><span>Cover awal</span><input type="checkbox" checked={scaffold.include_cover} onChange={(e) => setField("include_cover", e.target.checked)} /></label></div><div className="workspace-builder-actions"><button className="primary" disabled={createAuto.isPending || !scaffold.name.trim()} onClick={() => createAuto.mutate()}>{createAuto.isPending ? "Membuat workspace otomatis..." : "Buat Workspace Otomatis"}</button><button className="secondary" disabled={makeSnippet.isPending} onClick={() => makeSnippet.mutate()}>{makeSnippet.isPending ? "Menyiapkan snippet..." : "Tampilkan Kode LaTeX yang Harus Dimasukkan"}</button><button className="text-button" onClick={() => setShowBuilder(false)}>Tutup</button></div>{createAuto.error && <p className="error">{(createAuto.error as Error).message}</p>}{makeSnippet.error && <p className="error">{(makeSnippet.error as Error).message}</p>}{createAuto.isSuccess && <p className="notice">Workspace otomatis berhasil dibuat.</p>}{snippetPreview && <div className="workspace-snippet-preview"><p className="notice">Salin potongan yang kamu butuhkan.</p><div className="snippet-grid">{Object.entries(snippetPreview).map(([name, content]) => <label className="field" key={name}><span>{name}</span><textarea className="snippet-input" readOnly value={content} /></label>)}</div></div>}</section>}<section className="workspace-toolbar"><div className="workspace-toolbar-left">{!showBuilder && <button className="secondary" onClick={() => setShowBuilder(true)}>Atur Layout Lagi</button>}<select value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)}><option value="">Pilih workspace...</option>{workspaces.data?.map((space) => <option key={space.id} value={space.id}>{space.name}</option>)}</select></div><div className="workspace-toolbar-right"><input placeholder="Nama workspace blank baru" value={newName} onChange={(e) => setNewName(e.target.value)} /><button className="primary" disabled={!newName.trim()} onClick={() => create.mutate()}>Buat Blank Project</button></div></section>{selected ? <WorkspaceEditor projectId={projectId} workspace={selected} user={user} /> : <section className="empty-state"><h2>Pilih atau buat workspace</h2><p>Explorer, editor kolaboratif, dan PDF preview akan tampil di sini.</p></section>}</Page>;
}

type ExplorerNode = {
  name: string;
  path: string;
  kind: "file" | "folder";
  editable: boolean;
  children: ExplorerNode[];
};

function buildExplorerTree(items: Array<{ path: string; kind: "file" | "folder"; editable: boolean }>): ExplorerNode {
  const root: ExplorerNode = { name: "", path: "", kind: "folder", editable: false, children: [] };
  const folderMap = new Map<string, ExplorerNode>([["", root]]);

  const ensureFolder = (folderPath: string) => {
    if (folderMap.has(folderPath)) return folderMap.get(folderPath)!;
    const segments = folderPath.split("/");
    const name = segments[segments.length - 1];
    const parentPath = segments.slice(0, -1).join("/");
    const parent = ensureFolder(parentPath);
    const node: ExplorerNode = { name, path: folderPath, kind: "folder", editable: false, children: [] };
    parent.children.push(node);
    folderMap.set(folderPath, node);
    return node;
  };

  for (const item of items.filter((entry) => entry.kind === "folder")) ensureFolder(item.path);
  for (const item of items.filter((entry) => entry.kind === "file")) {
    const segments = item.path.split("/");
    const name = segments[segments.length - 1];
    const parentPath = segments.slice(0, -1).join("/");
    const parent = ensureFolder(parentPath);
    parent.children.push({ name, path: item.path, kind: "file", editable: item.editable, children: [] });
  }

  const sortNode = (node: ExplorerNode) => {
    node.children.sort((a, b) => {
      if (a.kind !== b.kind) return a.kind === "folder" ? -1 : 1;
      return a.name.localeCompare(b.name, "id", { sensitivity: "base" });
    });
    node.children.filter((child) => child.kind === "folder").forEach(sortNode);
  };

  sortNode(root);
  return root;
}

function WorkspaceEditor({ projectId, workspace, user }: { projectId: string; workspace: Workspace; user: User }) {
  const queryClient = useQueryClient();
  const files = useQuery({ queryKey: ["workspace-files", projectId, workspace.id], queryFn: () => api.workspaceFiles(projectId, workspace.id) });
  const [path, setPath] = useState("");
  const [fileNotice, setFileNotice] = useState("");
  const [menuTarget, setMenuTarget] = useState<{ path: string; kind: "file" | "folder" } | null>(null);
  const [pendingCreate, setPendingCreate] = useState<{ kind: "file" | "folder"; parentPath: string } | null>(null);
  const [pendingRename, setPendingRename] = useState<{ path: string; kind: "file" | "folder"; parentPath: string; currentName: string } | null>(null);
  const [pendingName, setPendingName] = useState("");
  const [uploadFolder, setUploadFolder] = useState<string | null>(null);
  const [expandedFolders, setExpandedFolders] = useState<Set<string>>(() => new Set(["__root__"]));
  const uploadInputRef = useRef<HTMLInputElement | null>(null);
  const selectedItem = files.data?.files.find((item) => item.path === path);
  const file = useQuery({ queryKey: ["workspace-file", projectId, workspace.id, path], queryFn: () => api.readFile(projectId, workspace.id, path), enabled: Boolean(path) && selectedItem?.kind === "file" && selectedItem.editable });
  const [content, setContent] = useState("");
  const serverContentRef = useRef("");
  const autosaveTimerRef = useRef<number | null>(null);
  const hydratedPathRef = useRef("");
  const [jobId, setJobId] = useState(localStorage.getItem(compileJobKey(projectId, workspace.id)) || "");
  const [dismissedCompileErrorKey, setDismissedCompileErrorKey] = useState("");
  const job = useQuery({ queryKey: ["job", jobId], queryFn: () => api.job(jobId), enabled: Boolean(jobId), refetchInterval: (query) => ["SUCCEEDED", "FAILED"].includes(query.state.data?.status || "") ? false : 1500 });
  const rootTree = buildExplorerTree(files.data?.files || []);

  useEffect(() => {
    if (!path || !file.data) return;
    serverContentRef.current = file.data.content;
    const cacheKey = workspaceDraftKey(projectId, workspace.id, path);
    const cachedDraft = localStorage.getItem(cacheKey);
    const shouldIgnoreBrokenBlankDraft = cachedDraft === "" && file.data.content.trim().length > 0;
    if (shouldIgnoreBrokenBlankDraft) localStorage.removeItem(cacheKey);
    setContent(shouldIgnoreBrokenBlankDraft ? file.data.content : (cachedDraft ?? file.data.content));
    hydratedPathRef.current = path;
  }, [file.data, path, projectId, workspace.id]);

  useEffect(() => {
    if (!path) {
      hydratedPathRef.current = "";
      return;
    }
    if (hydratedPathRef.current !== path) setContent("");
  }, [path]);

  useEffect(() => () => {
    if (autosaveTimerRef.current) window.clearTimeout(autosaveTimerRef.current);
  }, []);

  useEffect(() => {
    const items = files.data?.files.filter((item) => item.kind === "file") || [];
    if (!items.length) {
      if (path) setPath("");
      return;
    }
    const preferred = items.find((item) => item.path === workspace.main_document)?.path || items[0].path;
    const exists = items.some((item) => item.path === path);
    if (!path || !exists) setPath(preferred);
  }, [files.data, path, workspace.main_document]);

  useEffect(() => {
    const closeMenu = () => setMenuTarget(null);
    window.addEventListener("mousedown", closeMenu);
    return () => window.removeEventListener("mousedown", closeMenu);
  }, []);

  const save = useMutation({
    mutationFn: ({ targetPath, nextContent, autosave = false }: { targetPath: string; nextContent: string; autosave?: boolean }) => api.saveFile(projectId, workspace.id, targetPath, nextContent),
    onSuccess: (_data, variables) => {
      serverContentRef.current = variables.nextContent;
      localStorage.removeItem(workspaceDraftKey(projectId, workspace.id, variables.targetPath));
      setFileNotice(`${variables.autosave ? "Tersimpan otomatis" : "Tersimpan"}: ${variables.targetPath}`);
    }
  });
  const createFolder = useMutation({ mutationFn: (targetPath: string) => api.createFolder(projectId, workspace.id, targetPath), onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, workspace.id] }); setFileNotice(`Folder dibuat: ${data.path}`); setPendingCreate(null); setPendingName(""); } });
  const createFile = useMutation({ mutationFn: (targetPath: string) => api.createFile(projectId, workspace.id, targetPath, ""), onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, workspace.id] }); setPath(data.path); setFileNotice(`File dibuat: ${data.path}`); setPendingCreate(null); setPendingName(""); } });
  const renameEntry = useMutation({ mutationFn: (payload: { path: string; newName: string }) => api.renameFile(projectId, workspace.id, payload.path, payload.newName), onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, workspace.id] }); queryClient.invalidateQueries({ queryKey: ["workspaces", projectId] }); queryClient.removeQueries({ queryKey: ["workspace-file", projectId, workspace.id, data.old_path] }); if (path === data.old_path) setPath(data.path); else if (path.startsWith(`${data.old_path}/`)) setPath(`${data.path}/${path.slice(data.old_path.length + 1)}`); setFileNotice(`Diubah: ${data.old_path} -> ${data.path}`); setMenuTarget(null); setPendingRename(null); setPendingName(""); } });
  const removeEntry = useMutation({ mutationFn: (targetPath: string) => api.deleteFile(projectId, workspace.id, targetPath), onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, workspace.id] }); queryClient.removeQueries({ queryKey: ["workspace-file", projectId, workspace.id, data.path] }); if (path === data.path || path.startsWith(`${data.path}/`)) setPath(workspace.main_document); setFileNotice(`Dihapus: ${data.path}`); setMenuTarget(null); } });
  const uploadAsset = useMutation({ mutationFn: (payload: { folder: string; file: File }) => { const normalized = payload.folder.trim().replace(/\\/g, "/").replace(/\/$/, ""); const targetPath = normalized ? `${normalized}/${payload.file.name}` : payload.file.name; return api.uploadWorkspaceFile(projectId, workspace.id, targetPath, payload.file); }, onSuccess: (data) => { queryClient.invalidateQueries({ queryKey: ["workspace-files", projectId, workspace.id] }); setFileNotice(`File upload: ${data.path}`); } });
  const compile = useMutation({ mutationFn: () => api.compile(projectId, workspace.id), onSuccess: (data) => { setDismissedCompileErrorKey(""); setJobId(data.job_id); localStorage.setItem(compileJobKey(projectId, workspace.id), data.job_id); } });
  const compileFile = useMutation({ mutationFn: (targetPath: string) => api.compileFile(projectId, workspace.id, targetPath), onSuccess: (data) => { setDismissedCompileErrorKey(""); setJobId(data.job_id); localStorage.setItem(compileJobKey(projectId, workspace.id), data.job_id); } });

  const preview = typeof job.data?.result.preview_url === "string" ? job.data.result.preview_url : "";
  const downloadUrl = typeof job.data?.result.download_url === "string" ? job.data.result.download_url : "";
  const compileError = typeof job.data?.result.error_summary === "string" ? job.data.result.error_summary : "Compile gagal.";
  const compileErrorLine = typeof job.data?.result.error_line === "number" ? job.data.result.error_line : null;
  const compileErrorContext = typeof job.data?.result.error_context === "string" ? job.data.result.error_context : "";
  const compiledPath = typeof job.data?.result.compiled_path === "string" ? job.data.result.compiled_path : "";
  const compileErrorKey = `${jobId}:${job.data?.status || ""}:${compiledPath}:${compileError}:${compileErrorLine ?? ""}`;
  const showCompileError = ((job.data?.status === "SUCCEEDED" && job.data.result.success === false) || job.data?.status === "FAILED") && dismissedCompileErrorKey !== compileErrorKey;
  const isTexFileSelected = Boolean(path) && selectedItem?.kind === "file" && path.toLowerCase().endsWith(".tex");
  const color = `hsl(${[...user.id].reduce((sum, char) => sum + char.charCodeAt(0), 0) % 360} 65% 45%)`;
  const canDelete = Boolean(path) && path != workspace.main_document;
  const isDirty = Boolean(path) && content !== serverContentRef.current;

  useEffect(() => {
    if (job.data?.status === "RUNNING" || job.data?.status === "QUEUED") setDismissedCompileErrorKey("");
  }, [job.data?.status, jobId]);

  useEffect(() => {
    if (!path || !selectedItem?.editable || hydratedPathRef.current !== path || !file.data) return;
    localStorage.setItem(workspaceDraftKey(projectId, workspace.id, path), content);
    if (autosaveTimerRef.current) window.clearTimeout(autosaveTimerRef.current);
    if (content === serverContentRef.current) return;
    autosaveTimerRef.current = window.setTimeout(() => {
      save.mutate({ targetPath: path, nextContent: content, autosave: true });
    }, 1000);
    return () => {
      if (autosaveTimerRef.current) window.clearTimeout(autosaveTimerRef.current);
    };
  }, [content, file.data, path, projectId, workspace.id, selectedItem?.editable]);

  async function ensureSavedBeforeCompile() {
    if (!path || !selectedItem?.editable || !isDirty) return;
    await save.mutateAsync({ targetPath: path, nextContent: content, autosave: true });
  }

  function toggleFolder(folderPath: string) {
    setExpandedFolders((current) => {
      const next = new Set(current);
      if (next.has(folderPath)) next.delete(folderPath);
      else next.add(folderPath);
      return next;
    });
  }

  function openCreateRow(kind: "file" | "folder", parentPath = "") {
    setMenuTarget(null);
    setPendingRename(null);
    setPendingCreate({ kind, parentPath });
    setPendingName("");
    setExpandedFolders((current) => new Set(current).add(parentPath || "__root__"));
  }

  function buildPendingPath() {
    if (!pendingCreate || !pendingName.trim()) return "";
    return pendingCreate.parentPath ? `${pendingCreate.parentPath}/${pendingName.trim()}` : pendingName.trim();
  }

  function submitPendingCreate() {
    const targetPath = buildPendingPath();
    if (!targetPath) return;
    if (pendingCreate?.kind === "folder") createFolder.mutate(targetPath);
    else createFile.mutate(targetPath);
  }

  function openRenameRow(targetPath: string, kind: "file" | "folder") {
    const segments = targetPath.split("/");
    const currentName = segments[segments.length - 1] || targetPath;
    const parentPath = segments.slice(0, -1).join("/");
    setMenuTarget(null);
    setPendingCreate(null);
    setPendingRename({ path: targetPath, kind, parentPath, currentName });
    setPendingName(currentName);
    setExpandedFolders((current) => new Set(current).add(parentPath || "__root__"));
  }

  function submitPendingRename() {
    if (!pendingRename || !pendingName.trim()) return;
    renameEntry.mutate({ path: pendingRename.path, newName: pendingName.trim() });
  }

  function confirmDelete(targetPath: string, kind: "file" | "folder") {
    const label = kind === "folder" ? "folder" : "file";
    if (!window.confirm(`Hapus ${label} ${targetPath}?`)) return;
    removeEntry.mutate(targetPath);
  }

  function openFolderUpload(folderPath: string) {
    setUploadFolder(folderPath);
    uploadInputRef.current?.click();
    setMenuTarget(null);
  }

  function onUploadSelected(event: React.ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0];
    if (!picked || uploadFolder === null) return;
    uploadAsset.mutate({ folder: uploadFolder, file: picked });
    event.target.value = "";
    setUploadFolder(null);
  }

  function toggleMenu(event: React.MouseEvent, targetPath: string, kind: "file" | "folder") {
    event.preventDefault();
    event.stopPropagation();
    setPendingCreate(null);
    setPendingRename(null);
    setMenuTarget((current) => current?.path === targetPath ? null : { path: targetPath, kind });
  }

  function handleFileContextMenu(event: React.MouseEvent, targetPath: string) {
    event.preventDefault();
    event.stopPropagation();
    setPendingCreate(null);
    setPendingRename(null);
    setMenuTarget({ path: targetPath, kind: "file" });
  }

  function renderChildren(nodes: ExplorerNode[], parentPath: string, depth: number = 1): React.ReactNode {
    const entries: React.ReactNode[] = [];
    if (pendingCreate?.parentPath === parentPath) {
      entries.push(
        <div key={`create-${parentPath || 'root'}`} className="inline-create-row" style={{ marginLeft: `${depth * 14}px` }}>
          <input autoFocus value={pendingName} onChange={(event) => setPendingName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") submitPendingCreate(); if (event.key === "Escape") { setPendingCreate(null); setPendingName(""); } }} placeholder={pendingCreate.kind === "folder" ? "nama-folder" : "nama-file.tex"} />
          <button className="secondary" onClick={submitPendingCreate} disabled={!pendingName.trim() || createFile.isPending || createFolder.isPending}>Buat</button>
          <button className="text-button" onClick={() => { setPendingCreate(null); setPendingName(""); }}>Batal</button>
        </div>
      );
    }
    for (const node of nodes) {
      if (node.kind === "folder") {
        const expanded = expandedFolders.has(node.path);
        entries.push(
          <div key={node.path} className="tree-entry-block">
            <div className="file-tree-folder-row" style={{ paddingLeft: `${depth * 14}px` }}>
              <button className="folder-caret" onClick={() => toggleFolder(node.path)}>{expanded ? "v" : ">"}</button>
              <button className="file-tree-folder" onClick={() => toggleFolder(node.path)}>{node.name}</button>
              <button className="icon-button" onClick={(event) => toggleMenu(event, node.path, "folder")}>...</button>
            </div>
            {menuTarget?.path === node.path && menuTarget.kind === "folder" && <div className="tree-menu-inline" style={{ marginLeft: `${depth * 14 + 22}px` }} onMouseDown={(event) => event.stopPropagation()}><button onClick={() => openRenameRow(node.path, "folder")}>Rename Folder</button><button onClick={() => openCreateRow("file", node.path)}>Tambah File Baru</button><button onClick={() => openCreateRow("folder", node.path)}>Tambah Folder</button><button onClick={() => openFolderUpload(node.path)}>Upload File</button><button className="danger-text" onClick={() => confirmDelete(node.path, "folder")}>Hapus Folder</button></div>}
            {pendingRename?.path === node.path && <div className="inline-create-row" style={{ marginLeft: `${depth * 14 + 22}px` }}><input autoFocus value={pendingName} onChange={(event) => setPendingName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") submitPendingRename(); if (event.key === "Escape") { setPendingRename(null); setPendingName(""); } }} placeholder={pendingRename.kind === "folder" ? "nama-folder-baru" : "nama-file-baru.tex"} /><button className="secondary" onClick={submitPendingRename} disabled={!pendingName.trim() || renameEntry.isPending}>{renameEntry.isPending ? "Menyimpan..." : "Rename"}</button><button className="text-button" onClick={() => { setPendingRename(null); setPendingName(""); }}>Batal</button></div>}
            {expanded && renderChildren(node.children, node.path, depth + 1)}
          </div>
        );
      } else {
        entries.push(
          <div key={node.path} className="tree-entry-block" onContextMenu={(event) => handleFileContextMenu(event, node.path)}>
            <div className="file-tree-file-row" style={{ paddingLeft: `${depth * 14}px` }}>
              <span className="file-tree-spacer" />
              <button className={path === node.path ? "active-row" : ""} onClick={() => setPath(node.path)}>{node.name}{node.path === workspace.main_document ? " (main)" : node.editable ? "" : " (asset)"}</button>
              <button className="icon-button" onClick={(event) => toggleMenu(event, node.path, "file")}>...</button>
            </div>
            {menuTarget?.path === node.path && menuTarget.kind === "file" && <div className="tree-menu-inline" style={{ marginLeft: `${depth * 14 + 22}px` }} onMouseDown={(event) => event.stopPropagation()}><button onClick={() => openRenameRow(node.path, "file")}>Rename File</button><button className="danger-text" onClick={() => confirmDelete(node.path, "file")}>Hapus File</button></div>}
            {pendingRename?.path === node.path && <div className="inline-create-row" style={{ marginLeft: `${depth * 14 + 22}px` }}><input autoFocus value={pendingName} onChange={(event) => setPendingName(event.target.value)} onKeyDown={(event) => { if (event.key === "Enter") submitPendingRename(); if (event.key === "Escape") { setPendingRename(null); setPendingName(""); } }} placeholder="nama-file-baru.tex" /><button className="secondary" onClick={submitPendingRename} disabled={!pendingName.trim() || renameEntry.isPending}>{renameEntry.isPending ? "Menyimpan..." : "Rename"}</button><button className="text-button" onClick={() => { setPendingRename(null); setPendingName(""); }}>Batal</button></div>}
          </div>
        );
      }
    }
    return entries;
  }

  return <section className="workspace"><aside className="file-tree"><div className="panel-title"><strong>EXPLORER</strong></div>{fileNotice && <p className="notice compact-notice">{fileNotice}</p>}{createFolder.error && <p className="error">{(createFolder.error as Error).message}</p>}{createFile.error && <p className="error">{(createFile.error as Error).message}</p>}{renameEntry.error && <p className="error">{(renameEntry.error as Error).message}</p>}{uploadAsset.error && <p className="error">{(uploadAsset.error as Error).message}</p>}{removeEntry.error && <p className="error">{(removeEntry.error as Error).message}</p>}<input ref={uploadInputRef} type="file" className="hidden-upload" onChange={onUploadSelected} /><div className="tree-entry-block"><div className="file-tree-root-row"><button className="folder-caret" onClick={() => toggleFolder("__root__")}>{expandedFolders.has("__root__") ? "v" : ">"}</button><button className="file-tree-root" onClick={() => toggleFolder("__root__")}><span className="folder-icon">[]</span>{workspace.name}</button><button className="icon-button" onClick={(event) => toggleMenu(event, "", "folder")}>...</button></div>{menuTarget?.path === "" && menuTarget.kind === "folder" && <div className="tree-menu-inline" onMouseDown={(event) => event.stopPropagation()}><button onClick={() => openCreateRow("file")}>Tambah File Baru</button><button onClick={() => openCreateRow("folder")}>Tambah Folder</button><button onClick={() => openFolderUpload("")}>Upload File</button></div>}{expandedFolders.has("__root__") && renderChildren(rootTree.children, "", 1)}</div></aside><div className="editor-pane"><div className="editor-toolbar"><span>{path || "Pilih file"}</span><div><span className="presence-dot" style={{ background: color }} /> realtime<button className="secondary" onClick={() => path && save.mutate({ targetPath: path, nextContent: content })} disabled={!path || !selectedItem?.editable || save.isPending}>{save.isPending ? "Menyimpan..." : "Save"}</button>{isTexFileSelected && <button className="secondary" onClick={async () => { if (!path) return; await ensureSavedBeforeCompile(); compileFile.mutate(path); }} disabled={save.isPending || compileFile.isPending || compile.isPending || job.data?.status === "RUNNING"}>{compileFile.isPending ? "Menyiapkan file..." : job.data?.status === "RUNNING" && compiledPath === path ? `Compile File ${job.data.progress_percent}%` : "Compile File"}</button>}<button className="danger-button" disabled={!canDelete || removeEntry.isPending} onClick={() => path && confirmDelete(path, "file")}>{removeEntry.isPending ? "Menghapus..." : "Hapus"}</button><button className="primary" onClick={async () => { await ensureSavedBeforeCompile(); compile.mutate(); }} disabled={save.isPending || compile.isPending || compileFile.isPending || job.data?.status === "RUNNING"}>{compile.isPending ? "Menyiapkan compile..." : job.data?.status === "RUNNING" && !compiledPath ? `Compile ${job.data.progress_percent}%` : "Compile Main"}</button></div></div>{job.data && ["QUEUED", "RUNNING"].includes(job.data.status) && <div className="review-progress-card"><div className="review-progress-head"><strong>{job.data.progress_percent}%</strong><span>{job.data.progress_message}</span></div><div className="review-progress-bar"><div className="review-progress-fill" style={{ width: `${job.data.progress_percent}%` }} /></div></div>}{showCompileError && <div className="error dismissible-error"><button className="error-close" onClick={() => setDismissedCompileErrorKey(compileErrorKey)} aria-label="Tutup pesan compile gagal">x</button><div><strong>Compile gagal{compiledPath ? ` pada ${compiledPath}` : ""}:</strong> {compileError}{compileErrorLine !== null && <span> | line {compileErrorLine}</span>}{compileErrorContext && <div className="compile-error-context">{compileErrorContext}</div>}</div></div>}{path && selectedItem?.editable && file.data ? <CollaborativeEditor key={`${workspace.id}:${path}`} room={`project:${projectId}:workspace:${workspace.id}:file:${path}`} value={content} user={{ name: user.display_name, color }} onChange={setContent} workspaceFiles={(files.data?.files || []).filter((item) => item.kind === "file").map((item) => item.path)} /> : <Splash text={selectedItem && !selectedItem.editable ? "File asset tidak dibuka di editor." : "Membuka file..."} />}</div><aside className="preview-pane"><div className="editor-toolbar"><span>PDF PREVIEW</span><div>{downloadUrl && <a className="secondary" href={downloadUrl}>Download PDF</a>}</div></div>{preview ? <iframe title="PDF preview" src={preview} /> : <div className="preview-empty">Compile untuk melihat PDF.</div>}</aside></section>;
}
