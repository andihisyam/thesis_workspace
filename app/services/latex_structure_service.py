import re
from typing import Any


HEADING_PATTERNS = {
    "chapter": re.compile(r"^\\chapter(\*)?\{(.+?)\}"),
    "section": re.compile(r"^\\section(\*)?\{(.+?)\}"),
    "subsection": re.compile(r"^\\subsection(\*)?\{(.+?)\}"),
    "subsubsection": re.compile(r"^\\subsubsection(\*)?\{(.+?)\}"),
}

LEVEL_RANK = {
    "chapter": 0,
    "section": 1,
    "subsection": 2,
    "subsubsection": 3,
}


def _is_frontmatter_file(file_name: str) -> bool:
    return file_name.lower() == "frontmatter.tex"


def _find_heading(line: str) -> tuple[str, str, bool] | None:
    stripped = line.strip()
    for level, pattern in HEADING_PATTERNS.items():
        match = pattern.match(stripped)
        if match:
            return level, match.group(2).strip(), bool(match.group(1))
    return None


def _extract_chapter_number(file_name: str) -> str:
    match = re.search(r"chapter(\d+)", file_name, re.IGNORECASE)
    return match.group(1) if match else "?"


def _build_path(unit: dict[str, Any]) -> str:
    if unit["type"] == "chapter" and unit.get("is_starred"):
        return unit["title"]

    parts = [unit.get("chapter_title", "")]
    for key in ("section_title", "subsection_title", "subsubsection_title"):
        value = unit.get(key, "")
        if value:
            parts.append(value)
    return " > ".join(part for part in parts if part)


def _build_display_label(unit: dict[str, Any]) -> str:
    if unit["type"] == "chapter":
        if unit.get("is_starred") or unit.get("chapter_number") == "?":
            return unit["title"]
        return f"Bab {unit['chapter_number']} - {unit['chapter_title']}"
    return f"{unit['display_number']} {unit['title']}"


