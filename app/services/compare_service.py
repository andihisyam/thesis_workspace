from __future__ import annotations

import difflib
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.compile_service import run_latex_compile
from app.services.latex_revision_sanitizer import sanitize_revision_latex
from app.services.latex_structure_service import parse_latex_structure, resolve_review_unit


def _is_full_file_draft(selected_scope: str, selected_target_id: str) -> bool:
    return selected_scope == "chapter" and selected_target_id in {"", "chapter:full"}


def build_html_diff(original_text: str, revised_text: str) -> str:
    differ = difflib.HtmlDiff(tabsize=4, wrapcolumn=80)
    return differ.make_table(
        original_text.splitlines(),
        revised_text.splitlines(),
        fromdesc="Teks Asli",
        todesc="Draft Revisi",
        context=True,
        numlines=2,
    )


def apply_revision_to_document(
    full_text: str,
    selected_file: str,
    selected_scope: str,
    selected_target_id: str,
    revised_text: str,
) -> str:
    if _is_full_file_draft(selected_scope, selected_target_id):
        return revised_text

    document = parse_latex_structure(selected_file, full_text)
    unit = resolve_review_unit(document, selected_scope, selected_target_id)
    lines = full_text.splitlines()
    start_index = int(unit["start_line"]) - 1
    end_index = int(unit["end_line"])
    revised_lines = sanitize_revision_latex(revised_text).strip("\n").splitlines()

    if unit["type"] == "chapter":
        lines[start_index:end_index] = revised_lines
    else:
        heading_line = lines[start_index]
        if revised_lines:
            heading_pattern = rf"^\\{unit['type']}\*?\{{"
            if re.match(heading_pattern, revised_lines[0].strip()):
                revised_lines = revised_lines[1:]
        lines[start_index:end_index] = [heading_line, *revised_lines]

    return "\n".join(lines) + "\n"


def prepare_compare_build(
    project_root: Path,
    thesis_root: Path,
    draft_metadata: dict[str, Any],
    *,
    revised_text_override: str | None = None,
    include_original_compile: bool = True,
) -> dict[str, Any]:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    run_root = project_root / "data" / "compile_runs" / f"run_{timestamp}"
    original_root = run_root / "original"
    revised_root = run_root / "revised"

    shutil.copytree(thesis_root, original_root)
    shutil.copytree(thesis_root, revised_root)

    selected_file = draft_metadata["selected_file"]
    original_full_text = (thesis_root / selected_file).read_text(encoding="utf-8")
    revised_text = sanitize_revision_latex(revised_text_override or draft_metadata["revised_text"])
    revised_full_text = apply_revision_to_document(
        full_text=original_full_text,
        selected_file=selected_file,
        selected_scope=draft_metadata["selected_scope"],
        selected_target_id=draft_metadata.get("selected_target_id", ""),
        revised_text=revised_text,
    )
    (revised_root / selected_file).write_text(revised_full_text, encoding="utf-8")

    if include_original_compile:
        original_result = run_latex_compile(original_root, project_root)
    else:
        original_result = {
            "success": True,
            "steps": [],
            "summary": "Compile asli dilewati pada mode preview editor.",
            "log_path": "",
            "pdf_path": str(original_root / "main.pdf") if (original_root / "main.pdf").exists() else "",
        }
    revised_result = run_latex_compile(revised_root, project_root)

    return {
        "run_root": str(run_root),
        "original": original_result,
        "revised": revised_result,
        "original_text": draft_metadata["original_text"],
        "revised_text": revised_text,
        "diff_html": build_html_diff(draft_metadata["original_text"], revised_text),
    }
