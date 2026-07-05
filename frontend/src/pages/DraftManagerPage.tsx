import { useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import LazyPdfDocumentViewer from "../components/LazyPdfDocumentViewer";
import PageHeader from "../components/PageHeader";
import PanelCard from "../components/PanelCard";
import WaitingState from "../components/WaitingState";
import {
  compileFullDocument,
  deleteRevisionDraft,
  listRevisionDrafts,
  setRevisionDraftFullDocumentActive
} from "../lib/api";

export default function DraftManagerPage() {
  const queryClient = useQueryClient();
  const [deleteCandidate, setDeleteCandidate] = useState("");
  const draftsQuery = useQuery({
    queryKey: ["revision-drafts"],
    queryFn: listRevisionDrafts
  });
  const activeDrafts = useMemo(
    () => draftsQuery.data?.filter((draft) => draft.is_active_for_full_document) ?? [],
    [draftsQuery.data]
  );

  const toggleActiveMutation = useMutation({
    mutationFn: setRevisionDraftFullDocumentActive,
    onSuccess: async () => {
      fullDocumentMutation.reset();
      await queryClient.invalidateQueries({ queryKey: ["revision-drafts"] });
    }
  });

  const fullDocumentMutation = useMutation({
    mutationFn: compileFullDocument
  });

  const deleteMutation = useMutation({
    mutationFn: deleteRevisionDraft,
    onSuccess: async () => {
      setDeleteCandidate("");
      fullDocumentMutation.reset();
      await queryClient.invalidateQueries({ queryKey: ["revision-drafts"] });
    }
  });

  function handleToggleActive(draftJsonPath: string, nextValue: boolean) {
    deleteMutation.reset();
    void toggleActiveMutation.mutateAsync({
      draft_json_path: draftJsonPath,
      is_active_for_full_document: nextValue
    });
  }

  const fullDocumentResult = fullDocumentMutation.data;
  const fullDocumentCompileFailed = Boolean(
    fullDocumentResult && (!fullDocumentResult.compile_result.success || !fullDocumentResult.pdf_preview_url)
  );

  return (
    <div className="page-stack">
      <PageHeader
        badge="Drafts"
        title="Draft Manager"
        description="Kelola draft revisi, tentukan mana yang dipakai untuk dokumen final, lalu generate full PDF tanpa mengubah file thesis asli."
      />

      <PanelCard
        title="Dokumen Final"
        subtitle="Draft aktif akan digabungkan ke salinan thesis sementara. Jika ada area yang bentrok, draft aktif lama akan dimatikan otomatis saat Anda mengaktifkan draft baru."
      >
        <div className="draft-manager-summary">
          <div className="tree-card final-document-summary-card">
            <strong>{activeDrafts.length} draft aktif untuk dokumen final</strong>
            <ul className="selection-summary">
              <li>{draftsQuery.data?.length ?? 0} draft tersimpan di Draft Manager</li>
              <li>{activeDrafts.length ? `${activeDrafts.length} bagian akan memakai versi revisi` : "Semua bagian masih memakai versi original"}</li>
            </ul>
            {activeDrafts.length ? (
              <div className="active-draft-chip-list">
                {activeDrafts.map((draft) => (
                  <span className="pill" key={draft.json_path}>
                    {draft.selected_label || "Draft aktif"}
                  </span>
                ))}
              </div>
            ) : null}
          </div>

          <div className="toolbar-row toolbar-row-end draft-manager-actions">
            <button
              type="button"
              className="primary-button"
              onClick={() => void fullDocumentMutation.mutateAsync()}
              disabled={!activeDrafts.length || fullDocumentMutation.isPending}
            >
              {fullDocumentMutation.isPending ? "Generating..." : "Generate Full PDF"}
            </button>
          </div>
        </div>

        {toggleActiveMutation.error ? (
          <p className="feedback error">{(toggleActiveMutation.error as Error).message}</p>
        ) : null}
        {fullDocumentMutation.error || fullDocumentCompileFailed ? (
          <div className="compile-failure" role="alert">
            <div>
              <strong>Compile full document gagal.</strong>
              <p>
                {fullDocumentMutation.error
                  ? (fullDocumentMutation.error as Error).message || "Silakan coba lagi."
                  : fullDocumentResult?.compile_result.summary || "Silakan coba lagi."}
              </p>
            </div>
            <button
              type="button"
              className="secondary-button"
              onClick={() => void fullDocumentMutation.mutateAsync()}
              disabled={!activeDrafts.length || fullDocumentMutation.isPending}
            >
              Coba Lagi
            </button>
          </div>
        ) : null}
        {fullDocumentMutation.isPending ? (
          <WaitingState
            title="Sedang menyusun dokumen final"
            detail="Bagian revisi aktif sedang digabungkan ke thesis penuh lalu di-compile untuk preview akhir."
          />
        ) : null}
        {fullDocumentResult?.pdf_preview_url && !fullDocumentCompileFailed ? (
          <div className="page-stack full-document-preview-section">
            <div className="compare-result-header">
              <div>
                <span className="pill">Full PDF siap</span>
                <strong>{fullDocumentResult.applied_draft_count} draft diterapkan</strong>
              </div>
              {fullDocumentResult.pdf_download_url ? (
                <a className="secondary-button pdf-download-link" href={fullDocumentResult.pdf_download_url}>
                  Download Full PDF
                </a>
              ) : null}
            </div>
            <PanelCard title="Preview Full PDF" subtitle="Menampilkan dokumen thesis utuh dengan kombinasi bagian original dan revisi aktif.">
              <LazyPdfDocumentViewer
                title="Preview Full PDF"
                pdfUrl={fullDocumentResult.pdf_preview_url}
              />
            </PanelCard>
          </div>
        ) : null}
      </PanelCard>

      <PanelCard
        title="Daftar Draft"
        subtitle="Pilih draft untuk compare, edit, hapus, atau tandai sebagai bagian dari dokumen final."
      >
        {draftsQuery.isLoading ? <p className="muted">Memuat draft revisi...</p> : null}
        {draftsQuery.error ? (
          <p className="feedback error">{(draftsQuery.error as Error).message}</p>
        ) : null}
        {toggleActiveMutation.data ? (
          <p className="feedback success">Draft aktif untuk dokumen final berhasil diperbarui.</p>
        ) : null}
        {deleteMutation.error ? (
          <p className="feedback error">Draft gagal dihapus. Silakan coba lagi.</p>
        ) : null}
        {deleteMutation.data ? (
          <p className="feedback success">Draft berhasil dihapus.</p>
        ) : null}
        {!draftsQuery.isLoading && !draftsQuery.data?.length ? (
          <p className="muted">Belum ada draft revisi tersimpan.</p>
        ) : null}
        <div className="draft-list">
          {draftsQuery.data?.map((draft) => (
            <div className="draft-row" key={draft.json_path}>
              <div>
                <strong>{draft.selected_label || "Draft tanpa label"}</strong>
                <p className="muted">File sumber: {draft.selected_file || "-"}</p>
              </div>
              <div className="draft-meta">
                <div className="draft-pill-row">
                  <span className="pill">Ready to Compare</span>
                  <span className="pill draft-usage-pill">
                    {draft.is_active_for_full_document ? "Aktif di Full PDF" : "Belum Dipakai"}
                  </span>
                </div>
                {deleteCandidate === draft.json_path ? (
                  <div className="delete-confirmation" role="alert">
                    <span>Yakin ingin menghapus draft ini?</span>
                    <div className="toolbar-row">
                      <button
                        type="button"
                        className="secondary-button"
                        onClick={() => setDeleteCandidate("")}
                        disabled={deleteMutation.isPending}
                      >
                        Batal
                      </button>
                      <button
                        type="button"
                        className="danger-button"
                        onClick={() => deleteMutation.mutate({ draft_json_path: draft.json_path })}
                        disabled={deleteMutation.isPending}
                      >
                        {deleteMutation.isPending ? "Menghapus..." : "Hapus Permanen"}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="toolbar-row">
                    <button
                      type="button"
                      className={draft.is_active_for_full_document ? "secondary-button" : "primary-button"}
                      onClick={() => handleToggleActive(draft.json_path, !draft.is_active_for_full_document)}
                      disabled={toggleActiveMutation.isPending || deleteMutation.isPending}
                    >
                      {toggleActiveMutation.isPending && toggleActiveMutation.variables?.draft_json_path === draft.json_path
                        ? "Menyimpan..."
                        : draft.is_active_for_full_document
                          ? "Nonaktifkan"
                          : "Pakai untuk Full PDF"}
                    </button>
                    <Link className="secondary-button inline-link-button" to={`/compare?draft=${encodeURIComponent(draft.json_path)}`}>
                      Buka Compare
                    </Link>
                    <Link className="primary-button inline-link-button" to={`/editor?draft=${encodeURIComponent(draft.json_path)}`}>
                      Edit Draft
                    </Link>
                    <button
                      type="button"
                      className="danger-button"
                      onClick={() => {
                        deleteMutation.reset();
                        setDeleteCandidate(draft.json_path);
                      }}
                      disabled={deleteMutation.isPending}
                    >
                      Hapus
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      </PanelCard>
    </div>
  );
}
