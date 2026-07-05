import { useEffect, useRef, useState, startTransition } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import LatexSourceViewer from "../components/LatexSourceViewer";
import PageHeader from "../components/PageHeader";
import PanelCard from "../components/PanelCard";
import ReviewSuggestionCard from "../components/ReviewSuggestionCard";
import WaitingState from "../components/WaitingState";
import {
  createRevisionDraft,
  getDocumentContent,
  getStructure,
  listDocuments,
  saveRevisionDraft,
  submitReview
} from "../lib/api";

const DEFAULT_GOAL =
  "Periksa kualitas akademik argumen, kejelasan penjelasan, konsistensi istilah, bagian yang butuh sitasi, dan kalimat yang perlu dirapikan.";

export default function ReviewDraftPage() {
  const [selectedFile, setSelectedFile] = useState("");
  const [selectedTargetKey, setSelectedTargetKey] = useState("");
  const [userGoal, setUserGoal] = useState(DEFAULT_GOAL);
  const reviewResultsRef = useRef<HTMLDivElement>(null);
  const revisionResultsRef = useRef<HTMLDivElement>(null);

  const documentsQuery = useQuery({
    queryKey: ["documents"],
    queryFn: listDocuments
  });

  useEffect(() => {
    if (!selectedFile && documentsQuery.data?.length) {
      setSelectedFile(documentsQuery.data[0]);
    }
  }, [documentsQuery.data, selectedFile]);

  const structureQuery = useQuery({
    queryKey: ["structure", selectedFile],
    queryFn: () => getStructure(selectedFile),
    enabled: Boolean(selectedFile)
  });

  useEffect(() => {
    const firstItem = structureQuery.data?.items[0];
    if (!firstItem) {
      return;
    }

    const currentExists = structureQuery.data?.items.some(
      (item) => `${item.scope}::${item.target_id}` === selectedTargetKey
    );

    if (!selectedTargetKey || !currentExists) {
      setSelectedTargetKey(`${firstItem.scope}::${firstItem.target_id}`);
    }
  }, [selectedTargetKey, structureQuery.data]);

  const selectedItem = structureQuery.data?.items.find(
    (item) => `${item.scope}::${item.target_id}` === selectedTargetKey
  );

  const contentQuery = useQuery({
    queryKey: ["content", selectedFile, selectedItem?.scope, selectedItem?.target_id],
    queryFn: () => getDocumentContent(selectedFile, selectedItem!.scope, selectedItem!.target_id),
    enabled: Boolean(selectedFile && selectedItem)
  });

  const reviewMutation = useMutation({
    mutationFn: submitReview
  });

  const revisionMutation = useMutation({
    mutationFn: createRevisionDraft
  });

  const saveDraftMutation = useMutation({
    mutationFn: saveRevisionDraft
  });

  useEffect(() => {
    reviewMutation.reset();
    revisionMutation.reset();
    saveDraftMutation.reset();
  }, [selectedFile, selectedTargetKey]);

  const selectedScope = selectedItem?.scope ?? "chapter";
  const selectedTargetId = selectedItem?.target_id ?? "chapter:full";
  const reviewResult = reviewMutation.data;
  const revisionResult = revisionMutation.data;
  const reviewNotice = reviewResult ? getReviewNotice(reviewResult.review_source, reviewResult.summary) : "";

  useEffect(() => {
    if (!reviewResult) {
      return;
    }
    window.requestAnimationFrame(() => {
      reviewResultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [reviewResult]);

  useEffect(() => {
    if (!revisionResult) {
      return;
    }
    window.requestAnimationFrame(() => {
      revisionResultsRef.current?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  }, [revisionResult]);

  async function handleRunReview() {
    if (!selectedFile || !selectedItem) {
      return;
    }

    reviewMutation.reset();
    revisionMutation.reset();
    saveDraftMutation.reset();
    await reviewMutation.mutateAsync({
      selected_file: selectedFile,
      selected_scope: selectedScope,
      selected_target_id: selectedTargetId,
      user_goal: userGoal
    });
  }

  async function handleCreateRevision() {
    if (!reviewResult || !contentQuery.data) {
      return;
    }

    revisionMutation.reset();
    saveDraftMutation.reset();
    await revisionMutation.mutateAsync({
      source_text: contentQuery.data.source_text,
      suggestions: reviewResult.suggestions,
      context_label: reviewResult.selected_label,
      user_goal: userGoal
    });
  }

  async function handleSaveDraft() {
    if (!revisionResult || !contentQuery.data) {
      return;
    }

    await saveDraftMutation.mutateAsync({
      selected_file: selectedFile,
      selected_label: reviewResult?.selected_label ?? contentQuery.data.selected_label,
      content: revisionResult.revised_text,
      metadata: {
        selected_file: selectedFile,
        selected_scope: selectedScope,
        selected_target_id: selectedTargetId,
        selected_label: reviewResult?.selected_label ?? contentQuery.data.selected_label,
        original_text: contentQuery.data.source_text,
        revised_text: revisionResult.revised_text,
        revision_summary: revisionResult.revision_summary,
        review_snapshot: reviewResult
          ? {
              schema_version: 1,
              review_source: reviewResult.review_source,
              user_goal: userGoal,
              created_at: new Date().toISOString(),
              suggestions: reviewResult.suggestions
            }
          : undefined
      }
    });
  }

  return (
    <div className="page-stack">
      <PageHeader
        badge="Review"
        title="Review Draft"
        description="Pilih bab, sub bab, atau sub sub bab lalu jalankan review, buat draft revisi, dan simpan hasilnya tanpa mengubah file asli."
      />
      <div className="two-column-grid review-layout">
        <PanelCard
          title="Navigator Dokumen"
          subtitle="Pilih file dan bagian skripsi yang ingin diperiksa."
        >
          <div className="control-stack">
            <label className="field-label" htmlFor="selected-file">
              File LaTeX
            </label>
            <select
              id="selected-file"
              className="app-select"
              value={selectedFile}
              onChange={(event) => {
                const nextFile = event.target.value;
                startTransition(() => {
                  setSelectedFile(nextFile);
                  setSelectedTargetKey("");
                });
              }}
            >
              {documentsQuery.data?.map((item) => (
                <option key={item} value={item}>
                  {item}
                </option>
              ))}
            </select>
            {documentsQuery.isLoading ? <p className="muted">Memuat daftar dokumen...</p> : null}
            {documentsQuery.error ? (
              <p className="feedback error">{(documentsQuery.error as Error).message}</p>
            ) : null}
          </div>

          <div className="control-stack">
            <label className="field-label" htmlFor="selected-target">
              Target Review
            </label>
            <select
              id="selected-target"
              className="app-select"
              value={selectedTargetKey}
              onChange={(event) => setSelectedTargetKey(event.target.value)}
              disabled={!structureQuery.data?.items.length}
            >
              {structureQuery.data?.items.map((item) => (
                <option
                  key={`${item.scope}::${item.target_id}`}
                  value={`${item.scope}::${item.target_id}`}
                >
                  {item.label}
                </option>
              ))}
            </select>
            {structureQuery.isLoading ? <p className="muted">Membaca struktur bab...</p> : null}
            {structureQuery.error ? (
              <p className="feedback error">{(structureQuery.error as Error).message}</p>
            ) : null}
          </div>

          <div className="control-stack">
            <label className="field-label" htmlFor="review-goal">
              Fokus Review
            </label>
            <textarea
              id="review-goal"
              className="app-textarea"
              value={userGoal}
              onChange={(event) => setUserGoal(event.target.value)}
              rows={5}
            />
          </div>

          <div className="selection-strip">
            <span>{contentQuery.data?.selected_label || selectedItem?.label || "Belum ada bagian dipilih"}</span>
            <span>
              Baris {contentQuery.data
                ? contentQuery.data.start_line + "-" + contentQuery.data.end_line
                : "-"}
            </span>
          </div>
        </PanelCard>

        <PanelCard
          title="Source LaTeX"
          subtitle="Menampilkan isi bagian terpilih, bukan seluruh dokumen, agar review lebih terkontrol."
        >
          <div className="toolbar-row">
            <button
              type="button"
              className="primary-button"
              onClick={() => void handleRunReview()}
              disabled={!selectedFile || !selectedItem || reviewMutation.isPending}
            >
              {reviewMutation.isPending ? "Menjalankan Review..." : "Jalankan Review"}
            </button>
          </div>
          {contentQuery.isLoading ? <p className="muted">Mengambil source LaTeX...</p> : null}
          {contentQuery.error ? (
            <p className="feedback error">{(contentQuery.error as Error).message}</p>
          ) : null}
          <LatexSourceViewer
            value={contentQuery.data?.source_text || "Belum ada bagian yang dipilih."}
            minLines={18}
          />
        </PanelCard>

      </div>

      {reviewMutation.isPending ? (
        <WaitingState
          title="Sedang meninjau bagian skripsi"
          detail="AI membaca konteks, struktur argumen, konsistensi istilah, dan kebutuhan sitasi."
        />
      ) : null}

      {reviewMutation.error ? (
        <p className="feedback error">{(reviewMutation.error as Error).message}</p>
      ) : null}

      {reviewResult ? (
        <div ref={reviewResultsRef} className="review-output-section">
          <PanelCard
            title="Saran Perbaikan"
            subtitle="Periksa setiap saran sebelum membuat draft revisi."
          >
            <div className="review-notice-row">
              <span className="pill">{reviewResult.suggestions.length} saran ditemukan</span>
              {reviewNotice ? <span className="reviewer-warning">{reviewNotice}</span> : null}
            </div>
            <div className="suggestion-grid">
              {reviewResult.suggestions.map((suggestion, index) => (
                <ReviewSuggestionCard
                  key={suggestion.category + "-" + index}
                  item={suggestion}
                  index={index + 1}
                />
              ))}
            </div>
            <div className="toolbar-row toolbar-row-end review-create-action">
              <button
                type="button"
                className="primary-button"
                onClick={() => void handleCreateRevision()}
                disabled={revisionMutation.isPending}
              >
                Buat Draft Revisi
              </button>
            </div>
          </PanelCard>
        </div>
      ) : null}

      {revisionMutation.error ? (
        <p className="feedback error">{(revisionMutation.error as Error).message}</p>
      ) : null}
      {saveDraftMutation.error ? (
        <p className="feedback error">{(saveDraftMutation.error as Error).message}</p>
      ) : null}

      {revisionMutation.isPending ? (
        <WaitingState
          title="Sedang menyusun draft revisi"
          detail="Saran yang telah ditinjau sedang diterapkan ke source LaTeX."
        />
      ) : null}

      {revisionResult ? (
        <div ref={revisionResultsRef} className="review-output-section">
          <div className="two-column-grid">
            <PanelCard title="Source Original" subtitle="Bagian sebelum saran diterapkan.">
              <LatexSourceViewer value={contentQuery.data?.source_text || "-"} minLines={16} />
            </PanelCard>
            <PanelCard title="Draft Revisi" subtitle="Hasil revisi LaTeX yang siap disimpan.">
              <LatexSourceViewer value={revisionResult.revised_text} minLines={16} />
            </PanelCard>
          </div>

          <div className="revision-save-bar">
            <div>
              <strong>Ringkasan Revisi</strong>
              <p>{revisionResult.revision_summary}</p>
            </div>
            <div className="revision-save-action">
              <button
                type="button"
                className="primary-button"
                onClick={() => void handleSaveDraft()}
                disabled={saveDraftMutation.isPending}
              >
                {saveDraftMutation.isPending ? "Menyimpan Draft..." : "Simpan Draft Revisi"}
              </button>
            </div>
          </div>
          {saveDraftMutation.data ? (
            <p className="feedback success">Draft revisi berhasil disimpan dan siap dibuka dari Draft Manager.</p>
          ) : null}
        </div>
      ) : null}

      {saveDraftMutation.isPending ? (
        <WaitingState
          title="Menyimpan draft revisi"
          detail="Draft sedang disimpan tanpa mengubah file skripsi asli."
        />
      ) : null}
    </div>
  );
}

function getReviewNotice(reviewSource: string, summary: string) {
  if (reviewSource === "openrouter") {
    return "";
  }

  const failure = summary.match(/Reviewer OpenRouter gagal dipakai \(.+?\)\./)?.[0];
  if (failure) {
    return failure + " Untuk hasil maksimal, silakan coba beberapa saat lagi.";
  }

  return "Reviewer OpenRouter belum dapat dipakai. Untuk hasil maksimal, silakan coba beberapa saat lagi.";
}
