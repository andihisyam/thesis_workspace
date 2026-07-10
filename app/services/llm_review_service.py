from __future__ import annotations

import json
import logging
import os
import re
from typing import Iterable

from openai import OpenAI

from app.services.review_service import build_rule_based_suggestions

DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "cohere/north-mini-code:free")
DEFAULT_APP_URL = os.getenv("OPENROUTER_APP_URL", "https://localhost")
DEFAULT_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "Thesis Atelier")
ENGLISH_MARKERS = {
    "according",
    "based",
    "can",
    "constructed",
    "data",
    "effective",
    "enables",
    "ensure",
    "finance",
    "health",
    "how",
    "in",
    "includes",
    "industry",
    "is",
    "it",
    "methodology",
    "more",
    "previous",
    "result",
    "section",
    "studies",
    "study",
    "such",
    "that",
    "the",
    "this",
    "to",
    "using",
    "various",
    "widely",
    "without",
}
ALLOWED_TECHNICAL_TERMS = {
    "baseline",
    "boosting",
    "ehr",
    "grid",
    "knn",
    "learning",
    "lightgbm",
    "logistic",
    "machine",
    "optuna",
    "random",
    "regression",
    "search",
    "svm",
    "t2dm",
    "xgboost",
}

logger = logging.getLogger(__name__)


def llm_review_available() -> tuple[bool, str]:
    if not os.getenv("OPENROUTER_API_KEY"):
        return False, "OPENROUTER_API_KEY belum diisi"
    return True, "ok"


def _extract_json_payload(content: str) -> dict:
    if not content:
        return {}
    content = content.strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    start = content.find("{")
    end = content.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(content[start:end + 1])
        except json.JSONDecodeError:
            return {}
    return {}


def _candidate_suggestions(payload: dict) -> list:
    for key in ("suggestions", "issues", "recommendations", "findings"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _normalize_suggestions(items: list) -> list[dict]:
    normalized: list[dict] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        issue = str(item.get("issue") or item.get("title") or item.get("problem") or "").strip()
        suggestion = str(item.get("suggestion") or item.get("detail") or item.get("recommendation") or item.get("action") or "").strip()
        severity = str(item.get("severity") or item.get("priority") or "medium").strip() or "medium"
        excerpt = str(item.get("excerpt") or item.get("evidence") or item.get("example") or "").strip()
        replacement = str(item.get("replacement") or item.get("revision") or item.get("proposed_text") or item.get("rewrite") or "").strip()
        reason = str(item.get("reason") or item.get("why") or item.get("rationale") or "").strip()
        if not issue and not suggestion and not replacement:
            continue
        normalized.append({
            "issue": issue or "Perlu perhatian lebih lanjut.",
            "suggestion": suggestion or "Periksa kembali bagian ini agar lebih sesuai dengan tujuan review.",
            "severity": severity,
            "excerpt": excerpt,
            "replacement": replacement,
            "reason": reason or suggestion or "Perlu penyesuaian agar lebih akademik dan jelas.",
        })
    return normalized


def _word_tokens(text: str) -> list[str]:
    return re.findall(r"[a-zA-Z][a-zA-Z\-']+", text.lower())


def _looks_english_text(text: str) -> bool:
    tokens = [token for token in _word_tokens(text) if token not in ALLOWED_TECHNICAL_TERMS]
    if len(tokens) < 4:
        return False
    marker_hits = sum(1 for token in tokens if token in ENGLISH_MARKERS)
    return marker_hits >= 2 and marker_hits >= max(2, len(tokens) // 5)


def _has_english_replacements(suggestions: list[dict]) -> bool:
    for item in suggestions:
        replacement = str(item.get("replacement") or "").strip()
        if replacement and _looks_english_text(replacement):
            return True
    return False


def _build_prompt(joined: str, user_goal: str, section_label: str, *, retry_for_indonesian: bool = False) -> str:
    extra_rule = ""
    if retry_for_indonesian:
        extra_rule = "\n9. Jawaban sebelumnya gagal karena replacement masih berbahasa Inggris. Ulangi dan pastikan SELURUH replacement, suggestion, summary, dan reason memakai bahasa Indonesia akademik formal."
    return f"""
Kamu adalah reviewer akademik untuk skripsi berbahasa Indonesia.

Bagian yang direview: {section_label}
Tujuan user: {user_goal}

Teks:
{joined}

Aturan bahasa:
- Semua output WAJIB ditulis dalam bahasa Indonesia akademik formal.
- Field summary, suggestion, replacement, dan reason wajib berbahasa Indonesia.
- Jangan menulis usulan revisi dalam bahasa Inggris.
- Istilah teknis seperti machine learning, baseline, boosting, grid search, atau EHR boleh dipertahankan hanya sebagai istilah, tetapi struktur kalimat utama tetap harus bahasa Indonesia.
- Jika ada kesalahan ejaan bahasa Indonesia, perbaiki ke bentuk bahasa Indonesia yang benar, bukan diterjemahkan ke bahasa Inggris.

Tugas:
1. Bertindak sebagai reviewer, bukan penulis ulang penuh.
2. Temukan bagian yang memang perlu diperbaiki, terutama kalimat yang terlalu panjang, ambigu, informal, atau kurang akademik.
3. Untuk setiap temuan, sebisa mungkin kutip bagian aslinya secara spesifik pada field excerpt.
4. Jika memungkinkan, beri usulan kalimat pengganti yang lebih baik pada field replacement, tetap dalam bahasa Indonesia akademik.
5. Jelaskan alasan revisi pada field reason.
6. Jangan menulis ulang seluruh bagian. Fokus pada saran per kalimat atau per frasa.
7. Beri 10 sampai 20 saran yang paling bernilai. Jika teks sudah cukup baik, tetap beri saran minor yang realistis.
8. Jawab HANYA dalam JSON valid tanpa penjelasan tambahan di luar JSON.{extra_rule}

Format JSON yang wajib:
{{
  "summary": "...",
  "suggestions": [
    {{
      "issue": "...",
      "suggestion": "...",
      "severity": "low|medium|high",
      "excerpt": "kutipan bagian asli yang perlu diperbaiki",
      "replacement": "usulan pengganti dalam bahasa Indonesia akademik",
      "reason": "alasan kenapa bagian itu sebaiknya direvisi"
    }}
  ]
}}
""".strip()


def _run_completion(client: OpenAI, prompt: str) -> str:
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"HTTP-Referer": DEFAULT_APP_URL, "X-Title": DEFAULT_APP_NAME},
        temperature=0.2,
    )
    return response.choices[0].message.content or ""


