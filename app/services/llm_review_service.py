import json
import os
from typing import Any

from dotenv import load_dotenv

from app.services.campus_guidelines import build_llm_review_guidance
from app.services.review_service import strip_latex_commands

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - depends on installed package
    OpenAI = None


load_dotenv()


DEFAULT_MODEL = os.getenv("OPENROUTER_MODEL", "cohere/north-mini-code:free")
DEFAULT_BASE_URL = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
DEFAULT_APP_URL = os.getenv("OPENROUTER_APP_URL", "http://localhost:8765")
DEFAULT_APP_NAME = os.getenv("OPENROUTER_APP_NAME", "Thesis Review Assistant")


def llm_review_available() -> tuple[bool, str]:
    if OpenAI is None:
        return False, "Package `openai` belum terinstall di environment ini."

    if not os.getenv("OPENROUTER_API_KEY"):
        return False, "OPENROUTER_API_KEY belum diisi, jadi sistem memakai fallback lokal."

    return True, f"Reviewer OpenRouter siap dipakai dengan model `{DEFAULT_MODEL}`."


def _extract_json_payload(raw_text: str) -> dict[str, Any]:
    content = raw_text.strip()
    if content.startswith("```"):
        parts = content.split("```")
        if len(parts) >= 3:
            content = parts[1]
            if content.startswith("json"):
                content = content[4:]
    start = content.find("{")
    end = content.rfind("}")
    if start == -1 or end == -1:
        raise ValueError("Reviewer tidak mengembalikan JSON yang valid.")
    return json.loads(content[start : end + 1])


def _build_prompt(paragraphs: list[str], user_goal: str, context_label: str, max_paragraphs: int = 12) -> str:
    selected = []
    for index, paragraph in enumerate(paragraphs[:max_paragraphs], start=1):
        cleaned = strip_latex_commands(paragraph)
        if cleaned:
            selected.append(f"Paragraf {index}: {cleaned}")

    joined_paragraphs = "\n\n".join(selected)
    extra_guidance = build_llm_review_guidance(context_label)
    extra_rules_block = f"\nAturan konteks khusus:\n{extra_guidance}\n" if extra_guidance else ""
    return f"""
Kamu adalah reviewer akademik untuk draft skripsi berbahasa Indonesia.
Tugasmu memberi masukan yang spesifik, tidak generik, dan fokus pada kualitas argumen.

Bagian yang sedang direview:
{context_label}

Fokus review dari user:
{user_goal}

{extra_rules_block}

Aturan:
- Jangan membahas hal yang sudah baik kecuali singkat di ringkasan.
- Beri maksimal 6 saran paling penting.
- Prioritaskan masalah yang benar-benar mempengaruhi kualitas akademik: koherensi, kejelasan argumen, kebutuhan sitasi, transisi antar gagasan, dan ketepatan gaya formal.
- Jika memberi saran, sebut nomor paragraf yang relevan terhadap bagian yang direview.
- Jika memungkinkan, beri contoh revisi singkat 1-2 kalimat, bukan menulis ulang seluruh bab.
- Jawab hanya dalam JSON valid dengan bentuk:
{{
  "summary": "...",
  "suggestions": [
    {{
      "category": "argument|clarity|citation|transition|formal-tone|structure",
      "title": "...",
      "detail": "...",
      "paragraph_index": 1,
      "priority": "high|medium|low",
      "suggested_revision": "..."
    }}
  ]
}}

Paragraf yang direview:
{joined_paragraphs}
""".strip()


def build_llm_suggestions(paragraphs: list[str], user_goal: str, context_label: str) -> tuple[list[dict], str]:
    available, reason = llm_review_available()
    if not available:
        raise RuntimeError(reason)

    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=DEFAULT_BASE_URL,
    )
    prompt = _build_prompt(paragraphs, user_goal=user_goal, context_label=context_label)
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        extra_headers={
            "HTTP-Referer": DEFAULT_APP_URL,
            "X-Title": DEFAULT_APP_NAME,
        },
        temperature=0.3,
    )

    content = response.choices[0].message.content or ""
    payload = _extract_json_payload(content)
    suggestions = payload.get("suggestions", [])
    normalized: list[dict] = []

    for suggestion in suggestions:
        normalized.append(
            {
                "category": suggestion.get("category", "clarity"),
                "title": suggestion.get("title", "Saran revisi"),
                "detail": suggestion.get("detail", "Tidak ada detail tambahan."),
                "paragraph_index": int(suggestion.get("paragraph_index", 0) or 0),
                "priority": suggestion.get("priority", "medium"),
                "suggested_revision": suggestion.get("suggested_revision", ""),
                "source": "openrouter",
            }
        )

    if not normalized:
        normalized.append(
            {
                "category": "healthy-draft",
                "title": "Model tidak menemukan masalah besar",
                "detail": "Draft terlihat cukup baik dari sampel paragraf yang direview.",
                "paragraph_index": 0,
                "priority": "low",
                "suggested_revision": "Tidak ada revisi mendesak dari reviewer ini.",
                "source": "openrouter",
            }
        )

    summary = payload.get("summary", "Review OpenRouter selesai tanpa ringkasan tambahan.")
    return normalized, summary
