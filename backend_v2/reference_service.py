import re
import unicodedata

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend_v2.models import CitationOccurrence, DocumentUnit, ReferenceRecord


BIB_ENTRY_PATTERN = re.compile(r"@(\w+)\s*\{\s*([^,]+),(.+?)\n\}", re.DOTALL)
BIB_FIELD_PATTERN = re.compile(r"(\w+)\s*=\s*[\{\"](.+?)[\}\"]\s*,?\s*$", re.MULTILINE)
AUTHOR_YEAR_PATTERN = re.compile(
    r"\(([^()]{2,80}?),\s*((?:19|20)\d{2})\)|\b([A-Z][A-Za-z'\-]+(?:\s+et\s+al\.)?)\s*\(((?:19|20)\d{2})\)"
)
NUMERIC_PATTERN = re.compile(r"\[(\d+(?:\s*[,;-]\s*\d+)*)\]")
IEEE_MARKER_PATTERN = re.compile(r"\[(\d+)\]")
IEEE_TITLE_PATTERN = re.compile(r"[\"']([^\"']+)[\"']")
DOI_PATTERN = re.compile(r"DOI\s*:\s*([^\s]+(?:\s*[^\s\]]+)*)", re.IGNORECASE)
YEAR_PATTERN = re.compile(r"\b((?:19|20)\d{2})\b")


def _slug(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "", normalized)


def _unique_key(db: Session, project_id: str, preferred: str) -> str:
    base = preferred[:140] or "reference"
    key = base
    suffix = 2
    while db.scalar(
        select(ReferenceRecord.id).where(
            ReferenceRecord.project_id == project_id,
            ReferenceRecord.citation_key == key,
        )
    ):
        key = f"{base}{suffix}"
        suffix += 1
    return key


