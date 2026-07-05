import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import LatexSourceViewer from "../components/LatexSourceViewer";
import PageHeader from "../components/PageHeader";
import PanelCard from "../components/PanelCard";
import LazyPdfDocumentViewer from "../components/LazyPdfDocumentViewer";
import {
  compileEditorPreview,
  loadRevisionDraft,
  saveRevisionDraftContent
} from "../lib/api";

const AUTO_SAVE_INTERVAL_MS = 10000;

export default function DraftEditorPage() {
  const [searchParams] = useSearchParams();
  const draftJsonPath = searchParams.get("draft") || "";
  const [editorText, setEditorText] = useState("");
  const [lastSavedText, setLastSavedText] = useState("");
  const [lastCompiledInput, setLastCompiledInput] = useState("");
  const timerRef = useRef<number | null>(null);

  const draftQuery = useQuery({
    queryKey: ["revision-draft-detail", draftJsonPath],
    queryFn: () => loadRevisionDraft({ draft_json_path: draftJsonPath }),
    enabled: Boolean(draftJsonPath)
  });

  const previewMutation = useMutation({
    mutationFn: compileEditorPreview
  });

  const saveMutation = useMutation({
    mutationFn: saveRevisionDraftContent,
    onSuccess: (updated) => {
      setLastSavedText(updated.revised_text);
    }
  });

  useEffect(() => {
    if (draftQuery.data) {
      setEditorText(draftQuery.data.revised_text);
      setLastSavedText(draftQuery.data.revised_text);
      setLastCompiledInput("");
    }
  }, [draftQuery.data]);

  const hasUnsavedChanges = useMemo(
    () => editorText !== lastSavedText,
    [editorText, lastSavedText]
  );

  useEffect(() => {
    if (!draftJsonPath || !draftQuery.data) {
      return;
    }

    if (timerRef.current) {
      window.clearInterval(timerRef.current);
    }

    timerRef.current = window.setInterval(() => {
      if (!hasUnsavedChanges || saveMutation.isPending) {
        return;
      }

      void saveMutation.mutateAsync({
        draft_json_path: draftJsonPath,
        content: editorText
      });
    }, AUTO_SAVE_INTERVAL_MS);

    return () => {
      if (timerRef.current) {
        window.clearInterval(timerRef.current);
      }
    };
  }, [draftJsonPath, draftQuery.data, editorText, hasUnsavedChanges, saveMutation.isPending]);

  async function handleManualCompile() {
    if (!draftJsonPath) {
      return;
    }
    const inputAtCompile = editorText;
    setLastCompiledInput("");
    const result = await previewMutation.mutateAsync({
      draft_json_path: draftJsonPath,
      content: inputAtCompile
    });
    if (result.revised.success) {
      setLastCompiledInput(inputAtCompile);
    }
  }

  async function handleSaveDraft() {
    if (!draftJsonPath) {
      return;
    }
    const updated = await saveMutation.mutateAsync({
      draft_json_path: draftJsonPath,
      content: editorText
    });
    setEditorText(updated.revised_text);
    setLastSavedText(updated.revised_text);
  }

  const previewResult = previewMutation.data;
  const previewDownloadUrl = previewResult?.revised.pdf_download_url ?? "";
  const canDownloadPreview = Boolean(
    previewDownloadUrl &&
      previewResult?.revised.success &&
      lastCompiledInput === editorText
  );

  return (
    <div className="page-stack">
      <PageHeader
        badge="Editor"
        title="Draft Editor"
        description="Edit LaTeX dan lihat hasil compile bagian terpilih secara langsung."
      />

      <div className="editor-topbar">
        <Link className="secondary-button inline-link-button" to={`/compare${draftJsonPath ? `?draft=${encodeURIComponent(draftJsonPath)}` : ""}`}>
          Kembali ke Compare
        </Link>
        <div className="toolbar-row toolbar-row-end">
          <button
            type="button"
            className="secondary-button"
            onClick={() => void handleManualCompile()}
            disabled={previewMutation.isPending}
          >
            {previewMutation.isPending ? "Compiling..." : "Compile Preview"}
          </button>
          {canDownloadPreview ? (
            <a className="primary-button pdf-download-link" href={previewDownloadUrl}>
              Download PDF
            </a>
          ) : (
            <button
              type="button"
              className="primary-button"
              disabled
              title="Compile preview terbaru sebelum mengunduh PDF."
            >
              Download PDF
            </button>
          )}
        </div>
      </div>

      {draftQuery.isLoading ? <p className="feedback success">Memuat draft editor...</p> : null}
      {draftQuery.error ? <p className="feedback error">{(draftQuery.error as Error).message}</p> : null}
      {saveMutation.error ? <p className="feedback error">{(saveMutation.error as Error).message}</p> : null}
      {previewMutation.error ? <p className="feedback error">{(previewMutation.error as Error).message}</p> : null}

      {draftQuery.data ? (
        <div className="editor-grid">
          <PanelCard
            title="Editor LaTeX"
            subtitle={`Mengedit bagian: ${draftQuery.data.selected_label}`}
          >
            <div className="toolbar-row toolbar-row-end editor-save-action">
              <button
                type="button"
                className="primary-button"
                onClick={() => void handleSaveDraft()}
                disabled={!hasUnsavedChanges || saveMutation.isPending}
              >
                Save
              </button>
            </div>
            <LatexSourceViewer
              title="Draft Revisi"
              value={editorText}
              editable
              onChange={setEditorText}
              minLines={28}
            />
          </PanelCard>

          <PanelCard title="Preview Bagian Terpilih">
            {previewResult?.revised.pdf_preview_url ? (
              <LazyPdfDocumentViewer
                title="Preview Revisi"
                pdfUrl={previewResult.revised.pdf_preview_url}
              />
            ) : (
              <div className="pdf-placeholder">Klik `Compile Preview` untuk melihat hasil compile terbaru di panel kanan.</div>
            )}
          </PanelCard>
        </div>
      ) : null}

    </div>
  );
}
