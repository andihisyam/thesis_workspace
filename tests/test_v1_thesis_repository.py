import json
from pathlib import Path

import pytest

from app.services.thesis_repository import ThesisRepository


CHAPTER = r"""\chapter{Pendahuluan}
Pembuka.
\section{Latar Belakang}
Isi latar belakang.
\subsection{Konteks}
Isi konteks.
\section{Rumusan Masalah}
Isi rumusan masalah.
"""


@pytest.fixture
def repository(tmp_path: Path) -> ThesisRepository:
    thesis_root = tmp_path / "thesis"
    thesis_root.mkdir()
    (thesis_root / "main.tex").write_text("main", encoding="utf-8")
    (thesis_root / "appendices.tex").write_text("lampiran", encoding="utf-8")
    (thesis_root / "chapter1.tex").write_text(CHAPTER, encoding="utf-8")
    (thesis_root / "frontmatter.tex").write_text("frontmatter", encoding="utf-8")
    return ThesisRepository(thesis_root)


def save_draft(
    repository: ThesisRepository,
    *,
    label: str,
    scope: str,
    target_id: str,
    content: str = "Isi revisi.",
) -> Path:
    repository.save_revision_draft(
        filename="chapter1.tex",
        selected_label=label,
        content=content,
        metadata={
            "selected_scope": scope,
            "selected_target_id": target_id,
            "original_text": "Isi original.",
            "revised_text": content,
            "revision_summary": "Ringkasan.",
        },
    )
    safe_label = label.replace(" ", "_")
    return repository.revision_drafts_dir / f"chapter1__{safe_label}.json"


def test_repository_lists_only_editable_thesis_files(repository: ThesisRepository) -> None:
    assert repository.list_tex_files() == ["chapter1.tex", "frontmatter.tex"]


def test_draft_lifecycle_keeps_thesis_source_unchanged(repository: ThesisRepository) -> None:
    original_source = repository.read_tex("chapter1.tex")
    json_path = save_draft(
        repository,
        label="1.1 Latar Belakang",
        scope="section",
        target_id="section:1",
        content="**Revisi** & aman.",
    )

    loaded = repository.load_revision_draft(str(json_path))
    assert loaded["revised_text"] == r"\textbf{Revisi} \& aman."
    assert Path(loaded["tex_path"]).read_text(encoding="utf-8") == loaded["revised_text"]

    updated = repository.update_revision_draft_content(str(json_path), "Versi terbaru.")
    assert updated["revised_text"] == "Versi terbaru."
    assert repository.read_tex("chapter1.tex") == original_source

    deleted = repository.delete_revision_draft(str(json_path))
    assert not Path(deleted["json_path"]).exists()
    assert not Path(deleted["tex_path"]).exists()
    assert repository.read_tex("chapter1.tex") == original_source


def test_invalid_draft_metadata_is_skipped(repository: ThesisRepository) -> None:
    invalid_path = repository.revision_drafts_dir / "invalid.json"
    invalid_path.write_text("{not-json", encoding="utf-8")

    assert repository.list_revision_drafts() == []


def test_activating_overlapping_draft_deactivates_previous_draft(
    repository: ThesisRepository,
) -> None:
    section_path = save_draft(
        repository,
        label="Section",
        scope="section",
        target_id="section:1",
    )
    subsection_path = save_draft(
        repository,
        label="Subsection",
        scope="subsection",
        target_id="subsection:2",
    )

    repository.set_full_document_active(str(section_path), True)
    repository.set_full_document_active(str(subsection_path), True)

    active = repository.list_active_revision_drafts()
    assert [item["selected_label"] for item in active] == ["Subsection"]
    section_payload = json.loads(section_path.read_text(encoding="utf-8"))
    assert section_payload["is_active_for_full_document"] is False


def test_non_overlapping_drafts_can_stay_active(repository: ThesisRepository) -> None:
    first_path = save_draft(
        repository,
        label="Section Satu",
        scope="section",
        target_id="section:1",
    )
    second_path = save_draft(
        repository,
        label="Section Dua",
        scope="section",
        target_id="section:3",
    )

    repository.set_full_document_active(str(first_path), True)
    repository.set_full_document_active(str(second_path), True)

    assert len(repository.list_active_revision_drafts()) == 2