def _escape_bibtex(value: str) -> str:
    cleaned = (value or "").replace("\r", " ").replace("\n", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned.replace("{", "\\{").replace("}", "\\}")


def _normalize_reference_text(raw_text: str) -> str:
    text = raw_text.replace("\r", "\n")
    text = text.replace("\u00a0", " ")
    text = re.sub(r"(?<=\w)-\s*\n\s*(?=\w)", "", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _extract_doi(block: str) -> str:
    match = DOI_PATTERN.search(block)
    if not match:
        return ""
    doi = re.sub(r"\s+", "", match.group(1))
    return doi.rstrip(".,;")


def _split_ieee_entries(raw_text: str) -> list[str]:
    text = _normalize_reference_text(raw_text)
    matches = list(IEEE_MARKER_PATTERN.finditer(text))
    if not matches:
        return []
    entries: list[str] = []
    for index, match in enumerate(matches):
        start = match.start()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        entry = text[start:end].strip(" ;")
        if entry:
            entries.append(entry)
    return entries


def _parse_ieee_entry(block: str) -> dict:
    marker_match = IEEE_MARKER_PATTERN.match(block)
    number = int(marker_match.group(1)) if marker_match else 0
    body = IEEE_MARKER_PATTERN.sub("", block, count=1).strip(" ,")
    title_match = IEEE_TITLE_PATTERN.search(body)
    title = title_match.group(1).strip(" ,") if title_match else ""
    if title_match:
        authors = body[: title_match.start()].strip(" ,")
        rest = body[title_match.end() :].strip(" ,")
    else:
        parts = body.split(",", 1)
        authors = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
    doi = _extract_doi(body)
    years = YEAR_PATTERN.findall(body)
    year = years[-1] if years else ""
    container = re.split(r",\s*(?:jourvol|vol\.?|in\s|pages?\s|number\s|DOI\s*:)", rest, maxsplit=1, flags=re.IGNORECASE)[0].strip(" ,") if rest else ""
    if not title:
        title = body
    return {
        "number": number,
        "citation_key": f"ieee{number:04d}",
        "authors": authors,
        "title": title,
        "year": year,
        "container_title": container,
        "doi": doi,
        "raw_reference": f"[{number}] {body}".strip(),
        "source_type": "ieee",
        "parse_confidence": 0.86 if title else 0.72,
    }


def preview_references(raw_text: str, source_type: str, reference_format: str = "auto") -> list[dict]:
    format_key = (reference_format or "auto").strip().lower()
    source_key = (source_type or "paste").strip().lower()
    if source_key == "bib" or format_key == "bibtex":
        entries = []
        for _entry_type, citation_key, body in BIB_ENTRY_PATTERN.findall(raw_text):
            fields = {key.lower(): value.strip() for key, value in BIB_FIELD_PATTERN.findall(body)}
            entries.append(
                {
                    "citation_key": citation_key.strip(),
                    "authors": fields.get("author", ""),
                    "title": fields.get("title", ""),
                    "year": fields.get("year", ""),
                    "container_title": fields.get("journal", fields.get("booktitle", "")),
                    "doi": fields.get("doi", ""),
                    "raw_reference": f"@{{{citation_key},{body}}}",
                    "source_type": "bib",
                    "parse_confidence": 0.95,
                }
            )
        return entries

    if format_key == "ieee":
        return [_parse_ieee_entry(block) for block in _split_ieee_entries(raw_text)]

    blocks = [block.strip() for block in re.split(r"(?m)(?:\n\s*\n|^\s*\d+[.)]\s+)", raw_text) if block.strip()]
    entries = []
    for index, block in enumerate(blocks, start=1):
        year_match = YEAR_PATTERN.search(block)
        year = year_match.group(1) if year_match else ""
        author_segment = block.split(".", 1)[0].strip()
        first_author = re.split(r"[,;&]", author_segment)[0].strip().split()[-1] if author_segment else "ref"
        entries.append(
            {
                "citation_key": f"{_slug(first_author)}{year or index}",
                "authors": author_segment,
                "title": block,
                "year": year,
                "container_title": "",
                "doi": _extract_doi(block),
                "raw_reference": block,
                "source_type": source_key,
                "parse_confidence": 0.6 if year else 0.4,
            }
        )
    return entries


def import_references(db: Session, project_id: str, raw_text: str, source_type: str, reference_format: str = "auto") -> list[ReferenceRecord]:
    created: list[ReferenceRecord] = []
    for item in preview_references(raw_text, source_type, reference_format):
        record = ReferenceRecord(
            project_id=project_id,
            citation_key=_unique_key(db, project_id, item["citation_key"]),
            authors=item.get("authors", ""),
            title=item.get("title", ""),
            year=item.get("year", ""),
            container_title=item.get("container_title", ""),
            doi=item.get("doi", ""),
            url=item.get("url", ""),
            raw_reference=item.get("raw_reference", ""),
            source_type=item.get("source_type", source_type),
            parse_confidence=item.get("parse_confidence", 0.5),
        )
        db.add(record)
        created.append(record)
    db.commit()
    return created


def _match_numeric_references(marker: str, references: list[ReferenceRecord]) -> list[ReferenceRecord]:
    numbers = [int(value) for value in re.findall(r"\d+", marker)]
    if not numbers:
        return []
    wanted = {f"ieee{number:04d}" for number in numbers}
    return [
        ref
        for ref in references
        if ref.citation_key in wanted or any(ref.raw_reference.startswith(f"[{number}]") for number in numbers)
    ]


def map_citations(db: Session, project_id: str) -> list[CitationOccurrence]:
    db.execute(delete(CitationOccurrence).where(CitationOccurrence.project_id == project_id))
    references = list(db.scalars(select(ReferenceRecord).where(ReferenceRecord.project_id == project_id)))
    units = list(db.scalars(select(DocumentUnit).where(DocumentUnit.project_id == project_id)))
    occurrences: list[CitationOccurrence] = []
    for unit in units:
        candidates: list[tuple[str, int, int]] = []
        for match in AUTHOR_YEAR_PATTERN.finditer(unit.content):
            candidates.append((match.group(0), match.start(), match.end()))
        for match in NUMERIC_PATTERN.finditer(unit.content):
            candidates.append((match.group(0), match.start(), match.end()))
        for marker, start, end in candidates:
            if NUMERIC_PATTERN.fullmatch(marker):
                matches = _match_numeric_references(marker, references)
            else:
                marker_lower = marker.lower()
                matches = [
                    ref
                    for ref in references
                    if (ref.year and ref.year in marker_lower)
                    and any(_slug(part) in _slug(marker_lower) for part in ref.authors.split() if len(part) > 3)
                ]
            status = "VERIFIED" if len(matches) == 1 else "AMBIGUOUS" if len(matches) > 1 else "MISSING_REFERENCE"
            occurrence = CitationOccurrence(
                project_id=project_id,
                unit_id=unit.id,
                reference_id=matches[0].id if len(matches) == 1 else None,
                marker=marker,
                context=unit.content[max(0, start - 100) : min(len(unit.content), end + 100)],
                page_number=unit.start_page,
                status=status,
            )
            db.add(occurrence)
            occurrences.append(occurrence)
    db.commit()
    return occurrences


def export_references_bib(db: Session, project_id: str) -> str:
    references = list(
        db.scalars(
            select(ReferenceRecord)
            .where(ReferenceRecord.project_id == project_id)
            .order_by(ReferenceRecord.created_at.asc())
        )
    )
    entries: list[str] = []
    for reference in references:
        entry_type = "article" if reference.container_title else "misc"
        fields: list[tuple[str, str]] = [
            ("author", reference.authors),
            ("title", reference.title),
            ("year", reference.year),
            ("doi", reference.doi),
        ]
        if reference.container_title:
            fields.append(("journal", reference.container_title))
        if reference.url:
            fields.append(("url", reference.url))
        if reference.raw_reference:
            fields.append(("note", reference.raw_reference))
        rendered_fields = ",\n".join(
            f"  {name} = {{{_escape_bibtex(value)}}}"
            for name, value in fields
            if (value or "").strip()
        )
        entries.append(f"@{entry_type}{{{reference.citation_key},\n{rendered_fields}\n}}")
    return "\n\n".join(entries).strip() + ("\n" if entries else "")
