from app.services.latex_revision_sanitizer import sanitize_revision_latex


def test_sanitize_revision_latex_escapes_special_characters() -> None:
    sample = "section Pendahuluan\nA & B 100% #tag data_set\n"
    result = sanitize_revision_latex(sample)

    assert "\\section" in result
    assert "A \\& B" in result
    assert "100\\%" in result
    assert "\\#tag" in result
    assert "data\\_set" in result


def test_sanitize_revision_latex_keeps_existing_escapes() -> None:
    sample = r"Sudah aman: \& \% \# \_"
    result = sanitize_revision_latex(sample)

    assert result == sample