def build_llm_suggestions(paragraphs: Iterable[str], user_goal: str, section_label: str) -> tuple[list[dict], str]:
    available, reason = llm_review_available()
    if not available:
        raise RuntimeError(reason)

    paragraph_list = list(paragraphs)
    joined = "\n\n".join(f"Paragraf {index + 1}: {paragraph}" for index, paragraph in enumerate(paragraph_list))
    client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=DEFAULT_BASE_URL)

    raw_content = _run_completion(client, _build_prompt(joined, user_goal, section_label))
    payload = _extract_json_payload(raw_content)
    suggestions = _candidate_suggestions(payload)
    normalized = _normalize_suggestions(suggestions)
    summary = str(payload.get("summary") or f"Review LLM selesai dengan {len(normalized)} saran.")

    if normalized and _has_english_replacements(normalized):
        logger.info("LLM review for %s returned English replacements, retrying with stricter Indonesian constraint.", section_label)
        raw_content = _run_completion(client, _build_prompt(joined, user_goal, section_label, retry_for_indonesian=True))
        payload = _extract_json_payload(raw_content)
        suggestions = _candidate_suggestions(payload)
        normalized = _normalize_suggestions(suggestions)
        summary = str(payload.get("summary") or f"Review LLM selesai dengan {len(normalized)} saran.")

    if normalized and not _has_english_replacements(normalized):
        return normalized, summary

    logger.warning(
        "LLM review returned no valid Indonesian structured suggestions for %s using model %s. Raw response: %s",
        section_label,
        DEFAULT_MODEL,
        raw_content[:1000],
    )
    fallback = build_rule_based_suggestions(paragraph_list, selected_label=section_label, source_text="\n\n".join(paragraph_list))
    if fallback:
        return fallback, f"Review LLM tidak memberi saran terstruktur berbahasa Indonesia, jadi sistem memakai fallback lokal untuk {section_label}."
    raise RuntimeError("LLM returned no structured suggestions")
