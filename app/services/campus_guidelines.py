from __future__ import annotations

import re


CITATION_COMMANDS = ("\\cite", "\\textcite", "\\parencite", "\\autocite")


def detect_review_profile(selected_label: str) -> str:
    normalized = selected_label.strip().upper()
    if normalized == "ABSTRAK":
        return "abstract_id"
    if normalized == "ABSTRACT":
        return "abstract_en"
    return "general"


def build_llm_review_guidance(selected_label: str) -> str:
    profile = detect_review_profile(selected_label)
    if profile == "abstract_id":
        return (
            "Aturan kampus khusus ABSTRAK yang wajib dicek:\n"
            "- Ditulis dalam bahasa Indonesia.\n"
            "- Hanya satu alinea.\n"
            "- Maksimal 200 kata.\n"
            "- Tidak boleh ada sitasi.\n"
            "- Harus merangkum masalah, tujuan, metode, hasil, dan kesimpulan secara singkat.\n"
            "- Hindari simbol, identifier, atau istilah teknis yang terlalu spesifik jika masih bisa ditulis lebih umum.\n"
            "- Kata kunci maksimal 6, ditulis huruf kecil."
        )
    if profile == "abstract_en":
        return (
            "Campus rules for ABSTRACT that must be checked:\n"
            "- Written in English.\n"
            "- Single paragraph only.\n"
            "- Maximum 200 words.\n"
            "- No citations.\n"
            "- Must briefly cover problem context, objective, method, result, and conclusion.\n"
            "- Avoid overly technical symbols or identifiers when a general wording is possible.\n"
            "- Keywords must contain no more than 6 items and should be lower-case except abbreviations."
        )
    return ""


def _split_body_and_keywords(source_text: str) -> tuple[str, str]:
    keyword_pattern = re.compile(r"^(?:\\noindent\s*)?\\textbf\{(Kata Kunci|Keywords):\}\s*(.*)$", re.IGNORECASE)
    lines = source_text.splitlines()
    body_lines: list[str] = []
    keyword_line = ""

    for line in lines:
        if keyword_pattern.match(line.strip()):
            keyword_line = line.strip()
            continue
        body_lines.append(line)

    return "\n".join(body_lines).strip(), keyword_line


def _strip_latex_commands(text: str) -> str:
    text = re.sub(r"\\[a-zA-Z]+\*?(?:\[[^\]]*\])?(?:\{[^}]*\})?", " ", text)
    text = re.sub(r"[{}]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_abstract_body(text: str) -> str:
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped in {"\\clearpage", "\\newpage", "\\pagebreak"}:
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines).strip()


def build_abstract_rule_suggestions(selected_label: str, source_text: str) -> list[dict]:
    profile = detect_review_profile(selected_label)
    if profile == "general":
        return []

    body_text, keyword_line = _split_body_and_keywords(source_text)
    body_text = _normalize_abstract_body(body_text)
    cleaned_body = _strip_latex_commands(body_text)
    body_paragraphs = [chunk.strip() for chunk in re.split(r"\n\s*\n", body_text) if chunk.strip()]
    words = cleaned_body.split()
    suggestions: list[dict] = []

    if len(body_paragraphs) != 1:
        suggestions.append(
            {
                "category": "abstract-paragraph",
                "title": f"{selected_label} harus satu alinea",
                "detail": (
                    f"Saat ini terdeteksi {len(body_paragraphs)} blok paragraf. Panduan kampus meminta abstrak atau abstract ditulis dalam satu alinea."
                ),
                "paragraph_index": 1,
                "priority": "high",
                "suggested_revision": "Gabungkan isi abstrak menjadi satu paragraf utuh tanpa pemisahan alinea tambahan.",
                "source": "campus-guideline",
            }
        )

    if len(words) > 200:
        suggestions.append(
            {
                "category": "abstract-length",
                "title": f"{selected_label} melebihi batas 200 kata",
                "detail": (
                    f"Terdeteksi sekitar {len(words)} kata pada isi abstrak. Panduan kampus membatasi maksimal 200 kata."
                ),
                "paragraph_index": 1,
                "priority": "high",
                "suggested_revision": "Ringkas kalimat yang terlalu rinci dan sisakan inti masalah, tujuan, metode, hasil, dan kesimpulan.",
                "source": "campus-guideline",
            }
        )

    if any(command in body_text for command in CITATION_COMMANDS):
        suggestions.append(
            {
                "category": "abstract-citation",
                "title": f"{selected_label} tidak boleh memuat sitasi",
                "detail": "Panduan kampus menyatakan abstrak tidak boleh berisi sitasi atau rujukan bibliografi.",
                "paragraph_index": 1,
                "priority": "high",
                "suggested_revision": "Hapus sitasi dari abstrak dan ubah menjadi pernyataan umum yang tetap informatif tanpa rujukan langsung.",
                "source": "campus-guideline",
            }
        )

    if "\\texttt{" in body_text or re.search(r"[$_=<>]", body_text):
        suggestions.append(
            {
                "category": "abstract-technical-term",
                "title": f"{selected_label} memuat notasi atau identifier teknis",
                "detail": (
                    "Terdeteksi penulisan yang cenderung teknis seperti identifier atau notasi khusus. Panduan kampus meminta abstrak menghindari simbol atau istilah teknis yang tidak perlu."
                ),
                "paragraph_index": 1,
                "priority": "medium",
                "suggested_revision": "Ganti identifier atau notasi teknis dengan penjelasan yang lebih umum jika tidak wajib ditampilkan di abstrak.",
                "source": "campus-guideline",
            }
        )

    if keyword_line:
        cleaned_keyword_line = _strip_latex_commands(keyword_line)
        _, _, keyword_text = cleaned_keyword_line.partition(":")
        keywords = [item.strip() for item in keyword_text.split(",") if item.strip()]

        if len(keywords) > 6:
            suggestions.append(
                {
                    "category": "abstract-keywords",
                    "title": "Jumlah kata kunci melebihi batas",
                    "detail": f"Terdeteksi {len(keywords)} kata kunci, sedangkan panduan kampus membatasi maksimal 6.",
                    "paragraph_index": 1,
                    "priority": "medium",
                    "suggested_revision": "Pilih maksimal 6 kata kunci yang paling mewakili isi penelitian.",
                    "source": "campus-guideline",
                }
            )

        lowercase_violations = [item for item in keywords if item != item.lower() and not item.isupper()]
        if lowercase_violations:
            suggestions.append(
                {
                    "category": "abstract-keyword-case",
                    "title": "Penulisan kata kunci belum konsisten huruf kecil",
                    "detail": (
                        "Panduan kampus meminta kata kunci ditulis huruf kecil, kecuali singkatan. "
                        f"Contoh yang perlu dicek: {', '.join(lowercase_violations[:3])}."
                    ),
                    "paragraph_index": 1,
                    "priority": "low",
                    "suggested_revision": "Ubah kata kunci menjadi huruf kecil, kecuali jika memang berupa singkatan baku.",
                    "source": "campus-guideline",
                }
            )
    else:
        suggestions.append(
            {
                "category": "abstract-keywords-missing",
                "title": "Baris kata kunci belum terdeteksi",
                "detail": "Panduan kampus meminta abstrak disertai kata kunci atau keywords maksimal 6 item.",
                "paragraph_index": 1,
                "priority": "medium",
                "suggested_revision": "Tambahkan baris kata kunci yang ringkas dan relevan dengan isi penelitian.",
                "source": "campus-guideline",
            }
        )

    return suggestions
