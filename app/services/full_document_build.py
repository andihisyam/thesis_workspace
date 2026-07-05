from __future__ import annotations

import json
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.compile_service import run_latex_compile
from app.services.latex_revision_sanitizer import sanitize_revision_latex
from app.services.latex_structure_service import parse_latex_structure, resolve_review_unit


GENERATED_ARTIFACT_SUFFIXES = {
    ".aux",
    ".bbl",
    ".bcf",
    ".blg",
    ".fdb_latexmk",
    ".fls",
    ".lof",
    ".log",
    ".lot",
    ".out",
    ".pdf",
    ".run.xml",
    ".synctex.gz",
    ".toc",
}

HEADING_START_PATTERN = re.compile(
    r"^\s*\\(chapter|section|subsection|subsubsection)\*?\s*\{"
)


def _ignore_generated_artifacts(_directory: str, names: list[str]) -> set[str]:
    ignored: set[str] = set()
    for name in names:
        path = Path(name)
        suffixes = "".join(path.suffixes)
        if path.name == "main.tex":
            continue
        if suffixes in GENERATED_ARTIFACT_SUFFIXES or path.suffix in GENERATED_ARTIFACT_SUFFIXES:
            ignored.add(name)
    return ignored


def _normalize_file_text(content: str) -> str:
    stripped = content.rstrip()
    return stripped + "\n" if stripped else ""


def _is_full_file_draft(selected_scope: str, selected_target_id: str) -> bool:
    return selected_scope == "chapter" and selected_target_id in {"", "chapter:full"}


def _build_replacement_lines(
    unit: dict[str, Any],
    revised_text: str,
    original_lines: list[str],
    *,
    replace_whole_file: bool,
) -> list[str]:
    clean_text = sanitize_revision_latex(revised_text).strip("\n")
    if replace_whole_file:
        return clean_text.splitlines()

    body_lines = clean_text.splitlines() if clean_text else []
    if body_lines:
        heading_match = HEADING_START_PATTERN.match(body_lines[0].strip())
        if heading_match and heading_match.group(1) == unit["type"]:
            body_lines = body_lines[1:]

    heading_index = int(unit["start_line"]) - 1
    heading_line = original_lines[heading_index]
    return [heading_line, *body_lines]


def prepare_full_document_build(
    project_root: Path,
    thesis_root: Path,
    active_drafts: list[dict[str, Any]],
) -> dict[str, Any]:
    if not active_drafts:
        raise ValueError("Belum ada draft aktif untuk disusun menjadi dokumen final.")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_root = project_root / "data" / "full_document_runs" / f"run_{timestamp}"
    build_root = run_root / "merged"
    shutil.copytree(thesis_root, build_root, ignore=_ignore_generated_artifacts)

    applied_labels: list[str] = []
    manifest_drafts: list[dict[str, str]] = []
    drafts_by_file: dict[str, list[dict[str, Any]]] = {}
    for draft in active_drafts:
        selected_file = str(draft.get("selected_file", ""))
        if not selected_file:
            raise ValueError("Salah satu draft aktif belum memiliki file sumber.")
        drafts_by_file.setdefault(selected_file, []).append(draft)

    for selected_file, file_drafts in drafts_by_file.items():
        source_path = thesis_root / selected_file
        if not source_path.exists():
            raise ValueError(f"File sumber untuk draft aktif tidak ditemukan: {selected_file}")

        original_text = source_path.read_text(encoding="utf-8")
        original_lines = original_text.splitlines()
        document = parse_latex_structure(selected_file, original_text)
        replacements: list[dict[str, Any]] = []

        for draft in file_drafts:
            selected_scope = str(draft.get("selected_scope", ""))
            selected_target_id = str(draft.get("selected_target_id", ""))
            unit = resolve_review_unit(document, selected_scope, selected_target_id)
            replace_whole_file = _is_full_file_draft(selected_scope, selected_target_id)
            start_index = 0 if replace_whole_file else int(unit["start_line"]) - 1
            end_index = len(original_lines) if replace_whole_file else int(unit["end_line"])
            replacements.append(
                {
                    "label": str(draft.get("selected_label") or unit["display_label"]),
                    "start_index": start_index,
                    "end_index": end_index,
                    "replacement_lines": _build_replacement_lines(
                        unit,
                        str(draft.get("revised_text", "")),
                        original_lines,
                        replace_whole_file=replace_whole_file,
                    ),
                    "json_path": str(draft.get("json_path", "")),
                }
            )

        replacements.sort(key=lambda item: item["start_index"])
        for index in range(1, len(replacements)):
            previous = replacements[index - 1]
            current = replacements[index]
            if current["start_index"] < previous["end_index"]:
                raise ValueError(
                    "Ada draft aktif yang saling bertumpang tindih. Nonaktifkan salah satu draft sebelum generate full PDF."
                )

        merged_lines = list(original_lines)
        for replacement in sorted(replacements, key=lambda item: item["start_index"], reverse=True):
            merged_lines[replacement["start_index"] : replacement["end_index"]] = replacement["replacement_lines"]
            applied_labels.append(replacement["label"])
            manifest_drafts.append(
                {
                    "selected_file": selected_file,
                    "selected_label": replacement["label"],
                    "json_path": replacement["json_path"],
                }
            )

        merged_path = build_root / selected_file
        merged_path.write_text(_normalize_file_text("\n".join(merged_lines)), encoding="utf-8")

    manifest = {
        "preview_mode": "full",
        "applied_drafts": manifest_drafts,
    }
    (run_root / "build_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    compile_result = run_latex_compile(build_root, project_root)
    return {
        "run_root": str(run_root),
        "preview_mode": "full",
        "applied_draft_count": len(manifest_drafts),
        "applied_draft_labels": applied_labels,
        "compile_result": compile_result,
    }
