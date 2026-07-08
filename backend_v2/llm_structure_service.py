import json
import os
import re

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.services.llm_review_service import (
    DEFAULT_APP_NAME,
    DEFAULT_APP_URL,
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    OpenAI,
    _extract_json_payload,
    llm_review_available,
)
from backend_v2.models import (
    CitationOccurrence,
    DocumentPage,
    DocumentUnit,
    DraftVersion,
    RevisionDraft,
    ReviewRun,
)


def _page_blocks(pages: list[DocumentPage], max_chars_per_page: int = 2200) -> str:
    blocks = []
    for page in pages:
        text = " ".join(page.text.split())[:max_chars_per_page]
        if text:
            blocks.append(f"HALAMAN {page.page_number}\n{text}")
    return "\n\n".join(blocks)


def _normalize_level(value: str, number: str) -> str:
    candidate = value.upper().replace(" ", "")
    if candidate in {"SUBSUBCHAPTER", "SUBSUBBAB"}:
        return "SUBSUBCHAPTER"
    if candidate in {"SUBCHAPTER", "SUBBAB"}:
        return "SUBCHAPTER"
    return "SUBSUBCHAPTER" if number.count(".") >= 2 else "SUBCHAPTER"


def _fallback_detect_subchapters(chapter: DocumentUnit, pages: list[DocumentPage]) -> list[dict]:
    pattern = re.compile(r"^\s*(\d+(?:\.\d+){1,2})\s+(.{3,160})$")
    items: list[dict] = []
    for page in pages:
        for line in page.text.splitlines():
            normalized = " ".join(line.split())
            match = pattern.match(normalized)
            if not match:
                continue
            number, title = match.groups()
            if len(title.split()) > 18:
                continue
            items.append(
                {
                    "level": _normalize_level("", number),
                    "number": number,
                    "title": title.strip(),
                    "start_page": page.page_number,
                    "end_page": page.page_number,
                    "confidence": 0.55,
                }
            )
    return items


def detect_subchapters_for_chapter(chapter: DocumentUnit, pages: list[DocumentPage]) -> tuple[list[dict], str]:
    available, reason = llm_review_available()
    if not available:
        return _fallback_detect_subchapters(chapter, pages), f"fallback: {reason}"

    page_text = _page_blocks(pages)
    if not page_text:
        return [], "empty"

    prompt = f"""
Kamu adalah parser struktur skripsi berbahasa Indonesia.
Tugasmu hanya mendeteksi Sub Bab dan Sub Sub Bab dari isi satu BAB.

BAB yang dianalisis:
{chapter.number} {chapter.title}

Aturan:
- Jangan menulis ulang isi skripsi.
- Jangan mengarang sub bab yang tidak terlihat dari teks.
- Ambil heading yang tampak sebagai nomor seperti 2.1, 2.2, 2.2.1.
- Jika halaman awal/akhir tidak pasti, isi halaman tempat heading ditemukan.
- Kembalikan hanya JSON valid dengan bentuk:
{{
  "items": [
    {{
      "level": "SUBCHAPTER",
      "number": "2.1",
      "title": "Judul Sub Bab",
      "start_page": 10,
      "end_page": 12
    }},
    {{
      "level": "SUBSUBCHAPTER",
      "number": "2.1.1",
      "title": "Judul Sub Sub Bab",
      "start_page": 11,
      "end_page": 11
    }}
  ]
}}

Teks BAB per halaman:
{page_text}
""".strip()

    client = OpenAI(api_key=os.getenv("OPENROUTER_API_KEY"), base_url=DEFAULT_BASE_URL)
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        extra_headers={"HTTP-Referer": DEFAULT_APP_URL, "X-Title": DEFAULT_APP_NAME},
        temperature=0.1,
    )
    payload = _extract_json_payload(response.choices[0].message.content or "")
    items: list[dict] = []
    min_page = min(page.page_number for page in pages)
    max_page = max(page.page_number for page in pages)
    for raw in payload.get("items", []):
        number = str(raw.get("number", "")).strip()
        title = str(raw.get("title", "")).strip()
        if not number or not title:
            continue
        start_page = int(raw.get("start_page") or min_page)
        end_page = int(raw.get("end_page") or start_page)
        start_page = max(min_page, min(max_page, start_page))
        end_page = max(start_page, min(max_page, end_page))
        items.append(
            {
                "level": _normalize_level(str(raw.get("level", "")), number),
                "number": number,
                "title": title,
                "start_page": start_page,
                "end_page": end_page,
                "confidence": 0.86,
            }
        )
    return items, "openrouter"


def replace_chapter_children_with_detected(
    db: Session,
    chapter: DocumentUnit,
    items: list[dict],
    source: str,
) -> list[DocumentUnit]:
    child_ids = list(db.scalars(select(DocumentUnit.id).where(DocumentUnit.parent_id == chapter.id)))
    grandchild_ids = (
        list(db.scalars(select(DocumentUnit.id).where(DocumentUnit.parent_id.in_(child_ids)))) if child_ids else []
    )
    removed_ids = child_ids + grandchild_ids
    if removed_ids:
        draft_ids = list(db.scalars(select(RevisionDraft.id).where(RevisionDraft.unit_id.in_(removed_ids))))
        if draft_ids:
            db.execute(delete(DraftVersion).where(DraftVersion.draft_id.in_(draft_ids)))
            db.execute(delete(RevisionDraft).where(RevisionDraft.id.in_(draft_ids)))
        db.execute(delete(ReviewRun).where(ReviewRun.unit_id.in_(removed_ids)))
        db.execute(delete(CitationOccurrence).where(CitationOccurrence.unit_id.in_(removed_ids)))
        db.execute(delete(DocumentUnit).where(DocumentUnit.id.in_(removed_ids)))
        db.flush()

    pages = list(
        db.scalars(
            select(DocumentPage)
            .where(
                DocumentPage.document_id == chapter.document_id,
                DocumentPage.page_number >= chapter.start_page,
                DocumentPage.page_number <= chapter.end_page,
            )
            .order_by(DocumentPage.page_number)
        )
    )
    page_lookup = {page.page_number: page.text for page in pages}
    siblings = list(
        db.scalars(
            select(DocumentUnit)
            .where(DocumentUnit.document_id == chapter.document_id, DocumentUnit.id != chapter.id)
            .order_by(DocumentUnit.sort_order)
        )
    )
    base_order = chapter.sort_order + 1
    for sibling in siblings:
        if sibling.sort_order > chapter.sort_order:
            sibling.sort_order += len(items)

    created: list[DocumentUnit] = []
    latest_subchapter: DocumentUnit | None = None
    for offset, item in enumerate(items):
        parent_id = chapter.id
        if item["level"] == "SUBSUBCHAPTER":
            parent_id = latest_subchapter.id if latest_subchapter else chapter.id
        content = "\n\n".join(
            page_lookup.get(page, "") for page in range(item["start_page"], item["end_page"] + 1)
        ).strip()
        unit = DocumentUnit(
            project_id=chapter.project_id,
            document_id=chapter.document_id,
            parent_id=parent_id,
            level=item["level"],
            number=item["number"],
            title=item["title"],
            content=content,
            start_page=item["start_page"],
            end_page=item["end_page"],
            sort_order=base_order + offset,
            confidence=item.get("confidence", 0.8),
        )
        db.add(unit)
        db.flush()
        created.append(unit)
        if unit.level == "SUBCHAPTER":
            latest_subchapter = unit

    db.commit()
    return created
