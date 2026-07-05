from __future__ import annotations

import json
import re
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from app.services.compile_service import run_latex_compile
from app.services.latex_revision_sanitizer import sanitize_revision_latex
from app.services.latex_structure_service import parse_latex_structure, resolve_review_unit


DOCUMENT_START_PATTERN = re.compile(r"\\begin\s*\{document\}")
HEADING_START_PATTERN = re.compile(
    r"^\s*\\(chapter|section|subsection|subsubsection)\*?\s*\{"
)
VALID_SCOPES = {"chapter", "section", "subsection", "subsubsection"}


@dataclass(frozen=True)
class FragmentContext:
    selected_file: str
    scope: str
    target_id: str
    label: str
    title: str
    chapter_number: int
    is_starred: bool = False
    is_full_file: bool = False
    section_number: int = 0
    subsection_number: int = 0
    subsubsection_number: int = 0


def _extract_preamble(main_source: str) -> str:
    marker = DOCUMENT_START_PATTERN.search(main_source)
    if marker is None:
        raise ValueError("main.tex tidak memiliki \\begin{document}.")
    return main_source[: marker.start()].rstrip()


def _parse_display_number(display_number: str) -> tuple[int, int, int, int]:
    parts = display_number.split(".")
    try:
        numbers = [int(part) for part in parts if part]
    except ValueError as exc:
        raise ValueError(f"Nomor heading tidak valid: {display_number}") from exc

    padded = (numbers + [0, 0, 0, 0])[:4]
    return padded[0], padded[1], padded[2], padded[3]


def resolve_fragment_context(
    thesis_root: Path,
    draft_metadata: dict[str, Any],
) -> FragmentContext:
    selected_file = str(draft_metadata.get("selected_file", ""))
    selected_scope = str(draft_metadata.get("selected_scope", ""))
    selected_target_id = str(draft_metadata.get("selected_target_id", ""))

    if selected_scope not in VALID_SCOPES:
        raise ValueError("Scope draft tidak didukung untuk preview fragmen.")

    source_path = (thesis_root / selected_file).resolve()
    thesis_root_resolved = thesis_root.resolve()
    if source_path.parent != thesis_root_resolved or not source_path.is_file():
        raise ValueError("File sumber draft tidak valid atau tidak ditemukan.")

    document = parse_latex_structure(
        selected_file,
        source_path.read_text(encoding="utf-8"),
    )
    unit = resolve_review_unit(document, selected_scope, selected_target_id)
    is_full_file = selected_scope == "chapter" and selected_target_id in {"", "chapter:full"}
    try:
        chapter, section, subsection, subsubsection = _parse_display_number(
            str(unit["display_number"])
        )
    except ValueError:
        chapter, section, subsection, subsubsection = 0, 0, 0, 0

    return FragmentContext(
        selected_file=selected_file,
        scope=selected_scope,
        target_id=selected_target_id,
        label=str(draft_metadata.get("selected_label") or unit["display_label"]),
        title=str(unit["title"]),
        chapter_number=chapter,
        is_starred=bool(unit.get("is_starred")),
        is_full_file=is_full_file,
        section_number=section,
        subsection_number=subsection,
        subsubsection_number=subsubsection,
    )


def _counter_setup(context: FragmentContext) -> list[str]:
    if context.is_starred and context.scope == "chapter":
        return []

    if context.scope == "chapter":
        return [f"\\setcounter{{chapter}}{{{max(context.chapter_number - 1, 0)}}}"]

    commands = [f"\\setcounter{{chapter}}{{{context.chapter_number}}}"]
    if context.scope == "section":
        commands.append(f"\\setcounter{{section}}{{{max(context.section_number - 1, 0)}}}")
    elif context.scope == "subsection":
        commands.extend(
            [
                f"\\setcounter{{section}}{{{context.section_number}}}",
                f"\\setcounter{{subsection}}{{{max(context.subsection_number - 1, 0)}}}",
            ]
        )
    elif context.scope == "subsubsection":
        commands.extend(
            [
                f"\\setcounter{{section}}{{{context.section_number}}}",
                f"\\setcounter{{subsection}}{{{context.subsection_number}}}",
                f"\\setcounter{{subsubsection}}{{{max(context.subsubsection_number - 1, 0)}}}",
            ]
        )
    return commands


