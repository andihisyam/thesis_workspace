from __future__ import annotations

import re
from typing import Iterable


def split_paragraphs(text: str) -> list[str]:
    if not text:
        return []
    parts = [chunk.strip() for chunk in re.split(r"\n\s*\n+", text) if chunk.strip()]
    if parts:
        return parts
    return [line.strip() for line in text.splitlines() if line.strip()]


def _make_suggestion(paragraph: str, issue: str, suggestion: str, severity: str = "medium") -> dict:
    return {
        "issue": issue,
        "suggestion": suggestion,
        "severity": severity,
        "excerpt": paragraph[:300],
    }


def build_rule_based_suggestions(paragraphs: Iterable[str], selected_label: str = "", source_text: str = "") -> list[dict]:
    suggestions: list[dict] = []
    for paragraph in paragraphs:
        clean = " ".join(paragraph.split())
        if len(clean.split()) > 70:
            suggestions.append(_make_suggestion(clean, "Kalimat atau paragraf terlalu panjang.", "Pecah paragraf menjadi bagian yang lebih ringkas agar lebih mudah dibaca.", "medium"))
        if clean and clean[0].islower():
            suggestions.append(_make_suggestion(clean, "Awal paragraf tidak diawali huruf kapital.", "Periksa kembali awal kalimat atau paragraf agar sesuai kaidah penulisan akademik.", "low"))
        if clean.endswith("?"):
            suggestions.append(_make_suggestion(clean, "Gaya kalimat berupa pertanyaan kurang umum untuk naskah akademik formal.", "Pertimbangkan mengubah kalimat tanya menjadi kalimat pernyataan yang lebih formal.", "low"))
        if re.search(r"\b(aku|kamu|nggak|gak|banget)\b", clean, flags=re.IGNORECASE):
            suggestions.append(_make_suggestion(clean, "Terdapat gaya bahasa yang terlalu informal.", "Ganti dengan bahasa akademik yang lebih formal dan objektif.", "medium"))
        if re.search(r"\betc\.?\b", clean, flags=re.IGNORECASE):
            suggestions.append(_make_suggestion(clean, "Penggunaan singkatan asing seperti etc. kurang tepat dalam naskah formal.", "Ganti dengan padanan yang lebih formal, misalnya 'dan lain-lain'.", "low"))
    if not suggestions and source_text.strip():
        suggestions.append(_make_suggestion(source_text.strip(), f"Bagian {selected_label or 'ini'} sudah cukup rapi secara aturan dasar.", "Lanjutkan pemeriksaan manual untuk kedalaman argumen, sitasi, dan konsistensi istilah.", "info"))
    return suggestions
