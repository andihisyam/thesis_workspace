from __future__ import annotations

import re
from typing import Iterable


INFORMAL_REPLACEMENTS = {
    "aku": "saya",
    "kamu": "peneliti",
    "nggak": "tidak",
    "gak": "tidak",
    "banget": "sangat",
}


def split_paragraphs(text: str) -> list[str]:
    if not text:
        return []
    parts = [chunk.strip() for chunk in re.split(r"\n\s*\n+", text) if chunk.strip()]
    if parts:
        return parts
    return [line.strip() for line in text.splitlines() if line.strip()]


def _make_suggestion(
    paragraph: str,
    issue: str,
    suggestion: str,
    severity: str = "medium",
    *,
    replacement: str = "",
    reason: str = "",
) -> dict:
    return {
        "issue": issue,
        "suggestion": suggestion,
        "severity": severity,
        "excerpt": paragraph[:300],
        "replacement": replacement.strip(),
        "reason": reason.strip() or suggestion,
    }


def _replace_informal_terms(text: str) -> str:
    result = text
    for source, target in INFORMAL_REPLACEMENTS.items():
        result = re.sub(rf"\b{re.escape(source)}\b", target, result, flags=re.IGNORECASE)
    return result


def build_rule_based_suggestions(paragraphs: Iterable[str], selected_label: str = "", source_text: str = "") -> list[dict]:
    suggestions: list[dict] = []
    for paragraph in paragraphs:
        clean = " ".join(paragraph.split())
        if len(clean.split()) > 70:
            suggestions.append(_make_suggestion(
                clean,
                "Kalimat atau paragraf terlalu panjang.",
                "Pecah paragraf menjadi dua atau lebih kalimat agar argumennya lebih mudah diikuti.",
                "medium",
                reason="Paragraf yang terlalu panjang membuat pembaca sulit menangkap inti argumen dan hubungan antargagasan.",
            ))
        if clean and clean[0].islower():
            suggestions.append(_make_suggestion(
                clean,
                "Awal paragraf tidak diawali huruf kapital.",
                "Awali kalimat pertama dengan huruf kapital agar sesuai kaidah penulisan akademik.",
                "low",
                replacement=clean[0].upper() + clean[1:],
                reason="Awal paragraf yang benar membantu konsistensi format dan keterbacaan naskah.",
            ))
        if clean.endswith("?"):
            suggestions.append(_make_suggestion(
                clean,
                "Gaya kalimat berupa pertanyaan kurang umum untuk naskah akademik formal.",
                "Ubah kalimat tanya menjadi kalimat pernyataan yang lebih tegas.",
                "low",
                replacement=clean.rstrip("?").rstrip() + ".",
                reason="Kalimat pernyataan biasanya lebih cocok untuk menjelaskan temuan, definisi, atau argumentasi ilmiah.",
            ))
        if re.search(r"\b(aku|kamu|nggak|gak|banget)\b", clean, flags=re.IGNORECASE):
            suggestions.append(_make_suggestion(
                clean,
                "Terdapat gaya bahasa yang terlalu informal.",
                "Ganti diksi informal dengan istilah akademik yang lebih netral dan objektif.",
                "medium",
                replacement=_replace_informal_terms(clean),
                reason="Diksi yang formal membuat tulisan lebih layak untuk konteks skripsi atau laporan ilmiah.",
            ))
        if re.search(r"\betc\.?\b", clean, flags=re.IGNORECASE):
            suggestions.append(_make_suggestion(
                clean,
                "Penggunaan singkatan asing seperti etc. kurang tepat dalam naskah formal.",
                "Gunakan padanan yang lebih formal dalam bahasa Indonesia.",
                "low",
                replacement=re.sub(r"\betc\.?\b", "dan lain-lain", clean, flags=re.IGNORECASE),
                reason="Padanan bahasa Indonesia yang jelas lebih sesuai untuk naskah akademik berbahasa Indonesia.",
            ))
    if not suggestions and source_text.strip():
        suggestions.append(_make_suggestion(
            source_text.strip(),
            f"Bagian {selected_label or 'ini'} sudah cukup rapi secara aturan dasar.",
            "Lanjutkan pemeriksaan manual untuk kedalaman argumen, sitasi, dan konsistensi istilah.",
            "info",
            reason="Secara mekanis bagian ini cukup baik, tetapi validitas akademiknya tetap perlu dicek manual.",
        ))
    return suggestions
