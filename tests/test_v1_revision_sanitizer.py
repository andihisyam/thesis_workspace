from app.services.latex_revision_sanitizer import sanitize_revision_latex


def test_sanitizer_normalizes_common_llm_output() -> None:
    source = "  **Penting** & konsisten\r\n  "

    assert sanitize_revision_latex(source) == r"\textbf{Penting} \& konsisten"


def test_sanitizer_does_not_double_escape_ampersand() -> None:
    assert sanitize_revision_latex(r"A \& B") == r"A \& B"