def parse_latex_structure(file_name: str, document_text: str) -> dict[str, Any]:
    lines = document_text.splitlines()
    events: list[dict[str, Any]] = []

    for index, line in enumerate(lines):
        found = _find_heading(line)
        if found:
            level, title, is_starred = found
            events.append(
                {
                    "level": level,
                    "title": title,
                    "is_starred": is_starred,
                    "line_index": index,
                }
            )

    chapter_title = "Bagian Awal" if _is_frontmatter_file(file_name) else file_name.replace(".tex", "")
    chapter_event = next((event for event in events if event["level"] == "chapter"), None)
    if chapter_event and not _is_frontmatter_file(file_name):
        chapter_title = chapter_event["title"]

    chapter_number = _extract_chapter_number(file_name)
    units: list[dict[str, Any]] = []
    current = {
        "chapter_title": chapter_title,
        "section_title": "",
        "subsection_title": "",
        "subsubsection_title": "",
        "section_number": 0,
        "subsection_number": 0,
        "subsubsection_number": 0,
    }

    for position, event in enumerate(events):
        level = event["level"]
        if level == "chapter":
            end_index = len(lines) - 1
            for next_event in events[position + 1 :]:
                if next_event["level"] == "chapter":
                    end_index = next_event["line_index"] - 1
                    break

            if event.get("is_starred"):
                content_lines = lines[event["line_index"] + 1 : end_index + 1]
                raw_latex = "\n".join(content_lines).strip()
                unit = {
                    "id": f"chapter:{position}",
                    "type": "chapter",
                    "title": event["title"],
                    "file_name": file_name,
                    "chapter_number": chapter_number,
                    "display_number": chapter_number,
                    "chapter_title": event["title"],
                    "section_title": "",
                    "subsection_title": "",
                    "subsubsection_title": "",
                    "raw_latex": raw_latex,
                    "start_line": event["line_index"] + 1,
                    "end_line": end_index + 1,
                    "is_starred": True,
                }
                unit["path"] = _build_path(unit)
                unit["display_label"] = _build_display_label(unit)
                units.append(unit)

            current["chapter_title"] = event["title"]
            current["section_title"] = ""
            current["subsection_title"] = ""
            current["subsubsection_title"] = ""
            current["section_number"] = 0
            current["subsection_number"] = 0
            current["subsubsection_number"] = 0
            continue

        if level == "section":
            current["section_number"] += 1
            current["subsection_number"] = 0
            current["subsubsection_number"] = 0
            current["section_title"] = event["title"]
            current["subsection_title"] = ""
            current["subsubsection_title"] = ""
            display_number = f"{chapter_number}.{current['section_number']}"
        elif level == "subsection":
            current["subsection_number"] += 1
            current["subsubsection_number"] = 0
            current["subsection_title"] = event["title"]
            current["subsubsection_title"] = ""
            display_number = (
                f"{chapter_number}.{current['section_number']}.{current['subsection_number']}"
            )
        else:
            current["subsubsection_number"] += 1
            current["subsubsection_title"] = event["title"]
            display_number = (
                f"{chapter_number}.{current['section_number']}.{current['subsection_number']}.{current['subsubsection_number']}"
            )

        end_index = len(lines) - 1
        current_rank = LEVEL_RANK[level]
        for next_event in events[position + 1 :]:
            if next_event["level"] == "chapter":
                end_index = next_event["line_index"] - 1
                break
            if LEVEL_RANK[next_event["level"]] <= current_rank:
                end_index = next_event["line_index"] - 1
                break
            if level == "subsubsection":
                end_index = next_event["line_index"] - 1
                break

        content_lines = lines[event["line_index"] + 1 : end_index + 1]
        raw_latex = "\n".join(content_lines).strip()

        unit = {
            "id": f"{level}:{position}",
            "type": level,
            "title": event["title"],
            "file_name": file_name,
            "chapter_number": chapter_number,
            "display_number": display_number,
            "chapter_title": current["chapter_title"],
            "section_title": current["section_title"],
            "subsection_title": current["subsection_title"],
            "subsubsection_title": current["subsubsection_title"],
            "raw_latex": raw_latex,
            "start_line": event["line_index"] + 1,
            "end_line": end_index + 1,
            "is_starred": bool(event.get("is_starred")),
        }
        unit["path"] = _build_path(unit)
        unit["display_label"] = _build_display_label(unit)
        units.append(unit)

    chapter_unit = {
        "id": "chapter:full",
        "type": "chapter",
        "title": chapter_title,
        "file_name": file_name,
        "chapter_number": chapter_number,
        "display_number": chapter_number,
        "chapter_title": chapter_title,
        "section_title": "",
        "subsection_title": "",
        "subsubsection_title": "",
        "raw_latex": document_text,
        "start_line": 1,
        "end_line": len(lines),
        "path": chapter_title,
        "is_starred": _is_frontmatter_file(file_name),
    }
    chapter_unit["display_label"] = _build_display_label(chapter_unit)

    grouped = {
        "chapter": chapter_unit,
        "sections": [unit for unit in units if unit["type"] == "section"],
        "subsections": [unit for unit in units if unit["type"] == "subsection"],
        "subsubsections": [unit for unit in units if unit["type"] == "subsubsection"],
        "all_units": units,
    }
    return grouped


def build_review_menu(document: dict[str, Any]) -> list[dict[str, str]]:
    items = [
        {
            "scope": "chapter",
            "target_id": document["chapter"]["id"],
            "label": document["chapter"]["display_label"],
        }
    ]
    for unit in document["all_units"]:
        items.append(
            {
                "scope": unit["type"],
                "target_id": unit["id"],
                "label": unit["display_label"],
            }
        )
    return items


def build_outline_lines(document: dict[str, Any]) -> list[str]:
    lines = [document["chapter"]["display_label"]]
    for unit in document["all_units"]:
        indent = ""
        if unit["type"] == "subsection":
            indent = "  "
        elif unit["type"] == "subsubsection":
            indent = "    "
        lines.append(f"{indent}{unit['display_label']}")
    return lines


def resolve_review_unit(document: dict[str, Any], scope_type: str, target_id: str | None = None) -> dict[str, Any]:
    if scope_type == "chapter":
        if target_id and target_id != document["chapter"]["id"]:
            for unit in document["all_units"]:
                if unit["type"] == "chapter" and unit["id"] == target_id:
                    return unit
        return document["chapter"]

    for unit in document["all_units"]:
        if unit["type"] == scope_type and unit["id"] == target_id:
            return unit

    raise ValueError("Bagian yang dipilih tidak ditemukan.")
