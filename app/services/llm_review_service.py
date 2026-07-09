from __future__ import annotations

import json
import os
from typing import Iterable

from openai import OpenAI

DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "cohere/north-mini-code:free")
DEFAULT_APP_URL = os.getenv("OPENROUTER_APP_URL", "https://localhost")
DEFAULT_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "Thesis Atelier")


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


def build_llm_suggestions(paragraphs: Iterable[str], user_goal: str, section_label: str) -> tuple[list[dict], str]:
    available, reason = llm_review_available()
    if not available:
        raise RuntimeError(reason)

    joined = "\n\n".join(f"Paragraf {index + 1}: {paragraph}" for index, paragraph in enumerate(paragraphs))
    prompt = f"""
Kamu adalah reviewer akademik untuk skripsi berbahasa Indonesia.

Bagian yang direview: {section_label}
Tujuan user: {user_goal}

Teks:
{joined}

Tugas:
1. Beri ringkasan singkat kualitas bagian ini.
2. Beri daftar saran revisi dalam JSON valid.

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
    payload = _extract_json_payload(response.choices[0].message.content or "")
    suggestions = payload.get("suggestions") or []
    summary = str(payload.get("summary") or f"Review LLM selesai dengan {len(suggestions)} saran.")
    normalized: list[dict] = []
    for item in suggestions:
        if not isinstance(item, dict):
            continue
        normalized.append({
            "issue": str(item.get("issue", "")),
            "suggestion": str(item.get("suggestion", "")),
            "severity": str(item.get("severity", "medium")),
            "excerpt": str(item.get("excerpt", "")),
        })
    return normalized, summary
