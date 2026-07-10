from app.services.revision_service import build_revision_draft


def test_build_revision_draft_promotes_headings_and_lists() -> None:
    source = """12

BAB I
PENDAHULUAN
1.1.
Latar Belakang
Perkembangan teknologi machine learning
semakin pesat.

1.2.
Rumusan Masalah
1. Bagaimana membangun model
2. Bagaimana membandingkan performa
"""
    content, summary = build_revision_draft(
        source,
        [{"issue": "Istilah belum konsisten.", "suggestion": "Samakan istilah."}],
        "I Bab I",
        "Rapikan bahasa akademik",
        section_number="I",
        section_title="Pendahuluan",
        section_level="CHAPTER",
    )

    assert "\\chapter{Pendahuluan}" in content
    assert "\\section{Latar Belakang}" in content
    assert "\\section{Rumusan Masalah}" in content
    assert "\\begin{enumerate}" in content
    assert "\\item Bagaimana membangun model" in content
    assert "12" not in content
    assert "dirapikan ke format LaTeX" in summary


def test_build_revision_draft_keeps_notes_commented() -> None:
    content, _summary = build_revision_draft(
        "Isi paragraf sederhana.",
        [{"issue": "Kalimat terlalu panjang.", "suggestion": "Pecah jadi dua kalimat."}],
        "1.1 Latar Belakang",
        "Rapikan",
        section_number="1.1",
        section_title="Latar Belakang",
        section_level="SUBCHAPTER",
    )

    assert "% Catatan revisi otomatis" in content
    assert "% 1. Kalimat terlalu panjang. Pecah jadi dua kalimat." in content
