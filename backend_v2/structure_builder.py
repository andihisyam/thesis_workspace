import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend_v2.models import (
    CitationOccurrence,
    DocumentPage,
    DocumentUnit,
    DraftVersion,
    RevisionDraft,
    ReviewRun,
    SourceDocument,
)


CHAPTER_RE = re.compile(r"^\s*(?:BAB|CHAPTER)\s+([IVXLCDM]+|\d+)\s*[:.\-]?\s*(.+?)?\s*$", re.IGNORECASE)
NUMBERED_RE = re.compile(r"^\s*(\d+(?:\.\d+){1,3})\s+(.+?)\s*$")
LEADER_RE = re.compile(r"\s+\.{2,}\s*\d+\s*$")
PAGE_SUFFIX_RE = re.compile(r"\s+\d+\s*$")


@dataclass
class OutlineItem:
    level: str
    number: str
    title: str
    start_page: int = 1
    confidence: float = 0.7


def normalize_text(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _level_for_number(number: str) -> str:
    depth = number.count(".")
    if depth == 0:
        return "CHAPTER"
    if depth == 1:
        return "SUBCHAPTER"
    return "SUBSUBCHAPTER"


def parse_toc_outline(content: str) -> list[OutlineItem]:
    items: list[OutlineItem] = []
    for raw_line in content.splitlines():
        line = " ".join(raw_line.strip().split())
        if not line:
            continue
        line = LEADER_RE.sub("", line)
        chapter_match = CHAPTER_RE.match(line)
        if chapter_match:
            number = chapter_match.group(1).upper()
            title = (chapter_match.group(2) or f"Bab {number}").strip()
            items.append(OutlineItem(level="CHAPTER", number=number, title=title, confidence=0.95))
            continue
        numbered_match = NUMBERED_RE.match(line)
        if numbered_match:
            number, title = numbered_match.groups()
            title = PAGE_SUFFIX_RE.sub("", title).strip()
            items.append(OutlineItem(level=_level_for_number(number), number=number, title=title, confidence=0.9))
    return items


def _find_page_for_item(pages: list[DocumentPage], item: OutlineItem, after_page: int) -> int:
    title_key = normalize_text(item.title)
    number_key = normalize_text(item.number)
    best_page = 0
    best_score = 0
    for page in pages:
        if page.page_number < after_page:
            continue
        text_key = normalize_text(page.text[:2500])
        score = 0
        if title_key and title_key in text_key:
            score += 4
        if number_key and re.search(rf"\b{re.escape(number_key)}\b", text_key):
            score += 2
        if item.level == "CHAPTER" and normalize_text(f"bab {item.number}") in text_key:
            score += 3
        if score > best_score:
            best_score = score
            best_page = page.page_number
    if best_page:
        item.confidence = min(1.0, item.confidence + 0.05)
        return best_page
    item.confidence = 0.45
    return after_page


def apply_toc_structure(db: Session, document: SourceDocument, toc_content: str) -> list[DocumentUnit]:
    outline = parse_toc_outline(toc_content)
    if not outline:
        raise ValueError("Daftar isi belum terbaca. Pastikan ada baris seperti BAB I atau 1.1 Judul Sub Bab.")

    pages = list(
        db.scalars(
            select(DocumentPage)
            .where(DocumentPage.document_id == document.id)
            .order_by(DocumentPage.page_number)
        )
    )
    if not pages:
        raise ValueError("Teks PDF belum tersedia. Upload dan tunggu ekstraksi PDF selesai terlebih dahulu.")

    previous_page = 1
    for item in outline:
        item.start_page = _find_page_for_item(pages, item, previous_page)
        previous_page = item.start_page

    unit_ids = list(
        db.scalars(select(DocumentUnit.id).where(DocumentUnit.document_id == document.id))
    )
    draft_ids = list(
        db.scalars(select(RevisionDraft.id).where(RevisionDraft.unit_id.in_(unit_ids)))
    ) if unit_ids else []
    if draft_ids:
        db.execute(delete(DraftVersion).where(DraftVersion.draft_id.in_(draft_ids)))
        db.execute(delete(RevisionDraft).where(RevisionDraft.id.in_(draft_ids)))
    if unit_ids:
        db.execute(delete(ReviewRun).where(ReviewRun.unit_id.in_(unit_ids)))
        db.execute(delete(CitationOccurrence).where(CitationOccurrence.unit_id.in_(unit_ids)))
        db.execute(delete(DocumentUnit).where(DocumentUnit.id.in_(unit_ids)))

    page_lookup = {page.page_number: page.text for page in pages}
    units: list[DocumentUnit] = []
    latest_chapter: DocumentUnit | None = None
    latest_subchapter: DocumentUnit | None = None
    max_page = max(page.page_number for page in pages)

    for index, item in enumerate(outline):
        next_start = outline[index + 1].start_page if index + 1 < len(outline) else max_page + 1
        end_page = max(item.start_page, min(max_page, next_start - 1))
        content = "\n\n".join(
            page_lookup.get(page_number, "") for page_number in range(item.start_page, end_page + 1)
        ).strip()
        parent_id = None
        if item.level == "CHAPTER":
            latest_subchapter = None
        elif item.level == "SUBCHAPTER":
            parent_id = latest_chapter.id if latest_chapter else None
        else:
            parent_id = (latest_subchapter or latest_chapter).id if (latest_subchapter or latest_chapter) else None
        unit = DocumentUnit(
            project_id=document.project_id,
            document_id=document.id,
            parent_id=parent_id,
            level=item.level,
            number=item.number,
            title=item.title,
            content=content,
            start_page=item.start_page,
            end_page=end_page,
            sort_order=index,
            confidence=item.confidence,
        )
        db.add(unit)
        db.flush()
        units.append(unit)
        if item.level == "CHAPTER":
            latest_chapter = unit
        elif item.level == "SUBCHAPTER":
            latest_subchapter = unit

    document.structure_confirmed = True
    document.status = "READY"
    db.commit()
    return units
