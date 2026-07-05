import type { ReviewSuggestion } from "../lib/api";

const PRIORITY_LABELS: Record<string, string> = {
  high: "Tinggi",
  medium: "Sedang",
  low: "Rendah"
};

type ReviewSuggestionCardProps = {
  item: ReviewSuggestion;
  index: number;
};

export default function ReviewSuggestionCard({ item, index }: ReviewSuggestionCardProps) {
  return (
    <article className="result-card">
      <div className="suggestion-heading">
        <strong>
          {index}. {item.title}
        </strong>
        <span className="pill">{PRIORITY_LABELS[item.priority] ?? item.priority}</span>
      </div>
      <p className="muted">Paragraf {item.paragraph_index || "-"}</p>
      <p>{item.detail}</p>
      {item.suggested_revision ? (
        <p className="suggested-revision">{item.suggested_revision}</p>
      ) : null}
    </article>
  );
}
