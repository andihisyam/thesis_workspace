from pathlib import Path

import pytest

from app.services import full_document_build


CHAPTER = r"""\chapter{Pendahuluan}
Pembuka.
\section{Latar Belakang}
Isi lama.
\subsection{Konteks}
Konteks lama.
\section{Rumusan Masalah}
Rumusan lama.
"""


@pytest.fixture
def thesis_workspace(tmp_path: Path) -> tuple[Path, Path]:
    thesis_root = tmp_path / "thesis"
    thesis_root.mkdir()
    (thesis_root / "main.tex").write_text(
        r"\documentclass{report}\begin{document}\input{chapter1}\end{document}",
        encoding="utf-8",
    )
    (thesis_root / "chapter1.tex").write_text(CHAPTER, encoding="utf-8")
    return tmp_path, thesis_root


def fake_compile(thesis_root: Path, _project_root: Path) -> dict:
    pdf_path = thesis_root / "main.pdf"
    pdf_path.write_bytes(b"%PDF-test")
    return {
        "success": True,
        "steps": [],
        "summary": "ok",
        "log_path": "",
        "pdf_path": str(pdf_path),
    }


def test_full_build_applies_revision_without_changing_source(
    thesis_workspace: tuple[Path, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    project_root, thesis_root = thesis_workspace
    monkeypatch.setattr(full_document_build, "run_latex_compile", fake_compile)
    draft = {
        "selected_file": "chapter1.tex",
        "selected_scope": "section",
        "selected_target_id": "section:1",
        "selected_label": "1.1 Latar Belakang",
        "revised_text": "Isi baru.\n\\subsection{Konteks}\nKonteks baru.",
        "json_path": "draft.json",
    }

    result = full_document_build.prepare_full_document_build(
        project_root,
        thesis_root,
        [draft],
    )

    merged = Path(result["run_root"]) / "merged" / "chapter1.tex"
    merged_text = merged.read_text(encoding="utf-8")
    assert "Isi baru." in merged_text
    assert "Konteks baru." in merged_text
    assert "Rumusan lama." in merged_text
    assert thesis_root.joinpath("chapter1.tex").read_text(encoding="utf-8") == CHAPTER
    assert result["compile_result"]["success"] is True


def test_full_build_requires_an_active_draft(
    thesis_workspace: tuple[Path, Path],
) -> None:
    project_root, thesis_root = thesis_workspace

    with pytest.raises(ValueError, match="Belum ada draft aktif"):
        full_document_build.prepare_full_document_build(project_root, thesis_root, [])
