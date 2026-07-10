from __future__ import annotations

import re
from typing import Iterable


LIST_ITEM_RE = re.compile(r"^(\d+)\.\s+(.*)$")
PAGE_ARTIFACT_RE = re.compile(r"^\d+$")
NUMBERING_ONLY_RE = re.compile(r"^\d+(?:\.\d+)*\.?$")


def _command_for_level(level: str) -> str:
    mapping = {
        "CHAPTER": "chapter",
        "SUBCHAPTER": "section",
        "SUBSUBCHAPTER": "subsection",
        "FRONTMATTER": "section*",
    }
    return mapping.get(level or "", "section")


def _normalize_text(text: str) -> str:
    value = text.replace("\r\n", "\n")
    value = value.replace("\xa0", " ")
    value = re.sub(r"[ \t]+", " ", value)
    return value


def _drop_artifact_lines(lines: list[str]) -> list[str]:
    cleaned: list[str] = []
    for raw in lines:
        line = raw.strip()
        if not line:
            cleaned.append("")
            continue
        if PAGE_ARTIFACT_RE.fullmatch(line):
            continue
        cleaned.append(line)
    while cleaned and not cleaned[0]:
        cleaned.pop(0)
    while cleaned and not cleaned[-1]:
        cleaned.pop()
    return cleaned


def _remove_heading_echo(lines: list[str], number: str, title: str, level: str) -> list[str]:
    index = 0
    upper_title = title.strip().upper()
    if index < len(lines) and level == "CHAPTER" and re.fullmatch(r"BAB\s+[IVXLCDM]+", lines[index], flags=re.IGNORECASE):
        index += 1
    if index < len(lines) and NUMBERING_ONLY_RE.fullmatch(lines[index]):
        index += 1
    if index < len(lines) and upper_title and lines[index].upper() == upper_title:
        index += 1
    if index < len(lines) and number and NUMBERING_ONLY_RE.fullmatch(lines[index]) and lines[index].rstrip(".") == number.rstrip("."):
        index += 1
    if index < len(lines) and upper_title and lines[index].upper() == upper_title:
        index += 1
    trimmed = lines[index:]
    while trimmed and not trimmed[0]:
        trimmed.pop(0)
    return trimmed


def _command_for_numbering(numbering: str) -> str:
    depth = len([part for part in numbering.rstrip('.').split('.') if part])
    mapping = {
        1: 'section',
        2: 'section',
        3: 'subsection',
        4: 'subsubsection',
    }
    return mapping.get(depth, 'subsection')


def _looks_like_heading_title(line: str) -> bool:
    words = [part for part in line.split() if part]
    if not words or len(words) > 8:
        return False
    return all(len(word) < 40 for word in words)


def _promote_inner_headings(lines: list[str]) -> list[str]:
    promoted: list[str] = []
    index = 0
    while index < len(lines):
        line = lines[index]
        if NUMBERING_ONLY_RE.fullmatch(line) and index + 1 < len(lines):
            title = lines[index + 1].strip()
            if title and not NUMBERING_ONLY_RE.fullmatch(title) and _looks_like_heading_title(title):
                command = _command_for_numbering(line)
                if promoted and promoted[-1] != '':
                    promoted.append('')
                promoted.append(f"\\{command}{{{title}}}")
                promoted.append('')
                index += 2
                continue
        promoted.append(line)
        index += 1
    return promoted


def _title_looks_generic(title: str, level: str) -> bool:
    if level != 'CHAPTER':
        return False
    normalized = title.strip().lower()
    return not normalized or bool(re.fullmatch(r'bab\s+[ivxlcdm]+', normalized))


def _infer_title_from_lines(lines: list[str], fallback: str, level: str) -> tuple[str, list[str]]:
    if not _title_looks_generic(fallback, level):
        return fallback.strip(), lines
    if not lines:
        return fallback.strip(), lines
    candidate = lines[0].strip()
    words = [part for part in candidate.split() if part]
    if candidate and len(words) <= 6:
        return candidate.title(), lines[1:]
    return fallback.strip(), lines


def _merge_wrapped_lines(lines: list[str]) -> list[str]:
    blocks: list[str] = []
    current = ""
    for line in lines:
        if not line:
            if current.strip():
                blocks.append(current.strip())
                current = ""
            continue
        if LIST_ITEM_RE.match(line):
            if current.strip():
                blocks.append(current.strip())
                current = ""
            blocks.append(line)
            continue
        if not current:
            if blocks and LIST_ITEM_RE.match(blocks[-1]) and not line.startswith("\\"):
                if blocks[-1].endswith("-"):
                    blocks[-1] = blocks[-1][:-1] + line
                else:
                    blocks[-1] = f"{blocks[-1]} {line}"
                continue
            current = line
            continue
        if current.endswith("-"):
            current = current[:-1] + line
        else:
            current = f"{current} {line}"
    if current.strip():
        blocks.append(current.strip())
    return blocks


def _blocks_to_latex(blocks: list[str]) -> str:
    output: list[str] = []
    index = 0
    while index < len(blocks):
        match = LIST_ITEM_RE.match(blocks[index])
        if match:
            items: list[str] = []
            while index < len(blocks):
                current_match = LIST_ITEM_RE.match(blocks[index])
                if not current_match:
                    break
                items.append(current_match.group(2).strip())
                index += 1
            enum_block = "\n".join([
                r"\begin{enumerate}",
                *(f"\\item {item}" for item in items),
                r"\end{enumerate}",
            ])
            output.append(enum_block)
            continue
        output.append(blocks[index])
        index += 1
    return "\n\n".join(output).strip()


def _format_revision_notes(suggestions: list[dict]) -> str:
    notes: list[str] = []
    for index, item in enumerate(suggestions[:8], start=1):
        issue = str(item.get("issue", "")).strip()
        suggestion = str(item.get("suggestion", "")).strip()
        if not issue and not suggestion:
            continue
        pieces = [piece for piece in [issue, suggestion] if piece]
        notes.append(f"% {index}. {' '.join(pieces)}")
    if not notes:
        return ""
    return "\n".join([
        "% ====================",
        "% Catatan revisi otomatis",
        "% ====================",
        *notes,
    ])


def build_revision_draft(source_text: str, suggestions: Iterable[dict], section_label: str, user_goal: str, *, section_number: str = "", section_title: str = "", section_level: str = "") -> tuple[str, str]:
    suggestions = list(suggestions)
    normalized = _normalize_text(source_text)
    lines = _drop_artifact_lines(normalized.split("\n"))
    lines = _remove_heading_echo(lines, section_number, section_title, section_level)
    lines = _promote_inner_headings(lines)
    resolved_title, lines = _infer_title_from_lines(lines, section_title, section_level)
    blocks = _merge_wrapped_lines(lines)
    body = _blocks_to_latex(blocks)

    heading = ""
    if resolved_title.strip():
        command = _command_for_level(section_level)
        heading = f"\\{command}{{{resolved_title.strip()}}}"

    content_parts = [part for part in [heading, body] if part]
    content = "\n\n".join(content_parts).strip()
    notes_block = _format_revision_notes(suggestions)
    if notes_block:
        content = f"{content}\n\n{notes_block}".strip()
        summary = f"Draft {section_label} dirapikan ke format LaTeX dan dilengkapi {min(len(suggestions), 8)} catatan revisi. Tujuan user: {user_goal}."
    else:
        summary = f"Draft {section_label} dirapikan ke format LaTeX tanpa catatan revisi tambahan. Tujuan user: {user_goal}."
    return content, summary
