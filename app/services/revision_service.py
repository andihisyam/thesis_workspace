import json
import os
from typing import Any

from dotenv import load_dotenv

from app.models.state import Suggestion
from app.services.latex_revision_sanitizer import sanitize_revision_latex
from app.services.llm_review_service import DEFAULT_APP_NAME, DEFAULT_APP_URL, DEFAULT_BASE_URL, DEFAULT_MODEL, OpenAI, _extract_json_payload, llm_review_available


load_dotenv()


def build_revision_draft(
    source_text: str,
    suggestions: list[Suggestion],
    context_label: str,
    user_goal: str,
) -> tuple[str, str]:
    available, reason = llm_review_available()
    if not available:
        raise RuntimeError(reason)

    client = OpenAI(
        api_key=os.getenv("OPENROUTER_API_KEY"),
        base_url=DEFAULT_BASE_URL,
    )

    compact_suggestions = []
    for item in suggestions[:6]:
        compact_suggestions.append(
            {
                "title": item.get("title", "Saran revisi"),
                "detail": item.get("detail", ""),
                "paragraph_index": item.get("paragraph_index", 0),
                "suggested_revision": item.get("suggested_revision", ""),
                "priority": item.get("priority", "medium"),
            }
        )

    prompt = f"""
Kamu adalah editor akademik untuk skripsi berbahasa Indonesia.
Tugasmu membuat draft revisi terkontrol untuk satu bagian dokumen LaTeX.

Bagian yang sedang direvisi:
{context_label}

Tujuan user:
{user_goal}

Aturan penting:
- Pertahankan format LaTeX yang sudah ada selama masih relevan.
- Jangan menghapus sitasi, label, atau environment LaTeX yang masih diperlukan.
- Perbaiki hanya isi bagian ini, bukan seluruh dokumen lain.
- Gunakan bahasa akademik Indonesia yang lebih rapi, jelas, dan formal.
- Jika ada kalimat yang lemah, rapikan tanpa mengubah makna inti secara liar.
- Hindari markdown seperti **bold** atau bullet markdown biasa; gunakan sintaks LaTeX jika memang perlu.
- Escape karakter khusus LaTeX yang muncul sebagai teks biasa, terutama &, %, dan _ bila bukan bagian command.
- Kembalikan hanya JSON valid dengan bentuk:
{{
  "summary": "ringkasan revisi",
  "revised_latex": "isi LaTeX hasil revisi"
}}

Saran review yang perlu dipertimbangkan:
{json.dumps(compact_suggestions, ensure_ascii=False, indent=2)}

Isi LaTeX asli yang direvisi:
{source_text}
""".strip()

    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={
            "HTTP-Referer": DEFAULT_APP_URL,
            "X-Title": DEFAULT_APP_NAME,
        },
        temperature=0.2,
    )

    content = response.choices[0].message.content or ""
    payload = _extract_json_payload(content)
    revised_text = sanitize_revision_latex(payload.get("revised_latex", "").strip())
    summary = payload.get("summary", "Draft revisi berhasil dibuat.")

    if not revised_text:
        raise ValueError("Model tidak mengembalikan isi revisi.")

    return revised_text, summary
