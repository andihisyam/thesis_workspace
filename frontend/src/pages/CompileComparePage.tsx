import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { useNavigate, useSearchParams } from "react-router-dom";
import PageHeader from "../components/PageHeader";
import PanelCard from "../components/PanelCard";
import LazyPdfDocumentViewer from "../components/LazyPdfDocumentViewer";
import ReviewSuggestionCard from "../components/ReviewSuggestionCard";
import WaitingState from "../components/WaitingState";
import {
  compileCompare,
  listRevisionDrafts,
  type RevisionDraftRecord
} from "../lib/api";

export default function CompileComparePage() {
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const draftsQuery = useQuery({
    queryKey: ["revision-drafts"],
    queryFn: listRevisionDrafts
  });
  const initialDraft = searchParams.get("draft") || "";
  const [selectedDraftPath, setSelectedDraftPath] = useState(initialDraft);
  const compareResultRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedDraftPath !== (searchParams.get("draft") || "")) {
      setSearchParams(selectedDraftPath ? { draft: selectedDraftPath } : {});
    }
  }, [selectedDraftPath, searchParams, setSearchParams]);

  const selectedDraft = useMemo(
    () => draftsQuery.data?.find((item) => item.json_path === selectedDraftPath),
    [draftsQuery.data, selectedDraftPath]
  );

  const compareMutation = useMutation({
    mutationFn: compileCompare
  });

  useEffect(() => {
    if (!compareMutation.data && !compareMutation.error) {
      return;
    }
    window.requestAnimationFrame(() => {
      compareResultRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [compareMutation.data, compareMutation.error]);

  const compareResult = compareMutation.data;
  const compareSucceeded = Boolean(
    compareResult?.original.success &&
      compareResult.revised.success &&
      compareResult.original.pdf_preview_url &&
      compareResult.revised.pdf_preview_url
  );
  const compareFailed = Boolean(compareMutation.error || (compareResult && !compareSucceeded));
  const reviewSuggestions = selectedDraft?.review_snapshot?.suggestions ?? [];

  function handleDraftChange(nextDraftPath: string) {
    compareMutation.reset();
    setSelectedDraftPath(nextDraftPath);
  }

  function handleRunCompare() {
    if (!selectedDraftPath || !selectedDraft) {
      return;
    }
    compareMutation.reset();
    compareMutation.mutate({ draft_json_path: selectedDraftPath });
  }

  return (
    <div className="page-stack">
      <PageHeader
        badge="Compare"
        title="Compile & Compare"
        description="Pilih draft revisi, lalu jalankan compare untuk melihat PDF original dan revisi bagian tersebut."
      />

      <PanelCard
        title="Draft Revisi"
        subtitle="Pilih draft terlebih dahulu. Compile hanya berjalan setelah tombol ditekan."
      >
        <div className="control-stack">
          <label className="field-label" htmlFor="compare-draft-select">
            Pilih Draft
          </label>
          <select
            id="compare-draft-select"
            className="app-select"
            value={selectedDraftPath}
            onChange={(event) => handleDraftChange(event.target.value)}
            disabled={!draftsQuery.data?.length || compareMutation.isPending}
          >
            <option value="">Pilih draft revisi...</option>
            {draftsQuery.data?.map((draft) => (
              <option key={draft.json_path} value={draft.json_path}>
                {draft.selected_label || draft.selected_file || draft.json_path}
              </option>
            ))}
          </select>
          {draftsQuery.isLoading ? <p className="muted">Memuat draft revisi...</p> : null}
          {draftsQuery.error ? (
            <p className="feedback error">{(draftsQuery.error as Error).message}</p>
          ) : null}
          {!draftsQuery.isLoading && !draftsQuery.data?.length ? (
            <p className="feedback error">Belum ada draft revisi tersimpan. Buat dulu dari halaman Review Draft.</p>
          ) : null}
        </div>

        {selectedDraft ? <DraftSummaryCard draft={selectedDraft} /> : null}

        <div className="toolbar-row toolbar-row-end compare-start-action">
          <button
            type="button"
            className="primary-button"
            onClick={() => void handleRunCompare()}
            disabled={!selectedDraft || compareMutation.isPending}
          >
            Compile & Compare
          </button>
        </div>
      </PanelCard>

      {compareMutation.isPending ? (
        <WaitingState
          title="Sedang menyiapkan perbandingan"
          detail="Versi original dan revisi sedang di-compile untuk preview bagian terpilih."
        />
      ) : null}

      {compareFailed || compareSucceeded ? (
        <div ref={compareResultRef} className="compare-result-section">
          {compareFailed ? (
            <div className="compile-failure" role="alert">
              <div>
                <strong>Compile gagal.</strong>
                <p>Silakan coba lagi.</p>
              </div>
              <button
                type="button"
                className="secondary-button"
                onClick={() => void handleRunCompare()}
              >
                Coba Lagi
              </button>
            </div>
          ) : null}

          {compareSucceeded && compareResult ? (
            <>
              <div className="compare-result-header">
                <div>
                  <span className="pill">Compare selesai</span>
                  <strong>{compareResult.fragment_label}</strong>
                </div>
                <div className="toolbar-row">
                  <button
                    type="button"
                    className="primary-button"
                    onClick={() => navigate(`/editor?draft=${encodeURIComponent(selectedDraftPath)}`)}
                  >
                    Edit Draft
                  </button>
                  {compareResult.revised.pdf_download_url ? (
                    <a
                      className="secondary-button pdf-download-link"
                      href={compareResult.revised.pdf_download_url}
                    >
                      Download PDF Revisi
                    </a>
                  ) : null}
                </div>
              </div>

              {reviewSuggestions.length ? (
                <details className="review-snapshot-card">
                  <summary>
                    <div>
                      <strong>Saran Review Acuan</strong>
                      <span>Saran yang tersimpan saat draft revisi dibuat.</span>
                    </div>
                    <span className="pill">{reviewSuggestions.length} saran</span>
                  </summary>
                  <div className="review-snapshot-body">
                    <div className="suggestion-grid">
                      {reviewSuggestions.map((suggestion, index) => (
                        <ReviewSuggestionCard
                          key={suggestion.category + "-" + index}
                          item={suggestion}
                          index={index + 1}
                        />
                      ))}
                    </div>
                  </div>
                </details>
              ) : null}

              <div className="two-column-grid">
                <PanelCard title="Hasil Original" subtitle={"Hanya menampilkan " + compareResult.fragment_label + "."}>
                  <LazyPdfDocumentViewer title="Hasil Original" pdfUrl={compareResult.original.pdf_preview_url} />
                </PanelCard>
                <PanelCard title="Hasil Revisi" subtitle={"Hanya menampilkan " + compareResult.fragment_label + "."}>
                  <LazyPdfDocumentViewer title="Hasil Revisi" pdfUrl={compareResult.revised.pdf_preview_url} />
                </PanelCard>
              </div>
            </>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

function DraftSummaryCard({ draft }: { draft: RevisionDraftRecord }) {
  return (
    <div className="tree-card">
      <strong>{draft.selected_label || "Draft revisi"}</strong>
      <ul className="selection-summary">
        <li>File sumber: {draft.selected_file || "-"}</li>
      </ul>
      {draft.revision_summary ? <p className="muted">{draft.revision_summary}</p> : null}
    </div>
  );
}
