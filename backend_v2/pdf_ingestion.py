import re
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from backend_v2.models import DocumentPage, DocumentUnit, SourceDocument


CHAPTER_PATTERN = re.compile(r"^\s*BAB\s+([IVXLCDM]+|\d+)\s*[:.-]?\s*(.*)$", re.IGNORECASE)
NUMBERED_PATTERN = re.compile(r"^\s*(\d+(?:\.\d+){1,3})\s+(.{3,180})$")


def _level_for_number(number: str) -> str:
    depth = number.count(".")
    return {1: "SUBCHAPTER", 2: "SUBSUBCHAPTER", 3: "SUBSUBCHAPTER"}.get(depth, "SUBCHAPTER")


def extract_pdf(db: Session, document: SourceDocument, pdf_path: Path) -> list[DocumentUnit]:
    try:
        import fitz
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyMuPDF belum terpasang.") from exc

    db.execute(delete(DocumentPage).where(DocumentPage.document_id == document.id))
    db.execute(delete(DocumentUnit).where(DocumentUnit.document_id == document.id))
    pdf = fitz.open(pdf_path)
    pages: list[tuple[int, str]] = []
    for page_index, page in enumerate(pdf, start=1):
        text = page.get_text("text").strip()
        method = "text" if text else "ocr-required"
        db.add(
            DocumentPage(
                document_id=document.id,
                page_number=page_index,
                text=text,
                extraction_method=method,
            )
        )
        pages.append((page_index, text))

    detected: list[dict] = []
    for page_number, page_text in pages:
        for line in page_text.splitlines():
            normalized = " ".join(line.split())
            chapter_match = CHAPTER_PATTERN.match(normalized)
            if chapter_match:
                number = chapter_match.group(1)
                title = chapter_match.group(2).strip() or f"Bab {number}"
                detected.append(
                    {"level": "CHAPTER", "number": number, "title": title, "page": page_number, "confidence": 0.92}
                )
                continue

    if not detected:
        detected.append(
            {"level": "CHAPTER", "number": "1", "title": "Dokumen", "page": 1, "confidence": 0.25}
        )

    if detected[0]["page"] > 1:
        detected.insert(
            0,
            {"level": "FRONTMATTER", "number": "", "title": "Bagian Awal", "page": 1, "confidence": 0.7},
        )

    page_lookup = {number: text for number, text in pages}
    units: list[DocumentUnit] = []
    latest_chapter: DocumentUnit | None = None
    latest_subchapter: DocumentUnit | None = None
    for index, item in enumerate(detected):
        end_page = detected[index + 1]["page"] if index + 1 < len(detected) else len(pages)
        if index + 1 < len(detected) and end_page > item["page"]:
            end_page -= 1
        content = "\n\n".join(page_lookup.get(page, "") for page in range(item["page"], end_page + 1)).strip()
        parent_id = None
        if item["level"] == "CHAPTER":
            latest_subchapter = None
        elif item["level"] == "SUBCHAPTER":
            parent_id = latest_chapter.id if latest_chapter else None
        elif item["level"] == "SUBSUBCHAPTER":
            parent_id = (latest_subchapter or latest_chapter).id if (latest_subchapter or latest_chapter) else None
        unit = DocumentUnit(
            project_id=document.project_id,
            document_id=document.id,
            parent_id=parent_id,
            level=item["level"],
            number=item["number"],
            title=item["title"],
            content=content,
            start_page=item["page"],
            end_page=end_page,
            sort_order=index,
            confidence=item["confidence"],
        )
        db.add(unit)
        db.flush()
        units.append(unit)
        if item["level"] == "CHAPTER":
            latest_chapter = unit
        elif item["level"] == "SUBCHAPTER":
            latest_subchapter = unit

    document.page_count = len(pages)
    document.structure_confirmed = True
    document.status = "READY"
    db.commit()
    return units