def build_fragment_source(context: FragmentContext, content: str) -> str:
    clean_content = content.strip()
    if not clean_content:
        raise ValueError("Isi fragmen kosong dan tidak dapat di-compile.")

    heading_match = HEADING_START_PATTERN.match(clean_content)
    if heading_match and heading_match.group(1) == context.scope:
        # Keep an LLM-provided heading without duplicating it in the wrapper.
        return clean_content + "\n"

    if context.scope == "chapter":
        heading = f"\\chapter*{{{context.title}}}" if context.is_starred else f"\\chapter{{{context.title}}}"
        return f"{heading}\n\n{clean_content}\n"

    heading = f"\\{context.scope}{{{context.title}}}"
    return f"{heading}\n\n{clean_content}\n"


def build_fragment_wrapper(main_source: str, context: FragmentContext) -> str:
    preamble = _extract_preamble(main_source)
    counters = "\n".join(_counter_setup(context))
    return (
        f"{preamble}\n\n"
        "% Generated fragment-preview wrapper. Do not edit the thesis source here.\n"
        "\\begin{document}\n"
        "\\selectlanguage{indonesian}\n"
        "\\pagenumbering{arabic}\n"
        "\\setcounter{page}{1}\n"
        f"{counters}\n"
        "\\input{fragment}\n"
        "\\end{document}\n"
    )


def _ignore_main_artifacts(_directory: str, names: list[str]) -> set[str]:
    return {
        name
        for name in names
        if name.startswith("main.") and name != "main.tex"
    }


def _prepare_variant_root(
    thesis_root: Path,
    variant_root: Path,
    main_source: str,
    context: FragmentContext,
    content: str,
) -> None:
    # Excluding generated main.* files prevents stale PDFs and locked aux files.
    shutil.copytree(thesis_root, variant_root, ignore=_ignore_main_artifacts)

    (variant_root / "main.tex").write_text(
        build_fragment_wrapper(main_source, context),
        encoding="utf-8",
    )
    (variant_root / "fragment.tex").write_text(
        build_fragment_source(context, content),
        encoding="utf-8",
    )


def prepare_fragment_compare_build(
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

    context = resolve_fragment_context(thesis_root, draft_metadata)
    main_source = (thesis_root / "main.tex").read_text(encoding="utf-8")
    original_text = str(draft_metadata.get("original_text", ""))
    revised_text = sanitize_revision_latex(
        revised_text_override
        if revised_text_override is not None
        else str(draft_metadata.get("revised_text", ""))
    )

    _prepare_variant_root(thesis_root, original_root, main_source, context, original_text)
    _prepare_variant_root(thesis_root, revised_root, main_source, context, revised_text)

    manifest = {
        "preview_mode": "fragment",
        "fragment": asdict(context),
        "variants": {
            "original": str(original_root / "fragment.tex"),
            "revised": str(revised_root / "fragment.tex"),
        },
    }
    (run_root / "preview_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    if include_original_compile:
        original_result = run_latex_compile(original_root, project_root)
    else:
        original_result = {
            "success": True,
            "steps": [],
            "summary": "Compile fragmen asli dilewati pada mode editor.",
            "log_path": "",
            "pdf_path": "",
        }

    revised_result = run_latex_compile(revised_root, project_root)
    return {
        "run_root": str(run_root),
        "preview_mode": "fragment",
        "fragment_label": context.label,
        "fragment_scope": context.scope,
        "original": original_result,
        "revised": revised_result,
        "original_text": original_text,
        "revised_text": revised_text,
        # Kept for API compatibility while the UI no longer renders a colored diff.
        "diff_html": "",
    }
