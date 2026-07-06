import pytest

from app.services.latex_structure_service import (
    build_review_menu,
    parse_latex_structure,
    resolve_review_unit,
)


DOCUMENT = r"""\chapter{Landasan Teori}
Pembuka bab.
\section{Diabetes}
Isi section.
\subsection{Definisi}
Isi definisi.
\subsubsection{Gejala}
Isi gejala.
\section{Machine Learning}
Isi machine learning.
"""


def test_parser_builds_numbered_thesis_menu() -> None:
    document = parse_latex_structure("chapter2.tex", DOCUMENT)
    menu = build_review_menu(document)

    assert [item["label"] for item in menu] == [
        "Bab 2 - Landasan Teori",
        "2.1 Diabetes",
        "2.1.1 Definisi",
        "2.1.1.1 Gejala",
        "2.2 Machine Learning",
    ]


def test_resolved_section_contains_children_but_not_next_section() -> None:
    document = parse_latex_structure("chapter2.tex", DOCUMENT)
    section = resolve_review_unit(document, "section", "section:1")

    assert "Isi section." in section["raw_latex"]
    assert r"\subsection{Definisi}" in section["raw_latex"]
    assert r"\section{Machine Learning}" not in section["raw_latex"]


def test_unknown_target_is_rejected() -> None:
    document = parse_latex_structure("chapter2.tex", DOCUMENT)

    with pytest.raises(ValueError, match="Bagian yang dipilih tidak ditemukan"):
        resolve_review_unit(document, "section", "section:999")


def test_frontmatter_uses_friendly_labels() -> None:
    source = "\\chapter*{Abstrak}\nIsi abstrak."
    document = parse_latex_structure("frontmatter.tex", source)

    assert document["chapter"]["display_label"] == "Bagian Awal"
    assert build_review_menu(document)[1]["label"] == "Abstrak"
