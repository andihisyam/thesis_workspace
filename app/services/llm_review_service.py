from __future__ import annotations

import json
import logging
import os
from typing import Iterable

from openai import OpenAI

from app.services.review_service import build_rule_based_suggestions

DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "cohere/north-mini-code:free")
DEFAULT_APP_URL = os.getenv("OPENROUTER_APP_URL", "https://localhost")
DEFAULT_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "Thesis Atelier")

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
        if not issue and not suggestion:
            continue
        normalized.append({
            "issue": issue or "Perlu perhatian lebih lanjut.",
            "suggestion": suggestion or "Periksa kembali bagian ini agar lebih sesuai dengan tujuan review.",
            "severity": severity,
            "excerpt": excerpt,
        })
    return normalized


def build_llm_suggestions(paragraphs: Iterable[str], user_goal: str, section_label: str) -> tuple[list[dict], str]:
    available, reason = llm_review_available()
    if not available:
        raise RuntimeError(reason)

    paragraph_list = list(paragraphs)
    joined = "\n\n".join(f"Paragraf {index + 1}: {paragraph}" for index, paragraph in enumerate(paragraph_list))
    prompt = f"""
Kamu adalah reviewer akademik untuk skripsi berbahasa Indonesia.

Bagian yang direview: {section_label}
Tujuan user: {user_goal}

Teks:
{joined}

Tugas:
1. Beri ringkasan singkat kualitas bagian ini.
2. Beri minimal 3 saran revisi spesifik.
3. Kalau naskah sudah cukup baik, tetap beri saran minor yang realistis.
4. Jawab HANYA dalam JSON valid tanpa penjelasan tambahan di luar JSON.

Format JSON yang wajib:
{{
  "summary": "...",
  "suggestions": [
    {{
      "issue": "...",
      "suggestion": "...",
      "severity": "low|medium|high",
      "excerpt": "..."
    }}
  ]
}}
""".strip()

    client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=DEFAULT_BASE_URL)
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"HTTP-Referer": DEFAULT_APP_URL, "X-Title": DEFAULT_APP_NAME},
        temperature=0.2,
    )
    raw_content = response.choices[0].message.content or ""
    payload = _extract_json_payload(raw_content)
    suggestions = _candidate_suggestions(payload)
    normalized = _normalize_suggestions(suggestions)
    summary = str(payload.get("summary") or f"Review LLM selesai dengan {len(normalized)} saran.")

    if normalized:
        return normalized, summary

    logger.warning(
        "LLM review returned no structured suggestions for %s using model %s. Raw response: %s",
        section_label,
        DEFAULT_MODEL,
        raw_content[:1000],
    )
    fallback = build_rule_based_suggestions(paragraph_list, selected_label=section_label, source_text="\n\n".join(paragraph_list))
    if fallback:
        return fallback, f"Review LLM tidak memberi saran terstruktur, jadi sistem memakai fallback lokal untuk {section_label}."
    raise RuntimeError("LLM returned no structured suggestions")
