from app.services.latex_fragment_preview import (
    FragmentContext,
    build_fragment_source,
    build_fragment_wrapper,
)


def _context(scope: str = "subsection") -> FragmentContext:
    return FragmentContext(
        selected_file="chapter2.tex",
        scope=scope,
        target_id=f"{scope}:3",
        label="Landasan Teori > Diabetes Mellitus Tipe 2",
        title="Diabetes Mellitus Tipe 2",
        chapter_number=2,
        section_number=2,
        subsection_number=1,
    )


def test_wrapper_reuses_preamble_and_restores_heading_counters() -> None:
    main_source = "\\documentclass{report}\n\\newcommand{\\eng}[1]{#1}\n\\begin{document}\nold"

    wrapper = build_fragment_wrapper(main_source, _context())

    assert "\\newcommand{\\eng}[1]{#1}" in wrapper
    assert "\\setcounter{chapter}{2}" in wrapper
    assert "\\setcounter{section}{2}" in wrapper
    assert "\\setcounter{subsection}{0}" in wrapper
    assert "\\input{fragment}" in wrapper
    assert "old" not in wrapper


def test_fragment_adds_selected_heading_once() -> None:
    content = "Isi revisi dengan \\cite{ref1}."
    with_heading = "\\subsection{Diabetes Mellitus Tipe 2}\n\n" + content

    generated = build_fragment_source(_context(), content)
    preserved = build_fragment_source(_context(), with_heading)

    assert generated.count("\\subsection{") == 1
    assert preserved.count("\\subsection{") == 1


def test_chapter_heading_is_restored_when_missing() -> None:
    chapter = _context("chapter")

    generated = build_fragment_source(chapter, "Isi Bab.")

    assert generated.startswith("\\chapter{Diabetes Mellitus Tipe 2}")
