import re
from collections import Counter

from app.services.campus_guidelines import build_abstract_rule_suggestions


def split_paragraphs(document_text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in re.split(r"\n\s*\n", document_text)]
    return [chunk for chunk in chunks if chunk and not chunk.startswith("%")]


def strip_latex_commands(text: str) -> str:
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def build_rule_based_suggestions(
    paragraphs: list[str],
    *,
    selected_label: str = "",
    source_text: str = "",
) -> list[dict]:
    suggestions: list[dict] = []

    suggestions.extend(build_abstract_rule_suggestions(selected_label, source_text))

    for index, paragraph in enumerate(paragraphs, start=1):
        cleaned = strip_latex_commands(paragraph)
        if not cleaned:
            continue

        words = cleaned.split()
        sentences = [part.strip() for part in re.split(r"[.!?]+", cleaned) if part.strip()]
        avg_sentence_length = sum(len(sentence.split()) for sentence in sentences) / max(len(sentences), 1)
        has_citation = any(token in paragraph for token in ("\\cite", "\\textcite", "\\parencite"))
        most_common = Counter(word.lower() for word in words if len(word) > 4).most_common(1)

        if len(words) > 140:
            suggestions.append(
                {
                    "category": "paragraph-length",
                    "title": f"Paragraf {index} terlalu padat",
                    "detail": (
                        f"Paragraf ini berisi sekitar {len(words)} kata. Pertimbangkan membaginya "
                        "menjadi dua paragraf agar ide utama lebih mudah diikuti."
                    ),
                    "paragraph_index": index,
                    "priority": "medium",
                    "suggested_revision": "Pisahkan gagasan utama dan penjelasannya menjadi dua paragraf yang lebih fokus.",
                    "source": "rule-based",
                }
            )

        if avg_sentence_length > 28:
            suggestions.append(
                {
                    "category": "sentence-length",
                    "title": f"Kalimat di paragraf {index} cenderung panjang",
                    "detail": (
                        f"Rata-rata panjang kalimat sekitar {avg_sentence_length:.0f} kata. "
                        "Coba pecah beberapa kalimat agar nada akademiknya lebih jelas."
                    ),
                    "paragraph_index": index,
                    "priority": "medium",
                    "suggested_revision": "Ubah satu kalimat panjang menjadi dua atau tiga kalimat yang lebih langsung.",
                    "source": "rule-based",
                }
            )

        if len(words) > 70 and not has_citation:
            suggestions.append(
                {
                    "category": "citation-gap",
                    "title": f"Paragraf {index} mungkin membutuhkan sitasi",
                    "detail": (
                        "Paragraf cukup panjang namun belum terdeteksi sitasi LaTeX. "
                        "Jika ada definisi, klaim, atau data dari literatur, tambahkan referensi."
                    ),
                    "paragraph_index": index,
                    "priority": "high",
                    "suggested_revision": "Tambahkan sitasi pada klaim, definisi, atau hasil penelitian yang berasal dari literatur.",
                    "source": "rule-based",
                }
            )

        if most_common and most_common[0][1] >= 4:
            suggestions.append(
                {
                    "category": "repetition",
                    "title": f"Istilah dominan di paragraf {index} perlu dicek",
                    "detail": (
                        f"Istilah `{most_common[0][0]}` cukup sering muncul dalam paragraf ini. "
                        "Periksa apakah ada repetisi yang bisa diringkas atau diganti sinonim yang tetap akademik."
                    ),
                    "paragraph_index": index,
                    "priority": "low",
                    "suggested_revision": "Rapikan repetisi istilah jika memang tidak diperlukan untuk penekanan konsep.",
                    "source": "rule-based",
                }
            )

    if not suggestions:
        suggestions.append(
            {
                "category": "healthy-draft",
                "title": "Draft terlihat cukup rapi secara struktur dasar",
                "detail": (
                    "Tidak ada masalah besar yang terdeteksi oleh analyzer lokal. "
                    "Jika kamu ingin review yang lebih kontekstual, aktifkan reviewer LLM melalui OPENROUTER_API_KEY."
                ),
                "paragraph_index": 0,
                "priority": "low",
                "suggested_revision": "Tidak ada revisi mekanis yang mendesak dari checker lokal.",
                "source": "rule-based",
            }
        )

    return suggestions


def build_summary(selected_label: str, suggestions: list[dict], review_source: str) -> str:
    major_categories = sorted({suggestion["category"] for suggestion in suggestions})
    categories = ", ".join(major_categories)
    return (
        f"Review untuk `{selected_label}` selesai menggunakan `{review_source}`. "
        f"Sistem menemukan {len(suggestions)} saran dengan fokus pada: {categories}."
    )
